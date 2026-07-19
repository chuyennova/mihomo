//go:build windows

package outbound

import (
	"context"
	"encoding/binary"
	goerrors "errors"
	"fmt"
	"hash/fnv"
	"net"
	"net/netip"
	"os"
	"sort"
	"strings"
	"sync"
	"syscall"
	"unsafe"

	"github.com/metacubex/mihomo/log"
	singWireGuard "github.com/metacubex/sing-wireguard"
	M "github.com/metacubex/sing/common/metadata"
	metaTun "github.com/metacubex/wireguard-go/tun"
	"golang.org/x/sys/windows"
	wireguardTun "golang.zx2c4.com/wireguard/tun"
	"golang.zx2c4.com/wireguard/windows/tunnel/winipcfg"
)

const (
	// Keep the interface itself cheap for sockets pinned with IP_UNICAST_IF or
	// IPV6_UNICAST_IF. Put the protection against accidental system-wide use on
	// the route metric instead.
	windowsWireGuardInterfaceMetric = 5
	windowsWireGuardRouteMetric     = 9000
	ipUnicastInterfaceOption        = 31
	ipv6UnicastInterfaceOption      = 31
)

type windowsWireGuardLUIDDevice interface {
	wireguardTun.Device
	LUID() uint64
}

type windowsWireGuardTunDevice struct {
	tun wireguardTun.Device

	luid    winipcfg.LUID
	name    string
	ifIndex int
	v4      netip.Addr
	v6      netip.Addr

	tcp4 *net.Dialer
	tcp6 *net.Dialer
	udp4 *net.Dialer
	udp6 *net.Dialer
	lc4  *net.ListenConfig
	lc6  *net.ListenConfig

	events    chan metaTun.Event
	startOnce sync.Once
	closeOnce sync.Once
	closeErr  error
}

var _ singWireGuard.Device = (*windowsWireGuardTunDevice)(nil)

func wireGuardShouldDeferDeviceCreation() bool {
	for _, argument := range os.Args[1:] {
		if argument == "-t" {
			return true
		}
	}
	return false
}

func newWireGuardTunDevice(option WireGuardOption, localPrefixes []netip.Prefix, mtu uint32) (_ singWireGuard.Device, err error) {
	if mtu == 0 {
		return nil, fmt.Errorf("Windows WireGuard system stack requires a non-zero MTU")
	}

	var v4, v6 netip.Addr
	addresses := make([]netip.Prefix, 0, len(localPrefixes))
	for _, prefix := range localPrefixes {
		if !prefix.IsValid() {
			continue
		}
		addresses = append(addresses, prefix)
		address := prefix.Addr().Unmap()
		if address.Is4() && !v4.IsValid() {
			v4 = address
		} else if address.Is6() && !v6.IsValid() {
			v6 = address
		}
	}
	if len(addresses) == 0 {
		return nil, fmt.Errorf("Windows WireGuard system stack requires at least one local address")
	}

	routePrefixes, err := windowsWireGuardRoutePrefixes(option, v4.IsValid(), v6.IsValid())
	if err != nil {
		return nil, err
	}

	name := windowsWireGuardInterfaceName(option.Name, addresses)
	nativeTun, err := wireguardTun.CreateTUN(name, int(mtu))
	if err != nil {
		return nil, fmt.Errorf("create Wintun adapter %q: %w", name, err)
	}

	luidDevice, ok := nativeTun.(windowsWireGuardLUIDDevice)
	if !ok {
		_ = nativeTun.Close()
		return nil, fmt.Errorf("Wintun adapter %q does not expose a Windows LUID", name)
	}
	luid := winipcfg.LUID(luidDevice.LUID())
	if luid == 0 {
		_ = nativeTun.Close()
		return nil, fmt.Errorf("Wintun adapter %q returned an invalid LUID", name)
	}

	device := &windowsWireGuardTunDevice{
		tun:    nativeTun,
		luid:   luid,
		name:   name,
		v4:     v4,
		v6:     v6,
		events: make(chan metaTun.Event, 4),
	}
	defer func() {
		if err != nil {
			_ = device.Close()
		}
	}()

	if err = luid.SetIPAddresses(addresses); err != nil {
		return nil, fmt.Errorf("configure addresses on %q: %w", name, err)
	}
	if v4.IsValid() {
		if err = configureWindowsWireGuardInterface(luid, windows.AF_INET, mtu); err != nil {
			return nil, fmt.Errorf("configure IPv4 interface %q: %w", name, err)
		}
	}
	if v6.IsValid() {
		if err = configureWindowsWireGuardInterface(luid, windows.AF_INET6, mtu); err != nil {
			return nil, fmt.Errorf("configure IPv6 interface %q: %w", name, err)
		}
	}

	routes, err := windowsWireGuardRoutes(routePrefixes, v4.IsValid(), v6.IsValid())
	if err != nil {
		return nil, err
	}
	if err = luid.SetRoutes(routes); err != nil {
		return nil, fmt.Errorf("configure routes on %q: %w", name, err)
	}

	interfaceRow, err := luid.Interface()
	if err != nil {
		return nil, fmt.Errorf("read Wintun interface %q: %w", name, err)
	}
	device.ifIndex = int(interfaceRow.InterfaceIndex)
	if device.ifIndex <= 0 {
		return nil, fmt.Errorf("Wintun interface %q has an invalid index", name)
	}

	if v4.IsValid() {
		device.tcp4 = newWindowsWireGuardDialer("tcp4", v4, device.ifIndex)
		device.udp4 = newWindowsWireGuardDialer("udp4", v4, device.ifIndex)
		device.lc4 = newWindowsWireGuardListenConfig("udp4", device.ifIndex)
	}
	if v6.IsValid() {
		device.tcp6 = newWindowsWireGuardDialer("tcp6", v6, device.ifIndex)
		device.udp6 = newWindowsWireGuardDialer("udp6", v6, device.ifIndex)
		device.lc6 = newWindowsWireGuardListenConfig("udp6", device.ifIndex)
	}

	log.Warnln("[WG](%s) Using Windows Winsock system stack: interface=%s index=%d mtu=%d", option.Name, name, device.ifIndex, mtu)
	return device, nil
}

func windowsWireGuardRoutePrefixes(option WireGuardOption, has4, has6 bool) ([]netip.Prefix, error) {
	routeSet := make(map[netip.Prefix]struct{})
	addRoute := func(prefix netip.Prefix) error {
		if !prefix.IsValid() {
			return fmt.Errorf("invalid WireGuard allowed IP")
		}
		prefix = prefix.Masked()
		address := prefix.Addr().Unmap()
		if address.Is4() {
			if !has4 {
				return fmt.Errorf("IPv4 allowed IP %s requires an IPv4 WireGuard address", prefix)
			}
		} else if address.Is6() {
			if !has6 {
				return fmt.Errorf("IPv6 allowed IP %s requires an IPv6 WireGuard address", prefix)
			}
		} else {
			return fmt.Errorf("unsupported WireGuard allowed IP %s", prefix)
		}
		routeSet[prefix] = struct{}{}
		return nil
	}

	if len(option.Peers) > 0 {
		for peerIndex, peer := range option.Peers {
			for _, allowedIP := range peer.AllowedIPs {
				prefix, err := netip.ParsePrefix(allowedIP)
				if err != nil {
					return nil, fmt.Errorf("parse allowed IP for peer %d: %w", peerIndex, err)
				}
				if err = addRoute(prefix); err != nil {
					return nil, err
				}
			}
		}
	} else {
		// Mihomo's legacy single-peer WireGuard configuration always installs
		// full-tunnel allowed IPs for every configured address family.
		if has4 {
			_ = addRoute(netip.MustParsePrefix("0.0.0.0/0"))
		}
		if has6 {
			_ = addRoute(netip.MustParsePrefix("::/0"))
		}
	}

	if len(routeSet) == 0 {
		return nil, fmt.Errorf("missing WireGuard allowed IP routes")
	}

	routes := make([]netip.Prefix, 0, len(routeSet))
	for prefix := range routeSet {
		routes = append(routes, prefix)
	}
	sort.Slice(routes, func(i, j int) bool {
		if routes[i].Addr().BitLen() != routes[j].Addr().BitLen() {
			return routes[i].Addr().BitLen() < routes[j].Addr().BitLen()
		}
		if routes[i].Bits() != routes[j].Bits() {
			return routes[i].Bits() < routes[j].Bits()
		}
		return routes[i].Addr().Less(routes[j].Addr())
	})
	return routes, nil
}

func configureWindowsWireGuardInterface(luid winipcfg.LUID, family winipcfg.AddressFamily, mtu uint32) error {
	row, err := luid.IPInterface(family)
	if err != nil {
		return err
	}
	row.RouterDiscoveryBehavior = winipcfg.RouterDiscoveryDisabled
	row.DadTransmits = 0
	row.ManagedAddressConfigurationSupported = false
	row.OtherStatefulConfigurationSupported = false
	row.NLMTU = mtu
	row.UseAutomaticMetric = false
	row.Metric = windowsWireGuardInterfaceMetric
	return row.Set()
}

func windowsWireGuardRoutes(prefixes []netip.Prefix, has4, has6 bool) ([]*winipcfg.RouteData, error) {
	routes := make([]*winipcfg.RouteData, 0, len(prefixes))
	for _, prefix := range prefixes {
		if !prefix.IsValid() {
			return nil, fmt.Errorf("invalid Windows WireGuard route")
		}
		prefix = prefix.Masked()
		nextHop := netip.IPv6Unspecified()
		if prefix.Addr().Is4() {
			if !has4 {
				return nil, fmt.Errorf("IPv4 route %s requires an IPv4 WireGuard address", prefix)
			}
			nextHop = netip.IPv4Unspecified()
		} else if prefix.Addr().Is6() {
			if !has6 {
				return nil, fmt.Errorf("IPv6 route %s requires an IPv6 WireGuard address", prefix)
			}
		} else {
			return nil, fmt.Errorf("unsupported Windows WireGuard route %s", prefix)
		}
		routes = append(routes, &winipcfg.RouteData{
			Destination: prefix,
			NextHop:     nextHop,
			Metric:      windowsWireGuardRouteMetric,
		})
	}
	return routes, nil
}

func windowsWireGuardInterfaceName(proxyName string, prefixes []netip.Prefix) string {
	parts := make([]string, 0, len(prefixes)+1)
	parts = append(parts, proxyName)
	for _, prefix := range prefixes {
		parts = append(parts, prefix.String())
	}
	sort.Strings(parts[1:])
	hash := fnv.New32a()
	_, _ = hash.Write([]byte(strings.Join(parts, ",")))
	return fmt.Sprintf("Mihomo WG %08x", hash.Sum32())
}

func newWindowsWireGuardDialer(network string, localAddr netip.Addr, ifIndex int) *net.Dialer {
	dialer := &net.Dialer{}

	// Do not hard-bind the IPv4 /32 source. IP_UNICAST_IF pins the socket
	// to this Wintun adapter while Windows selects its configured IPv4 source.
	// Bind IPv6 explicitly because a ULA /128 otherwise has unreliable source
	// selection on Windows when several interfaces are active.
	switch network {
	case "udp4":
		dialer.LocalAddr = &net.UDPAddr{IP: net.IP(localAddr.AsSlice())}
	case "tcp6":
		dialer.LocalAddr = &net.TCPAddr{IP: net.IP(localAddr.AsSlice())}
	case "udp6":
		dialer.LocalAddr = &net.UDPAddr{IP: net.IP(localAddr.AsSlice())}
	}
	dialer.Control = windowsWireGuardInterfaceControl(network, ifIndex)
	return dialer
}

func newWindowsWireGuardListenConfig(network string, ifIndex int) *net.ListenConfig {
	listenConfig := &net.ListenConfig{}
	listenConfig.Control = windowsWireGuardInterfaceControl(network, ifIndex)
	return listenConfig
}

func windowsWireGuardInterfaceControl(expectedNetwork string, ifIndex int) func(string, string, syscall.RawConn) error {
	return func(_, _ string, raw syscall.RawConn) error {
		var socketErr error
		controlErr := raw.Control(func(fd uintptr) {
			switch expectedNetwork {
			case "tcp4", "udp4":
				var indexBytes [4]byte
				binary.BigEndian.PutUint32(indexBytes[:], uint32(ifIndex))
				index := *(*uint32)(unsafe.Pointer(&indexBytes[0]))
				socketErr = windows.SetsockoptInt(windows.Handle(fd), windows.IPPROTO_IP, ipUnicastInterfaceOption, int(index))
			case "tcp6", "udp6":
				socketErr = windows.SetsockoptInt(windows.Handle(fd), windows.IPPROTO_IPV6, ipv6UnicastInterfaceOption, ifIndex)
			default:
				socketErr = fmt.Errorf("unsupported Windows WireGuard network %q", expectedNetwork)
			}
		})
		if controlErr != nil {
			return controlErr
		}
		return socketErr
	}
}

