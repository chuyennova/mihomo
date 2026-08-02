#!/usr/bin/env python3
"""Apply the Mihomo v1.19.29 WireGuard-only Android-like network profile.

Run after `go mod vendor` from the Mihomo repository root.
The standalone core selects this profile for WireGuard outbounds only; no YAML
field is added. Other gVisor users keep upstream behavior.
"""
from __future__ import annotations

import argparse
import pathlib


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
        """\tmtu := option.MTU
\tif mtu == 0 {
\t\tmtu = 1408
\t}
""",
        """\tmtu := option.MTU
\tif mtu == 0 {
\t\t// Representative Android/mobile WireGuard MTU. Explicit YAML always wins.
\t\tmtu = 1360
\t}
""",
        "Mihomo Android-like default MTU",
    )
    text = replace_once(
        text,
        "outbound.tunDevice, err = wireguard.NewStackDevice(outbound.localPrefixes, uint32(mtu))",
        "outbound.tunDevice, err = wireguard.NewStackDeviceAndroidLike(outbound.localPrefixes, uint32(mtu))",
        "Mihomo WireGuard Android-like constructor",
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
        """\taddr4       tcpip.Address
\taddr6       tcpip.Address
\tandroidLike bool
}

func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, false)
}

// NewStackDeviceAndroidLike creates one independent Android/Linux-oriented
// userspace stack for one WireGuard outbound. It does not create a Windows NIC.
func NewStackDeviceAndroidLike(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, true)
}

func newStackDevice(localAddresses []netip.Prefix, mtu uint32, androidLike bool) (*StackDevice, error) {
\tvar tcpProtocol stack.TransportProtocolFactory = tcp.NewProtocol
\tvar udpProtocol stack.TransportProtocolFactory = udp.NewProtocol
\tif androidLike {
\t\ttcpProtocol = tcp.NewProtocolAndroidLike
\t\tudpProtocol = udp.NewProtocolAndroidLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcpProtocol, udpProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
""",
        "sing-wireguard Android-like constructors",
    )
    text = replace_once(
        text,
        """\t\tctx:       ctx,
\t\tctxCancel: cancel,
\t}
""",
        """\t\tctx:         ctx,
\t\tctxCancel:   cancel,
\t\tandroidLike: androidLike,
\t}
""",
        "sing-wireguard Android-like initialization",
    )
    text = replace_once(
        text,
        """\tcase N.NetworkTCP:
\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
""",
        """\tcase N.NetworkTCP:
\t\tif w.androidLike {
\t\t\tconn, err = DialTCPWithBindAndroidLike(ctx, w.stack, bind, addr, networkProtocol)
\t\t} else {
\t\t\tconn, err = DialTCPWithBind(ctx, w.stack, bind, addr, networkProtocol)
\t\t}
""",
        "sing-wireguard Android-like TCP dial selection",
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

// DialTCPWithBindAndroidLike leaves SO_KEEPALIVE disabled unless the calling
// application explicitly requests it, instead of forcing one 15-second pattern.
func DialTCPWithBindAndroidLike(ctx context.Context, s *stack.Stack, localAddr, remoteAddr tcpip.FullAddress, network tcpip.NetworkProtocolNumber) (*gonet.TCPConn, error) {
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
\t\t// Preserve upstream sing-wireguard behavior for ordinary stacks.
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


def patch_stack_registration(root: pathlib.Path) -> None:
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
\tIPv6FlowLabel uint32

\t// DF indicates whether the DF bit should be set.
""",
        "gVisor NetworkHeaderParams IPv6 flow label",
    )
    write(path, text)


def patch_ipv6(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go"
    text = read(path)
    text = replace_once(
        text,
        """\t\tTransportProtocol: params.Protocol,
\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tSrcAddr:           srcAddr,
""",
        """\t\tTransportProtocol: params.Protocol,
\t\tHopLimit:          params.TTL,
\t\tTrafficClass:      params.TOS,
\t\tFlowLabel:         params.IPv6FlowLabel & 0x000fffff,
\t\tSrcAddr:           srcAddr,
""",
        "gVisor IPv6 header flow label",
    )
    write(path, text)


def patch_tcp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack

\tmu""",
        """type protocol struct {
\tstack       *stack.Stack
\tandroidLike bool `state:\"nosave\"`

\tmu""",
        "gVisor TCP Android-like field",
    )
    text = replace_once(
        text,
        """\tseqnumSecret   [16]byte
\ttsOffsetSecret [16]byte
}""",
        """\tseqnumSecret    [16]byte
\ttsOffsetSecret  [16]byte
\tflowLabelSecret [16]byte
}""",
        "gVisor TCP flow-label secret field",
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

// NewProtocolAndroidLike keeps the Linux-oriented TCP wire behavior and adds
// per-flow IPv6 labels only for the independent WireGuard stack selecting it.
func NewProtocolAndroidLike(s *stack.Stack) stack.TransportProtocol {
\treturn newProtocol(s, ccReno, nil, true)
}
""",
        "gVisor TCP NewProtocolAndroidLike",
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
        "gVisor TCP NewProtocolProbe",
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

func newProtocol(s *stack.Stack, cc string, probe TCPProbeFunc, androidLike bool) stack.TransportProtocol {
""",
        "gVisor TCP newProtocol signature",
    )
    text = replace_once(
        text,
        """\tvar seqnumSecret [16]byte
\tvar tsOffsetSecret [16]byte
""",
        """\tvar seqnumSecret [16]byte
\tvar tsOffsetSecret [16]byte
\tvar flowLabelSecret [16]byte
""",
        "gVisor TCP flow-label secret declaration",
    )
    text = replace_once(
        text,
        """\tif n, err := rng.Reader.Read(tsOffsetSecret[:]); err != nil || n != len(tsOffsetSecret) {
\t\tpanic(fmt.Sprintf(\"Read() failed: %v\", err))
\t}
\tp := protocol{
\t\tstack: s,
""",
        """\tif n, err := rng.Reader.Read(tsOffsetSecret[:]); err != nil || n != len(tsOffsetSecret) {
\t\tpanic(fmt.Sprintf(\"Read() failed: %v\", err))
\t}
\tif n, err := rng.Reader.Read(flowLabelSecret[:]); err != nil || n != len(flowLabelSecret) {
\t\tpanic(fmt.Sprintf(\"Read() failed: %v\", err))
\t}
\tp := protocol{
\t\tstack:       s,
\t\tandroidLike: androidLike,
""",
        "gVisor TCP protocol initialization",
    )
    text = replace_once(
        text,
        """\t\tseqnumSecret:               seqnumSecret,
\t\ttsOffsetSecret:             tsOffsetSecret,
\t\tprobe:                      probe,
""",
        """\t\tseqnumSecret:               seqnumSecret,
\t\ttsOffsetSecret:             tsOffsetSecret,
\t\tflowLabelSecret:            flowLabelSecret,
\t\tprobe:                      probe,
""",
        "gVisor TCP flow-label secret initialization",
    )
    text = replace_once(
        text,
        """func (p *protocol) tsOffset(src, dst tcpip.Address) tcp.TSOffset {
""",
        """func (p *protocol) ipv6FlowLabel(id stack.TransportEndpointID) uint32 {
\th := sha256.New()
\t_, _ = h.Write(p.flowLabelSecret[:])
\t_, _ = h.Write(id.LocalAddress.AsSlice())
\t_, _ = h.Write(id.RemoteAddress.AsSlice())
\tvar ports [4]byte
\tbinary.LittleEndian.PutUint16(ports[0:2], id.LocalPort)
\tbinary.LittleEndian.PutUint16(ports[2:4], id.RemotePort)
\t_, _ = h.Write(ports[:])
\t_, _ = h.Write([]byte{byte(ProtocolNumber)})
\tlabel := binary.LittleEndian.Uint32(h.Sum(nil)[:4]) & 0x000fffff
\tif label == 0 {
\t\treturn 1
\t}
\treturn label
}

func (p *protocol) tsOffset(src, dst tcpip.Address) tcp.TSOffset {
""",
        "gVisor TCP IPv6 flow-label hash",
    )
    write(path, text)


def patch_tcp_connect(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)
    text = replace_once(
        text,
        """type tcpFields struct {
\tid        stack.TransportEndpointID
\tttl       uint8
\ttos       uint8
\tflags     header.TCPFlags
""",
        """type tcpFields struct {
\tid            stack.TransportEndpointID
\tttl           uint8
\ttos           uint8
\tipv6FlowLabel uint32
\tflags         header.TCPFlags
""",
        "gVisor TCP fields IPv6 flow label",
    )
    text = replace_once(
        text,
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
""",
        """func (e *Endpoint) sendTCP(r *stack.Route, tf tcpFields, pkt *stack.PacketBuffer, gso stack.GSO) tcpip.Error {
\ttf.txHash = e.txHash
\tif e.protocol.androidLike && r.NetProto() == header.IPv6ProtocolNumber {
\t\ttf.ipv6FlowLabel = e.protocol.ipv6FlowLabel(tf.id)
\t}
""",
        "gVisor TCP per-flow IPv6 label",
    )
    text = replace_once(
        text,
        """\t\t\tProtocol:              ProtocolNumber,
\t\t\tTTL:                   tf.ttl,
\t\t\tTOS:                   tf.tos,
\t\t\tDF:                    tf.df,
""",
        """\t\t\tProtocol:              ProtocolNumber,
\t\t\tTTL:                   tf.ttl,
\t\t\tTOS:                   tf.tos,
\t\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\t\tDF:                    tf.df,
""",
        "gVisor TCP batch IPv6 label",
    )
    text = replace_once(
        text,
        """\t\tProtocol:              ProtocolNumber,
\t\tTTL:                   tf.ttl,
\t\tTOS:                   tf.tos,
\t\tDF:                    tf.df,
""",
        """\t\tProtocol:              ProtocolNumber,
\t\tTTL:                   tf.ttl,
\t\tTOS:                   tf.tos,
\t\tIPv6FlowLabel:         tf.ipv6FlowLabel,
\t\tDF:                    tf.df,
""",
        "gVisor TCP IPv6 label",
    )
    write(path, text)


def patch_udp_protocol(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go"
    text = read(path)
    text = replace_once(
        text,
        """import (
\t\"github.com/metacubex/gvisor/pkg/tcpip\"
""",
        """import (
\t\"crypto/sha256\"
\t\"encoding/binary\"
\t\"fmt\"

\t\"github.com/metacubex/gvisor/pkg/tcpip\"
""",
        "gVisor UDP hash imports",
    )
    text = replace_once(
        text,
        """type protocol struct {
\tstack *stack.Stack
}
""",
        """type protocol struct {
\tstack           *stack.Stack
\tandroidLike     bool `state:\"nosave\"`
\tflowLabelSecret [16]byte
}

func (p *protocol) ipv6FlowLabel(local, remote tcpip.Address, localPort, remotePort uint16) uint32 {
\th := sha256.New()
\t_, _ = h.Write(p.flowLabelSecret[:])
\t_, _ = h.Write(local.AsSlice())
\t_, _ = h.Write(remote.AsSlice())
\tvar ports [4]byte
\tbinary.LittleEndian.PutUint16(ports[0:2], localPort)
\tbinary.LittleEndian.PutUint16(ports[2:4], remotePort)
\t_, _ = h.Write(ports[:])
\t_, _ = h.Write([]byte{byte(ProtocolNumber)})
\tlabel := binary.LittleEndian.Uint32(h.Sum(nil)[:4]) & 0x000fffff
\tif label == 0 {
\t\treturn 1
\t}
\treturn label
}
""",
        "gVisor UDP Android-like protocol fields",
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
\treturn ep, nil
}
""",
        "gVisor UDP protocol endpoint link",
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

// NewProtocolAndroidLike adds deterministic per-flow IPv6 labels while
// preserving the normal Linux-oriented UDP behavior.
func NewProtocolAndroidLike(s *stack.Stack) stack.TransportProtocol {
\trng := s.SecureRNG()
\tvar secret [16]byte
\tif n, err := rng.Reader.Read(secret[:]); err != nil || n != len(secret) {
\t\tpanic(fmt.Sprintf(\"Read() failed: %v\", err))
\t}
\treturn &protocol{stack: s, androidLike: true, flowLabelSecret: secret}
}
""",
        "gVisor UDP NewProtocolAndroidLike",
    )
    write(path, text)


def patch_udp_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go"
    text = read(path)
    text = replace_once(
        text,
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
\tstats       tcpip.TransportEndpointStats
""",
        """\tstack       *stack.Stack
\twaiterQueue *waiter.Queue
\tnet         network.Endpoint
\tprotocol    *protocol `state:\"nosave\"`
\tstats       tcpip.TransportEndpointStats
""",
        "gVisor UDP endpoint protocol link",
    )
    text = replace_once(
        text,
        """\tpktInfo := udpInfo.ctx.PacketInfo()
\tpkt := udpInfo.ctx.TryNewPacketBufferFromPayloader(header.UDPMinimumSize+int(pktInfo.MaxHeaderLength), p)
""",
        """\tpktInfo := udpInfo.ctx.PacketInfo()
\tif e.protocol != nil && e.protocol.androidLike && pktInfo.NetProto == header.IPv6ProtocolNumber {
\t\tudpInfo.ctx.SetIPv6FlowLabel(e.protocol.ipv6FlowLabel(
\t\t\tpktInfo.LocalAddress,
\t\t\tpktInfo.RemoteAddress,
\t\t\tudpInfo.localPort,
\t\t\tudpInfo.remotePort,
\t\t))
\t}
\tpkt := udpInfo.ctx.TryNewPacketBufferFromPayloader(header.UDPMinimumSize+int(pktInfo.MaxHeaderLength), p)
""",
        "gVisor UDP per-flow IPv6 label",
    )
    write(path, text)


def patch_network_endpoint(root: pathlib.Path) -> None:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go"
    text = read(path)
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

// SetIPv6FlowLabel sets the per-write 20-bit IPv6 Flow Label.
func (c *WriteContext) SetIPv6FlowLabel(label uint32) {
\tc.ipv6FlowLabel = label & 0x000fffff
}
""",
        "gVisor datagram WriteContext IPv6 label",
    )
    text = replace_once(
        text,
        """\terr := c.route.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tExperimentOptionValue: expOptVal,
""",
        """\terr := c.route.WritePacket(stack.NetworkHeaderParams{
\t\tProtocol:              c.e.transProto,
\t\tTTL:                   c.ttl,
\t\tTOS:                   c.tos,
\t\tIPv6FlowLabel:         c.ipv6FlowLabel,
\t\tExperimentOptionValue: expOptVal,
""",
        "gVisor datagram network header IPv6 label",
    )
    write(path, text)


PATCHERS = (
    patch_mihomo,
    patch_sing_device_stack,
    patch_sing_gonet,
    patch_stack_registration,
    patch_ipv6,
    patch_tcp_protocol,
    patch_tcp_connect,
    patch_udp_protocol,
    patch_udp_endpoint,
    patch_network_endpoint,
)


def verify(root: pathlib.Path) -> None:
    checks = {
        "adapter/outbound/wireguard.go": (
            "NewStackDeviceAndroidLike",
            "mtu = 1360",
        ),
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": (
            "func NewStackDeviceAndroidLike",
            "tcp.NewProtocolAndroidLike",
            "udp.NewProtocolAndroidLike",
            "DialTCPWithBindAndroidLike",
        ),
        "vendor/github.com/metacubex/sing-wireguard/gonet.go": (
            "func DialTCPWithBindAndroidLike",
            "if forceKeepalive",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go": (
            "IPv6FlowLabel uint32",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": (
            "FlowLabel:         params.IPv6FlowLabel & 0x000fffff",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/protocol.go": (
            "func NewProtocolAndroidLike",
            "func (p *protocol) ipv6FlowLabel",
            "flowLabelSecret [16]byte",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": (
            "IPv6FlowLabel:         tf.ipv6FlowLabel",
            "e.protocol.androidLike",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/protocol.go": (
            "func NewProtocolAndroidLike",
            "func (p *protocol) ipv6FlowLabel",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/udp/endpoint.go": (
            "SetIPv6FlowLabel",
            "e.protocol.androidLike",
        ),
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/internal/network/endpoint.go": (
            "func (c *WriteContext) SetIPv6FlowLabel",
            "IPv6FlowLabel:         c.ipv6FlowLabel",
        ),
    }
    for relative, markers in checks.items():
        text = read(root / relative)
        for marker in markers:
            if marker not in text:
                raise RuntimeError(f"verify failed: {relative} missing {marker!r}")

    # Android-like deliberately keeps upstream Linux-style SYN generation.
    connect = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go")
    for forbidden in ("makeDarwinSynOptions", "tf.df = true"):
        if forbidden in connect:
            raise RuntimeError(f"verify failed: unexpected macOS behavior {forbidden!r}")
    endpoint = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go")
    for forbidden in ("return math.MaxUint16", "macOSLike"):
        if forbidden in endpoint:
            raise RuntimeError(f"verify failed: unexpected macOS behavior {forbidden!r}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()
    if not args.verify_only:
        for patcher in PATCHERS:
            patcher(root)
    verify(root)
    print("Android-like WireGuard profile verified successfully")


if __name__ == "__main__":
    main()
