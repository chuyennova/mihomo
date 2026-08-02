#!/usr/bin/env bash
set -euo pipefail
test "$(go list -m)" = "github.com/metacubex/mihomo"
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod
grep -F "network-profile" adapter/outbound/wireguard.go
sha256sum go.mod go.sum adapter/outbound/wireguard.go adapter/outbound/wireguard_system_windows.go
go version
go env GOOS GOARCH GOAMD64 GOMOD GOTOOLCHAIN