func (d *windowsWireGuardTunDevice) DialContext(ctx context.Context, network string, destination M.Socksaddr) (net.Conn, error) {
	if !destination.Addr.IsValid() {
		return nil, fmt.Errorf("Windows WireGuard system stack requires a resolved destination")
	}
	remoteIP := destination.Addr.Unmap()
	remote := netip.AddrPortFrom(remoteIP, destination.Port)

	network = strings.ToLower(network)
	switch {
	case strings.HasPrefix(network, "tcp"):
		if remoteIP.Is4() {
			if d.tcp4 == nil {
				return nil, fmt.Errorf("IPv4 is not configured on %q", d.name)
			}
			return d.tcp4.DialContext(ctx, "tcp4", remote.String())
		}
		if d.tcp6 == nil {
			return nil, fmt.Errorf("IPv6 is not configured on %q", d.name)
		}
		return d.tcp6.DialContext(ctx, "tcp6", remote.String())
	case strings.HasPrefix(network, "udp"):
		if remoteIP.Is4() {
			if d.udp4 == nil {
				return nil, fmt.Errorf("IPv4 is not configured on %q", d.name)
			}
			return d.udp4.DialContext(ctx, "udp4", remote.String())
		}
		if d.udp6 == nil {
			return nil, fmt.Errorf("IPv6 is not configured on %q", d.name)
		}
		return d.udp6.DialContext(ctx, "udp6", remote.String())
	default:
		return nil, fmt.Errorf("unsupported Windows WireGuard network %q", network)
	}
}

func (d *windowsWireGuardTunDevice) ListenPacket(ctx context.Context, destination M.Socksaddr) (net.PacketConn, error) {
	if !destination.Addr.IsValid() {
		return nil, fmt.Errorf("Windows WireGuard system stack requires a resolved UDP destination")
	}
	remoteIP := destination.Addr.Unmap()
	if remoteIP.Is4() {
		if d.lc4 == nil || !d.v4.IsValid() {
			return nil, fmt.Errorf("IPv4 is not configured on %q", d.name)
		}
		return d.lc4.ListenPacket(ctx, "udp4", net.JoinHostPort(d.v4.String(), "0"))
	}
	if d.lc6 == nil || !d.v6.IsValid() {
		return nil, fmt.Errorf("IPv6 is not configured on %q", d.name)
	}
	return d.lc6.ListenPacket(ctx, "udp6", net.JoinHostPort(d.v6.String(), "0"))
}

func (d *windowsWireGuardTunDevice) Start() error {
	d.startOnce.Do(func() {
		d.events <- metaTun.EventUp
	})
	return nil
}

func (d *windowsWireGuardTunDevice) Inet4Address() netip.Addr {
	return d.v4
}

func (d *windowsWireGuardTunDevice) Inet6Address() netip.Addr {
	return d.v6
}

func (d *windowsWireGuardTunDevice) RegisterForward(singWireGuard.ForwardOptions) error {
	return fmt.Errorf("packet forwarding is unavailable on the Windows WireGuard system stack")
}

func (d *windowsWireGuardTunDevice) File() *os.File {
	return d.tun.File()
}

func (d *windowsWireGuardTunDevice) Read(bufs [][]byte, sizes []int, offset int) (int, error) {
	return d.tun.Read(bufs, sizes, offset)
}

func (d *windowsWireGuardTunDevice) Write(bufs [][]byte, offset int) (int, error) {
	return d.tun.Write(bufs, offset)
}

func (d *windowsWireGuardTunDevice) MTU() (int, error) {
	return d.tun.MTU()
}

func (d *windowsWireGuardTunDevice) Name() (string, error) {
	return d.tun.Name()
}

func (d *windowsWireGuardTunDevice) Events() <-chan metaTun.Event {
	return d.events
}

func (d *windowsWireGuardTunDevice) BatchSize() int {
	return d.tun.BatchSize()
}

func (d *windowsWireGuardTunDevice) Close() error {
	d.closeOnce.Do(func() {
		var errs []error
		select {
		case d.events <- metaTun.EventDown:
		default:
		}

		if d.luid != 0 {
			if err := d.luid.FlushRoutes(windows.AF_UNSPEC); err != nil {
				errs = append(errs, fmt.Errorf("flush routes on %q: %w", d.name, err))
			}
			if err := d.luid.FlushIPAddresses(windows.AF_UNSPEC); err != nil {
				errs = append(errs, fmt.Errorf("flush addresses on %q: %w", d.name, err))
			}
		}
		if d.tun != nil {
			if err := d.tun.Close(); err != nil {
				errs = append(errs, fmt.Errorf("close Wintun adapter %q: %w", d.name, err))
			}
		}
		close(d.events)
		d.closeErr = goerrors.Join(errs...)
	})
	return d.closeErr
}
