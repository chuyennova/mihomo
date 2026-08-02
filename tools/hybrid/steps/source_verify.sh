#!/usr/bin/env bash
set -euo pipefail

# This step runs before `go mod vendor`. Never let a stale or partial vendor/
# directory affect source-lock verification. Parse the module path directly.
module_path="$(awk '$1 == "module" { print $2; exit }' go.mod)"
test "$module_path" = "github.com/metacubex/mihomo"

grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod
grep -F "network-profile" adapter/outbound/wireguard.go
sha256sum go.mod go.sum adapter/outbound/wireguard.go adapter/outbound/wireguard_system_windows.go

# GOFLAGS=-mod=mod explicitly ignores any stale committed vendor tree.
GOFLAGS=-mod=mod go version
GOFLAGS=-mod=mod go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN
