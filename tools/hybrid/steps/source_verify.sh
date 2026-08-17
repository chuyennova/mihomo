#!/usr/bin/env bash
set -euo pipefail

module_path="$(awk '$1 == "module" { print $2; exit }' go.mod)"
test "$module_path" = "github.com/metacubex/mihomo"

# v1.19.30 dependency locks. These are intentionally different from v1.19.29.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod

# Native Windows profile dependencies.
grep -F "golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb" go.mod
grep -F "golang.zx2c4.com/wireguard/windows v1.0.1" go.mod

# Upstream v1.19.30 architecture must remain present.
grep -F 'IPStack IPStackOption `proxy:"ip-stack,omitempty"`' adapter/outbound/wireguard.go
grep -F 'ipStackMips   = "mips"' adapter/outbound/wireguard.go
grep -F 'amneziav3.NewDevice' adapter/outbound/wireguard.go

# Hybrid selector and lazy lifecycle.
grep -F 'NetworkProfile      string `proxy:"network-profile,omitempty"`' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileWindows = "windows"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileMacOS   = "macos"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileLinux   = "linux"' adapter/outbound/wireguard.go
grep -F 'wireGuardProfileAndroid = "android"' adapter/outbound/wireguard.go
grep -F 'func (w *WireGuard) ensureDeviceLocked() error' adapter/outbound/wireguard.go
grep -F 'return 1360' adapter/outbound/wireguard.go
grep -F 'return 1408' adapter/outbound/wireguard.go

# Omitted network-profile must preserve upstream v1.19.30 ip-stack behavior.
grep -F 'case "":' adapter/outbound/wireguard.go
grep -F 'stack, err := newIPStack(w.option.IPStack, w.localPrefixes, w.mtu)' adapter/outbound/wireguard.go

# OS/profile implementations must exist.
test -f adapter/outbound/wireguard_profile_windows.go
test -f adapter/outbound/wireguard_profile_windows_other.go
test -f adapter/outbound/wireguard_profile_gvisor.go
test -f adapter/outbound/wireguard_profile_nogvisor.go
grep -F 'newWindowsNetworkProfileDevice' adapter/outbound/wireguard_profile_windows.go
grep -F 'NewStackDeviceWithProfile' adapter/outbound/wireguard_profile_gvisor.go

sha256sum \
  go.mod go.sum \
  adapter/outbound/wireguard.go \
  adapter/outbound/wireguard_profile_windows.go \
  adapter/outbound/wireguard_profile_windows_other.go \
  adapter/outbound/wireguard_profile_gvisor.go \
  adapter/outbound/wireguard_profile_nogvisor.go

GOFLAGS=-mod=mod go version
GOFLAGS=-mod=mod go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN
