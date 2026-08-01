#!/usr/bin/env python3
"""Apply the Mihomo v1.19.29 WireGuard-only macOS-like profile.

Run this script after `go mod vendor` from the Mihomo repository root.
It patches only the WireGuard userspace stack. OpenVPN, MASQUE, normal TUN,
and every other consumer of gVisor keep their original behavior.

The patch is intentionally strict: every source anchor must match exactly once.
If upstream source/dependency versions change, the build stops instead of
silently producing a partially patched executable.
"""
from __future__ import annotations

import argparse
import pathlib
import sys


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def patch_mihomo(root: pathlib.Path) -> None:
    path = root / "adapter/outbound/wireguard.go"
    text = read(path)
    text = replace_once(
        text,
        "outbound.tunDevice, err = wireguard.NewStackDevice(outbound.localPrefixes, uint32(mtu))",
        "outbound.tunDevice, err = wireguard.NewStackDeviceMacOSLike(outbound.localPrefixes, uint32(mtu))",
        "Mihomo WireGuard constructor",
    )
    write(path, text)


def patch_sing_device_stack(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go"
    text = read(path)

    text = replace_once(
        text,
        """\taddr4      tcpip.Address
\taddr6      tcpip.Address
}

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcp.NewProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
""",
        """\taddr4      tcpip.Address
\taddr6      tcpip.Address
\tmacOSLike  bool
}

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, false)
}

// NewStackDeviceMacOSLike creates an independent gVisor stack for one
// WireGuard outbound. It runs on Windows but selects a Darwin/macOS-like TCP
// wire profile instead of gVisor's default Linux-oriented profile.
func NewStackDeviceMacOSLike(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, true)
}

func newStackDevice(localAddresses []netip.Prefix, mtu uint32, macOSLike bool) (*StackDevice, error) {
\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tif macOSLike {
\t\ttcpProtocol = tcp.NewProtocolMacOSLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
\tif macOSLike {
\t\t// Normal XNU automatic client-port range. PortManager is per stack,
\t\t// so WireGuard outbounds remain fully isolated.
\t\tif err := ipStack.SetPortRange(49152, 65535); err != nil {
\t\t\treturn nil, E.New("set macOS-like ephemeral port range: ", err.String())
\t\t}
\t}
""",
        "sing-wireguard constructors",
    )

    text = replace_once(
        text,
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t}
""",
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t\tmacOSLike: macOSLike,
\t}
""",
        "sing-wireguard profile initialization",
    )

    text = replace_once(
        text,
        """\tcase N.NetworkTCP:
\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
""",
        """\tcase N.NetworkTCP:
\t\tif w.macOSLike {
\t\t\tconn, err = DialTCPWithBindMacOSLike(ctx, w.stack, bind, addr, networkProtocol)
\t\t} else {
\t\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
\t\t}
""",
        "sing-wireguard TCP dial selection",
    )
    write(path, text)


def patch_sing_gonet(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/gonet.go"
    text = read(path)

    text = replace_once(
        text,
        """func DialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\t// Create TCP endpoint, then connect.
""",
        """func DialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\treturn dialTCPWithBind(ctx, s, localAddr, remoteAddr, network, true)
}

// DialTCPWithBindMacOSLike leaves SO_KEEPALIVE disabled, as on a normal
// outbound socket unless the application explicitly enables it.
func DialTCPWithBindMacOSLike(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
\treturn dialTCPWithBind(ctx, s, localAddr, remoteAddr, network, false)
}

func dialTCPWithBind(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber, forceKeepalive bool) (*gonet.TCPConn, error) {
\t// Create TCP endpoint, then connect.
""",
        "sing-wireguard TCP dial helper",
    )

    text = replace_once(
        text,
        """\t// sing-box added: set keepalive
\tep.SocketOptions().SetKeepAlive(true)
\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveIdle)
\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveInterval)
""",
        """\tif forceKeepalive {
\t\t// Preserve original sing-wireguard behavior for ordinary stacks.
\t\tep.SocketOptions().SetKeepAlive(true)
\t\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveIdle)
\t\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveInterval)
\t}
""",
        "sing-wireguard forced keepalive",
    )
    write(path, text)


def patch_gvisor_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go"
    text = read(path)

    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack

\tmu""",
        """type protocol struct {
\tstack     *stack.Stack
\tmacOSLike bool `state:\"nosave\"`

\tmu""",
        "gVisor TCP protocol profile field",
    )

    text = replace_once(
        text,
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil)
}
""",
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil, false)
}

