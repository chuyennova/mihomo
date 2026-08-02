#!/usr/bin/env python3
"""Apply the Mihomo v1.19.29 standalone Android-like WireGuard overlay.

Run from the Mihomo repository root after `go mod vendor`.
Only WireGuard outbounds select the Android-like userspace stack. Other gVisor
users remain unchanged. This standalone build does not add a YAML field.
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib

SOURCE_HASHES = {
    "adapter/outbound/wireguard.go": "fc3d6082ffc067c0bad762b6670b6372626aa59767c98c4e92ed3a9d1a2290d8",
    "vendor/github.com/metacubex/sing-wireguard/device_stack.go": "c56e9fc817f88a4649340c1e76b619ba3bf98aaf2b2b9517b3b78e75381dac4e",
    "vendor/github.com/metacubex/sing-wireguard/gonet.go": "ce2d97aacc48768ce853356dcc51a06f0dd993c9918fa4ef7df2febb294f17e0",
    "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go": "f750f90953f7db1acd52b4a81a55460f354260bd06e9535fc7777ac53130b921",
    "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go": "daa09ef779d2a15dca690b2a1d46ec1d5eb1bff15d9e4c59062daac6f84c8e8e",
}

TEST_FILE = "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/android_flowlabel_test.go"


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


def validate_pristine(root: pathlib.Path) -> None:
    for relative, expected in SOURCE_HASHES.items():
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"missing locked source: {path}")
        actual = sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"source lock mismatch: {relative}\n"
                f"expected: {expected}\nactual:   {actual}\n"
                "Use the exact Mihomo v1.19.29 dependencies locked in go.mod."
            )


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
\t\t// Representative Android/mobile WireGuard MTU. Explicit YAML wins.
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
// userspace network stack for one WireGuard outbound. It creates no Windows NIC.
func NewStackDeviceAndroidLike(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, true)
}

func newStackDevice(localAddresses []netip.Prefix, mtu uint32, androidLike bool) (*StackDevice, error) {
\tvar ipv6Protocol stack.NetworkProtocolFactory = ipv6.NewProtocol
\tif androidLike {
\t\tipv6Protocol = ipv6.NewProtocolAndroidLike
\t}
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6Protocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcp.NewProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
\tif androidLike {
\t\t// Linux/Android default local ephemeral range. PortManager is per stack,
\t\t// so concurrent WireGuard outbounds remain isolated.
\t\tif err := ipStack.SetPortRange(32768, 60999); err != nil {
\t\t\tipStack.Close()
\t\t\treturn nil, E.New("set Android-like ephemeral port range: ", err.String())
\t\t}
\t}
""",
        "sing-wireguard Android-like constructor",
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
        "sing-wireguard Android-like state",
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
// application explicitly enables it, instead of forcing one 15-second pattern.
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
        """import (
\t"fmt"
\t"math"
\t"reflect"
""",
        """import (
\t"encoding/binary"
\t"fmt"
\t"math"
\t"math/bits"
\t"reflect"
""",
        "gVisor IPv6 Android-like imports",
    )
    text = replace_once(
        text,
        """\t// DefaultTTL is the default hop limit for IPv6 Packets egressed by
\t// Netstack.
\tDefaultTTL = 64

\t// buckets for fragment identifiers
""",
        """\t// DefaultTTL is the default hop limit for IPv6 Packets egressed by
\t// Netstack.
\tDefaultTTL = 64

\tipv6FlowLabelMask          = 0x000fffff
\tipv6FlowLabelStatelessFlag = 0x00080000

\t// buckets for fragment identifiers
""",
        "gVisor IPv6 flow-label mask",
    )
    helper_anchor = """const (
\tforwardingDisabled = 0
\tforwardingEnabled  = 1
)
"""
    helper_code = """const (
\tforwardingDisabled = 0
\tforwardingEnabled  = 1
)

func sipRound(v0, v1, v2, v3 *uint64) {
\t*v0 += *v1
\t*v1 = bits.RotateLeft64(*v1, 13)
\t*v1 ^= *v0
\t*v0 = bits.RotateLeft64(*v0, 32)
\t*v2 += *v3
\t*v3 = bits.RotateLeft64(*v3, 16)
\t*v3 ^= *v2
\t*v0 += *v3
\t*v3 = bits.RotateLeft64(*v3, 21)
\t*v3 ^= *v0
\t*v2 += *v1
\t*v1 = bits.RotateLeft64(*v1, 17)
\t*v1 ^= *v2
\t*v2 = bits.RotateLeft64(*v2, 32)
}

// sipHash24 implements SipHash-2-4. Linux uses a per-network-namespace SipHash
// secret for automatic IPv6 flow labels so labels remain stable per flow while
// not exposing a weak boot-time hash secret on the wire.
func sipHash24(k0, k1 uint64, data []byte) uint64 {
\tv0 := k0 ^ 0x736f6d6570736575
\tv1 := k1 ^ 0x646f72616e646f6d
\tv2 := k0 ^ 0x6c7967656e657261
\tv3 := k1 ^ 0x7465646279746573
\toriginalLength := len(data)
\tfor len(data) >= 8 {
\t\tm := binary.LittleEndian.Uint64(data[:8])
\t\tv3 ^= m
\t\tsipRound(&v0, &v1, &v2, &v3)
\t\tsipRound(&v0, &v1, &v2, &v3)
\t\tv0 ^= m
\t\tdata = data[8:]
\t}
\tb := uint64(originalLength) << 56
\tfor i, value := range data {
\t\tb |= uint64(value) << (8 * i)
\t}
\tv3 ^= b
\tsipRound(&v0, &v1, &v2, &v3)
\tsipRound(&v0, &v1, &v2, &v3)
\tv0 ^= b
\tv2 ^= 0xff
\tfor i := 0; i < 4; i++ {
\t\tsipRound(&v0, &v1, &v2, &v3)
\t}
\treturn v0 ^ v1 ^ v2 ^ v3
}
"""
    text = replace_once(text, helper_anchor, helper_code, "gVisor SipHash helper")
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
\t\tFlowLabel:         params.IPv6FlowLabel & ipv6FlowLabelMask,
\t\tSrcAddr:           srcAddr,
""",
        "gVisor IPv6 header flow label",
    )
    text = replace_once(
        text,
        """func (e *endpoint) WritePacket(r *stack.Route, params stack.NetworkHeaderParams, pkt *stack.PacketBuffer) tcpip.Error {
\tdstAddr := r.RemoteAddress()
\tif err := addIPHeader(r.LocalAddress(), dstAddr, pkt, params, nil /* extensionHeaders */); err != nil {
""",
        """func (e *endpoint) WritePacket(r *stack.Route, params stack.NetworkHeaderParams, pkt *stack.PacketBuffer) tcpip.Error {
\tdstAddr := r.RemoteAddress()
\tif e.protocol.androidLike && params.IPv6FlowLabel == 0 {
\t\tparams.IPv6FlowLabel = e.protocol.autoFlowLabel(
\t\t\tr.LocalAddress(),
\t\t\tdstAddr,
\t\t\tparams.Protocol,
\t\t\tpkt.TransportHeader().Slice(),
\t\t)
\t}
\tif err := addIPHeader(r.LocalAddress(), dstAddr, pkt, params, nil /* extensionHeaders */); err != nil {
""",
        "gVisor IPv6 automatic flow label",
    )
    text = replace_once(
        text,
        """type protocol struct {
\tstack   *stack.Stack
\toptions Options

\tmu protocolMu
""",
        """type protocol struct {
\tstack          *stack.Stack
\toptions        Options
\tandroidLike    bool     `state:\"nosave\"`
\tflowLabelKey   [2]uint64 `state:\"nosave\"`

\tmu protocolMu
""",
        "gVisor IPv6 protocol Android-like state",
    )
    method_anchor = """// Number returns the ipv6 protocol number.
func (p *protocol) Number() tcpip.NetworkProtocolNumber {
"""
    method_code = """// autoFlowLabel follows Linux's automatic-label shape: a keyed hash of the
// flow identity, a 16-bit rotate, and the low 20 bits. Android/Linux defaults
// reserve the upper half of the label space for stateless automatic labels.
// TCP/UDP use the 5-tuple; ICMPv6 also includes type, code and identifier.
func (p *protocol) autoFlowLabel(src, dst tcpip.Address, proto tcpip.TransportProtocolNumber, transportHeader []byte) uint32 {
\tvar flow [56]byte
\tn := copy(flow[:], src.AsSlice())
\tn += copy(flow[n:], dst.AsSlice())
\tflow[n] = byte(proto)
\tn++
\tswitch proto {
\tcase header.TCPProtocolNumber, header.UDPProtocolNumber:
\t\tif len(transportHeader) >= 4 {
\t\t\tn += copy(flow[n:], transportHeader[:4])
\t\t}
\tcase header.ICMPv6ProtocolNumber:
\t\tif len(transportHeader) >= 2 {
\t\t\tn += copy(flow[n:], transportHeader[:2])
\t\t}
\t\tif len(transportHeader) >= 6 {
\t\t\tn += copy(flow[n:], transportHeader[4:6])
\t\t}
\t}
\thash := uint32(sipHash24(p.flowLabelKey[0], p.flowLabelKey[1], flow[:n]))
\treturn (bits.RotateLeft32(hash, 16) & ipv6FlowLabelMask) | ipv6FlowLabelStatelessFlag
}

// Number returns the ipv6 protocol number.
func (p *protocol) Number() tcpip.NetworkProtocolNumber {
"""
    text = replace_once(text, method_anchor, method_code, "gVisor IPv6 autoFlowLabel method")
    text = replace_once(
        text,
        """func NewProtocolWithOptions(opts Options) stack.NetworkProtocolFactory {
\topts.NDPConfigs.validate()

\treturn func(s *stack.Stack) stack.NetworkProtocol {
\t\tp := &protocol{
\t\t\tstack:   s,
\t\t\toptions: opts,
\t\t}
""",
        """func NewProtocolWithOptions(opts Options) stack.NetworkProtocolFactory {
\treturn newProtocolWithOptions(opts, false)
}

// NewProtocolAndroidLike preserves normal Linux-oriented IPv6 behavior and
// enables Linux/Android-style automatic flow labels only for the selecting
// WireGuard stack.
func NewProtocolAndroidLike(s *stack.Stack) stack.NetworkProtocol {
\treturn newProtocolWithOptions(Options{}, true)(s)
}

func newProtocolWithOptions(opts Options, androidLike bool) stack.NetworkProtocolFactory {
\topts.NDPConfigs.validate()

\treturn func(s *stack.Stack) stack.NetworkProtocol {
\t\tp := &protocol{
\t\t\tstack:       s,
\t\t\toptions:     opts,
\t\t\tandroidLike: androidLike,
\t\t}
\t\tif androidLike {
\t\t\trng := s.SecureRNG()
\t\t\tp.flowLabelKey[0] = rng.Uint64()
\t\t\tp.flowLabelKey[1] = rng.Uint64()
\t\t}
""",
        "gVisor IPv6 Android-like constructor",
    )
    write(path, text)


def create_flowlabel_tests(root: pathlib.Path) -> None:
    path = root / TEST_FILE
    write(
        path,
        """package ipv6

import (
\t"encoding/binary"
\t"testing"

\t"github.com/metacubex/gvisor/pkg/tcpip"
\t"github.com/metacubex/gvisor/pkg/tcpip/header"
)

func TestSipHash24ReferenceVectors(t *testing.T) {
\tvar key [16]byte
\tfor i := range key {
\t\tkey[i] = byte(i)
\t}
\tk0 := binary.LittleEndian.Uint64(key[0:8])
\tk1 := binary.LittleEndian.Uint64(key[8:16])
\tvectors := []uint64{
\t\t0x726fdb47dd0e0e31,
\t\t0x74f839c593dc67fd,
\t\t0x0d6c8009d9a94f5a,
\t\t0x85676696d7fb7e2d,
\t}
\tmessage := make([]byte, len(vectors)-1)
\tfor i := range message {
\t\tmessage[i] = byte(i)
\t}
\tfor length, expected := range vectors {
\t\tif got := sipHash24(k0, k1, message[:length]); got != expected {
\t\t\tt.Fatalf("length %d: got %#016x, want %#016x", length, got, expected)
\t\t}
\t}
}

func TestAndroidAutoFlowLabelStablePerFlow(t *testing.T) {
\tp := protocol{androidLike: true}
\tp.flowLabelKey[0] = 0x0706050403020100
\tp.flowLabelKey[1] = 0x0f0e0d0c0b0a0908
\tsrc := tcpip.AddrFrom16([16]byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1})
\tdst := tcpip.AddrFrom16([16]byte{0x20, 0x01, 0x0d, 0xb8, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 2})
\ttcpPorts := []byte{0x80, 0x00, 0x01, 0xbb}
\tfirst := p.autoFlowLabel(src, dst, header.TCPProtocolNumber, tcpPorts)
\tsecond := p.autoFlowLabel(src, dst, header.TCPProtocolNumber, tcpPorts)
\tif first != second {
\t\tt.Fatalf("same flow changed label: %#x != %#x", first, second)
\t}
\tif first > ipv6FlowLabelMask {
\t\tt.Fatalf("label exceeds 20 bits: %#x", first)
\t}
\tif first&ipv6FlowLabelStatelessFlag == 0 {
\t\tt.Fatalf("automatic label is outside Linux stateless range: %#x", first)
\t}
\totherPorts := []byte{0x80, 0x01, 0x01, 0xbb}
\tif other := p.autoFlowLabel(src, dst, header.TCPProtocolNumber, otherPorts); other == first {
\t\tt.Fatalf("different flow unexpectedly reused label %#x", first)
\t}

\totherStack := protocol{androidLike: true}
\totherStack.flowLabelKey[0] = 0x0807060504030201
\totherStack.flowLabelKey[1] = 0x100f0e0d0c0b0a09
\tif other := otherStack.autoFlowLabel(src, dst, header.TCPProtocolNumber, tcpPorts); other == first {
\t\tt.Fatalf("different per-stack secret unexpectedly reused label %#x", first)
\t}

\ticmpEchoA := []byte{128, 0, 0, 0, 0x12, 0x34}
\ticmpEchoB := []byte{128, 0, 0, 0, 0x12, 0x35}
\tlabelA := p.autoFlowLabel(src, dst, header.ICMPv6ProtocolNumber, icmpEchoA)
\tlabelB := p.autoFlowLabel(src, dst, header.ICMPv6ProtocolNumber, icmpEchoB)
\tif labelA == labelB {
\t\tt.Fatalf("different ICMPv6 identifiers unexpectedly reused label %#x", labelA)
\t}
}
""",
    )


PATCHERS = (
    patch_mihomo,
    patch_sing_device_stack,
    patch_sing_gonet,
    patch_stack_registration,
    patch_ipv6,
)


def verify(root: pathlib.Path) -> None:
    checks = {
        "adapter/outbound/wireguard.go": (
            "mtu = 1360",
            "NewStackDeviceAndroidLike",
        ),
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": (
            "func NewStackDeviceAndroidLike",
            "ipv6.NewProtocolAndroidLike",
            "SetPortRange(32768, 60999)",
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
            "func NewProtocolAndroidLike",
            "func sipHash24",
            "func (p *protocol) autoFlowLabel",
            "(bits.RotateLeft32(hash, 16) & ipv6FlowLabelMask) | ipv6FlowLabelStatelessFlag",
            "FlowLabel:         params.IPv6FlowLabel & ipv6FlowLabelMask",
        ),
        TEST_FILE: (
            "TestSipHash24ReferenceVectors",
            "TestAndroidAutoFlowLabelStablePerFlow",
        ),
    }
    for relative, markers in checks.items():
        text = read(root / relative)
        for marker in markers:
            if marker not in text:
                raise RuntimeError(f"verify failed: {relative} missing {marker!r}")

    device = read(root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go")
    for forbidden in (
        "tcp.NewProtocolAndroidLike",
        "udp.NewProtocolAndroidLike",
        "SetPortRange(49152, 65535)",
    ):
        if forbidden in device:
            raise RuntimeError(f"verify failed: unexpected non-Android behavior {forbidden!r}")

    ipv6_text = read(root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go")
    for forbidden in ("crypto/sha256", "if label == 0", "return 1"):
        if forbidden in ipv6_text:
            raise RuntimeError(f"verify failed: obsolete flow-label behavior {forbidden!r}")


def already_patched(root: pathlib.Path) -> bool:
    paths = (
        root / "adapter/outbound/wireguard.go",
        root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go",
        root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go",
    )
    return all(path.is_file() for path in paths) and all(
        marker in read(path)
        for path, marker in zip(
            paths,
            ("NewStackDeviceAndroidLike", "SetPortRange(32768, 60999)", "func sipHash24"),
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()

    if args.verify_only:
        verify(root)
        print("Android-like v1.1.0 WireGuard overlay verified successfully")
        return

    if already_patched(root):
        verify(root)
        print("Android-like v1.1.0 overlay is already applied and verified")
        return

    validate_pristine(root)
    for patcher in PATCHERS:
        patcher(root)
    create_flowlabel_tests(root)
    verify(root)
    print("Android-like v1.1.0 WireGuard overlay applied and verified successfully")


if __name__ == "__main__":
    main()
