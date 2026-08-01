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


def verify(root: pathlib.Path) -> None:
    required = {
        "adapter/outbound/wireguard.go": ["NewStackDeviceMacOSLike"],
        "vendor/github.com/metacubex/sing-wireguard/device_stack.go": [
            "func NewStackDeviceMacOSLike",
            "tcp.NewProtocolMacOSLike",
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
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/endpoint.go": [
            "return math.MaxUint16",
            "return 4",
        ],
        "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": [
            "func makeDarwinSynOptions",
            "header.TCPOptionEOL",
            "tf.df = true",
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
        verify(root)
        print("macOS-like WireGuard v2 patch verification: OK")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