// NewProtocolMacOSLike creates a per-stack Darwin/macOS-like TCP profile.
// It is selected only by the Mihomo WireGuard constructor added by this patch.
func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true)
}
""",
        "gVisor NewProtocol",
    )

    text = replace_once(
        text,
        """\treturn func(s *stack.Stack) stack.TransportProtocol {
\t\treturn newProtocol(s, ccReno, probe)
\t}
""",
        """\treturn func(s *stack.Stack) stack.TransportProtocol {
\t\treturn newProtocol(s, ccReno, probe, false)
\t}
""",
        "gVisor NewProtocolProbe",
    )

    text = replace_once(
        text,
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc) stack.TransportProtocol {
""",
        """func NewProtocolCUBIC(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, false)
}

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc, macOSLike bool) stack.TransportProtocol {
""",
        "gVisor CUBIC and newProtocol signature",
    )

    text = replace_once(
        text,
        """\tp := protocol{
\t\tstack: s,
""",
        """\tp := protocol{
\t\tstack:     s,
\t\tmacOSLike: macOSLike,
""",
        "gVisor TCP protocol initialization",
    )
    write(path, text)


def patch_gvisor_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go"
    text = read(path)

    text = replace_once(
        text,
        """func (e *Endpoint) initialReceiveWindow() int {
\trcvWnd := wndFromSpace(e.receiveBufferAvailable())
""",
        """func (e *Endpoint) initialReceiveWindow() int {
\tif e.protocol.macOSLike {
\t\t// Common active-open XNU/macOS SYN profile. The negotiated scale is
\t\t// applied only after the handshake; the SYN field itself is 65535.
\t\treturn math.MaxUint16
\t}
\trcvWnd := wndFromSpace(e.receiveBufferAvailable())
""",
        "gVisor initial SYN receive window",
    )

    text = replace_once(
        text,
        """func (e *Endpoint) rcvWndScaleForHandshake() int {
\tbufSizeForScale := e.ops.GetReceiveBufferSize()
""",
        """func (e *Endpoint) rcvWndScaleForHandshake() int {
\tif e.protocol.macOSLike {
\t\t// Common desktop macOS/XNU client signature.
\t\treturn 4
\t}
\tbufSizeForScale := e.ops.GetReceiveBufferSize()
""",
        "gVisor SYN window scale",
    )
    write(path, text)


