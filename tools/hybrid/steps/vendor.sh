#!/usr/bin/env bash
set -Eeuo pipefail

# The Windows/Wintun source introduces Windows-only module imports. The four-
# profile source must be normalized with `go mod tidy` before vendoring; merely
# running `go mod download` is not sufficient and makes `go mod vendor` stop
# with "updates to go.mod needed".
mkdir -p logs/diagnostics
rm -rf vendor

cp -f go.mod logs/diagnostics/go.mod.before-tidy
cp -f go.sum logs/diagnostics/go.sum.before-tidy
sha256sum go.mod go.sum | tee logs/diagnostics/go-module-hashes.before-tidy.txt

# Match the successful standalone Windows build procedure: tidy first, then
# download and vendor. GOFLAGS=-mod=mod also guarantees that a stale committed
# vendor tree cannot influence module normalization.
GOWORK=off GOFLAGS=-mod=mod go mod tidy -v

cp -f go.mod logs/diagnostics/go.mod.after-tidy
cp -f go.sum logs/diagnostics/go.sum.after-tidy
sha256sum go.mod go.sum | tee logs/diagnostics/go-module-hashes.after-tidy.txt

git diff --no-ext-diff -- go.mod go.sum | tee logs/diagnostics/go-mod-tidy.diff || true

# Tidy may normalize direct/indirect placement, but it must not move the three
# locked Mihomo network dependencies away from the exact commits used by all
# four verified profile overlays.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod

GOWORK=off GOFLAGS=-mod=mod go mod download
GOWORK=off GOFLAGS=-mod=mod go mod vendor

test -f vendor/modules.txt
# Validate the freshly generated vendor tree before applying the macOS/Linux/
# Android profile patches.
GOWORK=off GOFLAGS=-mod=vendor go list -m >/dev/null
sha256sum vendor/modules.txt | tee logs/diagnostics/vendor-modules.sha256
awk '/^# / {print}' vendor/modules.txt > logs/diagnostics/vendor-module-list.txt
