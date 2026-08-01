#!/usr/bin/env python3
"""Apply the scoped macOS-like WireGuard stack patch to a vendored Mihomo tree.

Expected execution directory: Mihomo repository root after `go mod vendor`.
The script is deliberately strict: every edit must match exactly once, otherwise
it exits without silently applying a partial patch.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass


@dataclass
class Edit:
    path: pathlib.Path
    description: str


def read(path: pathlib.Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Missing required file: {path}")
    return path.read_text(encoding="utf-8")


def write(path: pathlib.Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 match, found {count}")
    return text.replace(old, new, 1)


def regex_once(text: str, pattern: str, repl: str, label: str) -> str:
    updated, count = re.subn(pattern, repl, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly 1 regex match, found {count}")
    return updated


def patch_mihomo_wireguard(root: pathlib.Path) -> Edit:
    path = root / "adapter/outbound/wireguard.go"
    text = read(path)
    old = "outbound.tunDevice, err = wireguard.NewStackDevice(outbound.localPrefixes, uint32(mtu))"
    new = "outbound.tunDevice, err = wireguard.NewStackDeviceMacOSLike(outbound.localPrefixes, uint32(mtu))"
    text = replace_once(text, old, new, "Mihomo WireGuard constructor")
    write(path, text)
    return Edit(path, "WireGuard only: select the macOS-like stack constructor")


def patch_sing_device_stack(root: pathlib.Path) -> Edit:
    path = root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go"
    text = read(path)
    old = '''func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcp.NewProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t})
'''
    new = '''func NewStackDevice(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, false)
}

// NewStackDeviceMacOSLike creates an independent userspace network stack for a
// WireGuard outbound and enables the scoped Darwin/macOS-like wire profile.
// It does not use the Windows kernel TCP stack.
func NewStackDeviceMacOSLike(localAddresses []netip.Prefix, mtu uint32) (*StackDevice, error) {
\treturn newStackDevice(localAddresses, mtu, true)
}

func newStackDevice(localAddresses []netip.Prefix, mtu uint32, macOSLike bool) (*StackDevice, error) {
\tipStack := stack.New(stack.Options{
\t\tNetworkProtocols:   []stack.NetworkProtocolFactory{ipv4.NewProtocol, ipv6.NewProtocol},
\t\tTransportProtocols: []stack.TransportProtocolFactory{tcp.NewProtocol, udp.NewProtocol, icmp.NewProtocol4, icmp.NewProtocol6},
\t\tHandleLocal:        true,
\t\tMacOSLike:          macOSLike,
\t})
\tif macOSLike {
\t\t// XNU's normal automatic client-port range is 49152-65535.
\t\t// PortManager randomizes the starting offset per stack, while each
\t\t// WireGuard outbound retains a separate PortManager and TCP state.
\t\tif err := ipStack.SetPortRange(49152, 65535); err != nil {
\t\t\treturn nil, E.New("set macOS-like ephemeral port range: ", err.String())
\t\t}
\t}
'''
    text = replace_once(text, old, new, "sing-wireguard stack constructor")
    write(path, text)
    return Edit(path, "Add per-WireGuard macOS-like stack constructor and XNU port range")


def patch_sing_gonet(root: pathlib.Path) -> Edit:
    path = root / "vendor/github.com/metacubex/sing-wireguard/gonet.go"
    text = read(path)
    old = '''\t// sing-box added: set keepalive
\tep.SocketOptions().SetKeepAlive(true)
\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveIdle)
\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\tep.SetSockOpt(&keepAliveInterval)
'''
    new = '''\t// Preserve the historical sing-wireguard 15-second keepalive only for
\t// ordinary stacks. A normal macOS socket does not have SO_KEEPALIVE forced
\t// on for every outbound connection, so the macOS-like profile leaves it off
\t// unless the application explicitly requests it.
\tif !s.MacOSLike() {
\t\tep.SocketOptions().SetKeepAlive(true)
\t\tkeepAliveIdle := tcpip.KeepaliveIdleOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveIdle)
\t\tkeepAliveInterval := tcpip.KeepaliveIntervalOption(15 * time.Second)
\t\tep.SetSockOpt(&keepAliveInterval)
\t}
'''
    text = replace_once(text, old, new, "sing-wireguard keepalive block")
    write(path, text)
    return Edit(path, "Do not force the 15-second sing-wireguard keepalive on macOS-like stacks")


def patch_gvisor_stack(root: pathlib.Path) -> Edit:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/stack.go"
    text = read(path)

    text = replace_once(
        text,
        '''\t// handleLocal allows non-loopback interfaces to loop packets.
\thandleLocal bool
''',
        '''\t// handleLocal allows non-loopback interfaces to loop packets.
\thandleLocal bool

\t// macOSLike enables narrowly scoped wire-format behavior used by the
\t// Mihomo WireGuard macOS-like profile. It is per Stack, never global.
\tmacOSLike bool
''',
        "gVisor Stack field",
    )

    text = replace_once(
        text,
        '''\t// HandleLocal indicates whether packets destined to their source
\t// should be handled by the stack internally (true) or outside the
\t// stack (false).
\tHandleLocal bool
''',
        '''\t// HandleLocal indicates whether packets destined to their source
\t// should be handled by the stack internally (true) or outside the
\t// stack (false).
\tHandleLocal bool

\t// MacOSLike enables a per-stack Darwin/macOS-like wire profile. It is
\t// intentionally disabled by default so other gVisor users are unchanged.
\tMacOSLike bool
''',
        "gVisor Options field",
    )

    text = replace_once(
        text,
        '''\t\thandleLocal:                  opts.HandleLocal,
''',
        '''\t\thandleLocal:                  opts.HandleLocal,
\t\tmacOSLike:                 opts.MacOSLike,
''',
        "gVisor Stack initialization",
    )

    text = replace_once(
        text,
        '''func (s *Stack) Clock() tcpip.Clock {
\treturn s.clock
}
''',
        '''func (s *Stack) Clock() tcpip.Clock {
\treturn s.clock
}

// MacOSLike reports whether this independent stack uses the scoped
// Darwin/macOS-like wire profile.
func (s *Stack) MacOSLike() bool {
\treturn s.macOSLike
}
''',
        "gVisor Stack profile getter",
    )

    write(path, text)
    return Edit(path, "Add a per-stack profile flag without changing global gVisor defaults")


def patch_gvisor_connect(root: pathlib.Path) -> Edit:
    path = root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go"
    text = read(path)

    text = replace_once(
        text,
        "func makeSynOptions(opts header.TCPSynOptions) []byte {",
        "func makeDefaultSynOptions(opts header.TCPSynOptions) []byte {",
        "rename default gVisor SYN encoder",
    )

    anchor = '''\treturn options[:offset]
}

// tcpFields is a struct to carry different parameters required by the
'''
    insertion = '''\treturn options[:offset]
}

// makeDarwinSynOptions follows XNU's documented SYN option packing order:
// MSS, NOP, Window Scale, SACK Permitted, Timestamp. XNU terminates and pads
// an unaligned option list with EOL/zero bytes rather than Linux-style NOPs.
func makeDarwinSynOptions(opts header.TCPSynOptions) []byte {
\toptions := getOptions()
\toffset := header.EncodeMSSOption(uint32(opts.MSS), options)

\tif opts.WS >= 0 {
\t\toffset += header.EncodeNOP(options[offset:])
\t\toffset += header.EncodeWSOption(opts.WS, options[offset:])
\t}
\tif opts.SACKPermitted {
\t\toffset += header.EncodeSACKPermittedOption(options[offset:])
\t}
\tif opts.TS {
\t\t// XNU aligns Timestamp so the option kind begins at offset 2 mod 4.
\t\tfor offset == 0 || offset%4 != 2 {
\t\t\toffset += header.EncodeNOP(options[offset:])
\t\t}
\t\toffset += header.EncodeTSOption(opts.TSVal, opts.TSEcr, options[offset:])
\t}

\tif offset%4 != 0 {
\t\t// TCP End of Option List is zero; the remaining bytes are zero padding.
\t\toptions[offset] = 0
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
'''
    text = replace_once(text, anchor, insertion, "insert Darwin SYN encoder")

    text = replace_once(
        text,
        "\ttf.opts = makeSynOptions(opts)",
        "\ttf.opts = makeSynOptions(opts, e.stack.MacOSLike())",
        "select SYN encoder per stack",
    )

    write(path, text)
    return Edit(path, "Use XNU SYN option order and EOL padding only for the macOS-like stack")


def verify(root: pathlib.Path) -> None:
    checks = {
        root / "adapter/outbound/wireguard.go": ["NewStackDeviceMacOSLike"],
        root / "vendor/github.com/metacubex/sing-wireguard/device_stack.go": [
            "func NewStackDeviceMacOSLike",
            "SetPortRange(49152, 65535)",
            "MacOSLike:          macOSLike",
        ],
        root / "vendor/github.com/metacubex/sing-wireguard/gonet.go": ["if !s.MacOSLike()"],
        root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/stack.go": [
            "MacOSLike bool",
            "func (s *Stack) MacOSLike() bool",
        ],
        root / "vendor/github.com/metacubex/gvisor/pkg/tcpip/transport/tcp/connect.go": [
            "func makeDarwinSynOptions",
            "MSS, NOP, Window Scale, SACK Permitted, Timestamp",
            "makeSynOptions(opts, e.stack.MacOSLike())",
        ],
    }
    for path, needles in checks.items():
        text = read(path)
        for needle in needles:
            if needle not in text:
                raise RuntimeError(f"Verification failed: {needle!r} missing from {path}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="Mihomo repository root")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    root = pathlib.Path(args.root).resolve()

    try:
        if not args.verify_only:
            edits = [
                patch_mihomo_wireguard(root),
                patch_sing_device_stack(root),
                patch_sing_gonet(root),
                patch_gvisor_stack(root),
                patch_gvisor_connect(root),
            ]
            for edit in edits:
                print(f"PATCHED: {edit.path.relative_to(root)} — {edit.description}")
        verify(root)
        print("macOS-like WireGuard patch verification: OK")
        return 0
    except Exception as exc:  # strict build failure is intentional
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