def patch_gvisor_connect(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)

    text = replace_once(
        text,
        "func makeSynOptions(opts header.TCPSynOptions) []byte {",
        "func makeDefaultSynOptions(opts header.TCPSynOptions) []byte {",
        "rename default SYN encoder",
    )

    text = replace_once(
        text,
        """\treturn options[:offset]
}

// tcpFields is a struct to carry different parameters required by the
""",
        """\treturn options[:offset]
}

// makeDarwinSynOptions follows XNU's active-open layout:
// MSS, NOP+WindowScale, NOP+NOP+Timestamp, SACK-Permitted last, followed by
// EOL and zero padding to a four-byte boundary.
func makeDarwinSynOptions(opts header.TCPSynOptions) []byte {
\toptions := getOptions()
\toffset := header.EncodeMSSOption(uint32(opts.MSS), options)

\tif opts.WS >= 0 {
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeWSOption(opts.WS, options[offset:])
\t}
\tif opts.TS {
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeTSOption(opts.TSVal, opts.TSEcr, options[offset:])
\t}
\tif opts.SACKPermitted {
\t\toffset += header.EncodeSACKPermittedOption(options[offset:])
\t}

\tif offset%4 != 0 {
\t\toptions[offset] = header.TCPOptionEOL
\t\toffset++
\t\tfor offset%4 != 0 {
\t\t\toptions[offset] = 0
\t\t\toffset++
\t\t}
\t}
\treturn options[:offset]
}

func makeSynOptions(opts header.TCPSynOptions, macOSLike bool) []byte {
\tif macOSLike {
\t\treturn makeDarwinSynOptions(opts)
\t}
\treturn makeDefaultSynOptions(opts)
}

// tcpFields is a struct to carry different parameters required by the
""",
        "insert Darwin SYN encoder",
    )

    text = replace_once(
        text,
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts)
""",
        """func (e *Endpoint) sendSynTCP(r *stack.Route, tf tcpFields, opts header.TCPSynOptions) tcpip.Error {
\ttf.opts = makeSynOptions(opts, e.protocol.macOSLike)
\tif e.protocol.macOSLike {
\t\t// XNU enables Path MTU Discovery for normal TCP. gVisor's IPv4
\t\t// writer then emits DF=1 and leaves the atomic datagram IP ID at 0.
\t\ttf.df = true
\t}
""",
        "gVisor SYN profile selection and DF",
    )
    write(path, text)



def patch_sing_ipv6_udp(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go"
    text = read(path)
    text = replace_once(
        text,
        """\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tif macOSLike {
\t\ttcpProtocol = tcp.NewProtocolMacOSLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
""",
        """\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tvar udpProtocol stack.TransportProtocolFactory = udp.NewProtocol
\tif macOSLike {
\t\ttcpProtocol = tcp.NewProtocolMacOSLike
\t\tudpProtocol = udp.NewProtocolMacOSLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udpProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
""",
        "sing-wireguard macOS-like UDP protocol",
    )
    write(path, text)


def patch_gvisor_ipv6_flowlabel(root: pathlib.Path) -> None:
    # Extend the transport-to-network header contract with a 20-bit flow label.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// TOS refers to TypeOfService or TrafficClass field of the IP-header.
\tTOS uint8

\t// DF indicates whether the DF bit should be set.
""",
        """\t// TOS refers to TypeOfService or TrafficClass field of the IP-header.
\tTOS uint8

\t// IPv6FlowLabel is the 20-bit Flow Label used only for IPv6 packets.
\t// IPv4 network endpoints ignore this field.
\tIPv6FlowLabel uint32

\t// DF indicates whether the DF bit should be set.
""",
        "gVisor NetworkHeaderParams IPv6 Flow Label",
    )
    write(path, text)

    # Encode the value into the real IPv6 base header.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go"
    text = read(path)
    text = replace_once(
        text,
        """\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tSrcAddr:           srcAddr,
""",
        """\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tFlowLabel:         params.IPv6FlowLabel & 0x000fffff,
\t\tSrcAddr:           srcAddr,
""",
        "gVisor IPv6 header Flow Label encoding",
    )
    write(path, text)

    # TCP uses one random 20-bit label for the lifetime of an IPv6 endpoint,
    # matching XNU's automatic per-PCB flow-label model.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true)
}
""",
        """func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccCubic, nil, true)
}

// newIPv6FlowLabel provides an XNU-like random value masked to the 20-bit
// IPv6 Flow Label field. A zero label is statistically possible and is kept.
func (p *protocol) newIPv6FlowLabel() uint32 {
\trng := p.stack.SecureRNG()
	return rng.Uint32() & 0x000fffff
}
""",
        "gVisor TCP random IPv6 Flow Label generator",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\troute             *stack.Route `state:\"nosave\"`
\tipv4TTL           uint8
\tipv6HopLimit      int16
\tisConnectNotified bool
""",
        """\troute             *stack.Route `state:\"nosave\"`
\tipv4TTL           uint8
\tipv6HopLimit      int16
\tipv6FlowLabel     uint32
\tisConnectNotified bool
""",
        "gVisor TCP endpoint IPv6 Flow Label field",
    )
    text = replace_once(
        text,
        """\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        """\tif protocol.macOSLike && netProto == header.IPv6ProtocolNumber {
\t\te.ipv6FlowLabel = protocol.newIPv6FlowLabel()
\t}
\te.ops.InitHandler(e, e.stack, GetTCPSendBufferLimits, GetTCPReceiveBufferLimits)
""",
        "gVisor TCP endpoint Flow Label initialization",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)
    text = replace_once(
        text,
        """\ttos       uint8
\tflags     header.TCPFlags
""",
        """\ttos           uint8
\tipv6FlowLabel uint32
\tflags         header.TCPFlags
""",
        "gVisor TCP fields IPv6 Flow Label",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
""",
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
\tif r.NetProto() == header.IPv6ProtocolNumber {
\t\ttf.ipv6FlowLabel = e.ipv6FlowLabel
\t}
""",
        "gVisor TCP packet Flow Label selection",
    )
    text = replace_once(
        text,
        """\t\t\tTOS:                   tf.tos,
\t\t\tDF:                    tf.df,
""",
        """\t\t\tTOS:                   tf.tos,
\t\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\t\tDF:                    tf.df,
""",
        "gVisor TCP batch IPv6 Flow Label",
    )
    text = replace_once(
        text,
        """\t\tTOS:                   tf.tos,
\t\tDF:                    tf.df,
""",
        """\t\tTOS:                   tf.tos,
\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\tDF:                    tf.df,
""",
        "gVisor TCP packet IPv6 Flow Label",
    )
    write(path, text)

    # UDP also gets a distinct macOS-like transport protocol so QUIC/UDP uses
    # a stable random label per UDP socket, not TCP-only behavior.
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack
}
""",
        """type protocol struct {
\tstack     *stack.Stack
\tmacOSLike bool `state:\"nosave\"`
}

func (p *protocol) newIPv6FlowLabel() uint32 {
\trng := p.stack.SecureRNG()
	return rng.Uint32() & 0x000fffff
}
""",
        "gVisor UDP profile and Flow Label generator",
    )
    text = replace_once(
        text,
        """func (p *protocol) NewEndpoint(netProto tcpip.NetworkProtocolNumber, waiterQueue *waiter.Queue) (tcpip.Endpoint, tcpip.Error) {
\treturn newEndpoint(p.stack, netProto, waiterQueue), nil
}
""",
        """func (p *protocol) NewEndpoint(netProto tcpip.NetworkProtocolNumber, waiterQueue *waiter.Queue) (tcpip.Endpoint, tcpip.Error) {
\tep := newEndpoint(p.stack, netProto, waiterQueue)
\tep.protocol = p
\tif p.macOSLike && netProto == header.IPv6ProtocolNumber {
\t\tep.net.SetIPv6FlowLabel(p.newIPv6FlowLabel())
\t}
\treturn ep, nil
}
""",
        "gVisor UDP endpoint constructor",
    )
    text = replace_once(
        text,
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s}
}
""",
        """func NewProtocol(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s}
}

// NewProtocolMacOSLike selects the XNU-like IPv6 flow-label behavior only
// for the independent WireGuard stack that opts into this constructor.
func NewProtocolMacOSLike(s *stack.Stack) stack.TransportProtocol {
\treturn &protocol{stack: s, macOSLike: true}
}
""",
        "gVisor UDP macOS-like constructor",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
""",
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
\tprotocol    *protocol `state:"nosave"`
""",
        "gVisor UDP endpoint protocol field",
    )
    text = replace_once(
        text,
        """\te.net.Disconnect()

\treturn nil
}
""",
        """\te.net.Disconnect()
\tif e.protocol != nil && e.protocol.macOSLike && e.net.NetProto() == header.IPv6ProtocolNumber {
\t\te.net.SetIPv6FlowLabel(e.protocol.newIPv6FlowLabel())
\t}

\treturn nil
}
""",
        "gVisor UDP Flow Label refresh after disconnect",
    )
    write(path, text)

    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\t// +checklocks:mu
\tipv6TClass uint8
""",
        """\t// +checklocks:mu
\tipv6TClass uint8
\t// +checklocks:mu
\tipv6FlowLabel uint32
""",
        "gVisor datagram endpoint IPv6 Flow Label field",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) NetProto() tcpip.NetworkProtocolNumber {
\treturn e.netProto
}
""",
        """func (e *Endpoint) NetProto() tcpip.NetworkProtocolNumber {
\treturn e.netProto
}

// SetIPv6FlowLabel sets the per-socket 20-bit IPv6 Flow Label. A zero value
// disables flow labeling. IPv4 ignores the field.
func (e *Endpoint) SetIPv6FlowLabel(label uint32) {
\te.mu.Lock()
\te.ipv6FlowLabel = label & 0x000fffff
\te.mu.Unlock()
}
""",
        "gVisor datagram Flow Label setter",
    )
    text = replace_once(
        text,
        """type WriteContext struct {
\te     *Endpoint
\troute *stack.Route
\tttl   uint8
\ttos   uint8
}
""",
        """type WriteContext struct {
\te             *Endpoint
\troute         *stack.Route
\tttl           uint8
\ttos           uint8
\tipv6FlowLabel uint32
}
""",
        "gVisor datagram WriteContext Flow Label",
    )
    text = replace_once(
        text,
        """\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tExperimentOptionValue: expOptVal,
""",
        """\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tIPv6FlowLabel:         c.ipv6FlowLabel,
\t\tExperimentOptionValue: expOptVal,
""",
        "gVisor datagram NetworkHeaderParams Flow Label",
    )
    text = replace_once(
        text,
        """\treturn WriteContext{
\t\te:     e,
\t\troute: route,
\t\tttl:   ttl,
\t\ttos:   tos,
\t}, nil
}
""",
        """\treturn WriteContext{
\t\te:             e,
\t\troute:         route,
\t\tttl:           ttl,
\t\ttos:           tos,
\t\tipv6FlowLabel: e.ipv6FlowLabel,
\t}, nil
}
""",
        "gVisor datagram WriteContext initialization",
    )
    write(path, text)

def verify(root: pathlib.Path) -> None:
    required = {
        "adapter/outbound/wireguard.go": ["NewStackDeviceMacOSLike"],
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": [
            "func NewStackDeviceMacOSLike",
            "tcp.NewProtocolMacOSLike",
            "udp.NewProtocolMacOSLike",
            "SetPortRange(49152, 65535)",
            "DialTCPWithBindMacOSLike",
        ],
        "vendor/github.com/metacubex/sing-wireguard/gonet.go": [
            "func DialTCPWithBindMacOSLike",
            "if forceKeepalive",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go": [
            "macOSLike bool",
            "func NewProtocolMacOSLike",
            "rng := p.stack.SecureRNG()",
            "return rng.Uint32() & 0x000fffff",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go": [
            "return math.MaxUint16",
            "return 4",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": [
            "func makeDarwinSynOptions",
            "header.TCPOptionEOL",
            "tf.df = true",
            "IPv6FlowLabel:         tf.ipv6FlowLabel",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go": [
            "IPv6FlowLabel uint32",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": [
            "FlowLabel:         params.IPv6FlowLabel",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go": [
            "func NewProtocolMacOSLike",
            "func (p *protocol) newIPv6FlowLabel",
            "rng := p.stack.SecureRNG()",
            "return rng.Uint32() & 0x000fffff",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go": [
            'protocol    *protocol `state:"nosave"`',
            "e.protocol != nil",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/forwarder.go": [
            "newEndpoint(r.stack, r.pkt.NetworkProtocolNumber, queue)",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go": [
            "ipv6FlowLabel uint32",
            "IPv6FlowLabel:         c.ipv6FlowLabel",
        ],
    }
    for rel, needles in required.items():
        text = read(root / rel)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"verification failed: {needle!r} missing from {rel}")

    # Exactly one Mihomo outbound may opt into the new constructor.
    selected = []
    for path in (root / "adapter/outbound").glob("*.go"):
        if "NewStackDeviceMacOSLike" in read(path):
            selected.append(path.name)
    if selected != ["wireguard.go"]:
        raise RuntimeError(f"macOS-like constructor leaked outside WireGuard: {selected}")

    for rel in (
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go",
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go",
    ):
        if "SecureRNG().Uint32()" in read(root / rel):
            raise RuntimeError(
                f"non-addressable SecureRNG temporary detected in {rel}; Uint32 has a pointer receiver"
            )

    udp_endpoint = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go")
    if "func newEndpoint(s *stack.Stack, netProto tcpip.NetworkProtocolNumber" not in udp_endpoint:
        raise RuntimeError("UDP newEndpoint signature changed; this would break udp/forwarder.go")
    if "func newEndpoint(p *protocol" in udp_endpoint:
        raise RuntimeError("unsafe UDP constructor signature detected")

    # Verify the expected byte-level active SYN option shape with all normal
    # options enabled: 2,1,3,1,1,8,4,0 and 24 bytes total.
    connect = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go")
    ordered = [
        "EncodeMSSOption",
        "EncodeNOP(options[offset:])\n\t\toffset += header.EncodeWSOption",
        "EncodeNOP(options[offset:])\n\t\toffset += header.EncodeNOP(options[offset:])\n\t\toffset += header.EncodeTSOption",
        "EncodeSACKPermittedOption",
        "TCPOptionEOL",
    ]
    positions = [connect.find(x, connect.find("func makeDarwinSynOptions")) for x in ordered]
    if any(p < 0 for p in positions) or positions != sorted(positions):
        raise RuntimeError("Darwin SYN option encoder order verification failed")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    try:
        if not args.verify_only:
            patch_mihomo(root)
            patch_sing_device_stack(root)
            patch_sing_gonet(root)
            patch_gvisor_protocol(root)
            patch_gvisor_endpoint(root)
            patch_gvisor_connect(root)
            patch_sing_ipv6_udp(root)
            patch_gvisor_ipv6_flowlabel(root)
        verify(root)
        print("macOS-like WireGuard v3.2.1 patch verification: OK")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
