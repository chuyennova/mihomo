#!/usr/bin/env bash
set -Eeuo pipefail
mkdir -p logs/diagnostics
rm -rf vendor

cp -f go.mod logs/diagnostics/go.mod.before-tidy
cp -f go.sum logs/diagnostics/go.sum.before-tidy
sha256sum go.mod go.sum | tee logs/diagnostics/go-module-hashes.before-tidy.txt

# Normalize only against v1.19.30's module graph plus the two Windows/Wintun
# dependencies introduced by this overlay.
GOWORK=off GOFLAGS=-mod=mod go mod tidy -v

cp -f go.mod logs/diagnostics/go.mod.after-tidy
cp -f go.sum logs/diagnostics/go.sum.after-tidy
sha256sum go.mod go.sum | tee logs/diagnostics/go-module-hashes.after-tidy.txt
git diff --no-ext-diff -- go.mod go.sum | tee logs/diagnostics/go-mod-tidy.diff || true

# Critical upstream network modules must stay on the v1.19.30 commits.
grep -F "github.com/metacubex/sing-wireguard v0.0.0-20260810013230-110eac03c3f0" go.mod
grep -F "github.com/metacubex/gvisor v0.0.0-20260810011720-3cc44cf9ac22" go.mod
grep -F "github.com/metacubex/wireguard-go v0.0.0-20250820062549-a6cecdd7f57f" go.mod

grep -F "golang.zx2c4.com/wireguard v0.0.0-20250521234502-f333402bd9cb" go.mod
grep -F "golang.zx2c4.com/wireguard/windows v1.0.1" go.mod

GOWORK=off GOFLAGS=-mod=mod go mod download
GOWORK=off GOFLAGS=-mod=mod go mod vendor

test -f vendor/modules.txt
GOWORK=off GOFLAGS=-mod=vendor go list -m >/dev/null
sha256sum vendor/modules.txt | tee logs/diagnostics/vendor-modules.sha256
awk '/^# / {print}' vendor/modules.txt > logs/diagnostics/vendor-module-list.txt
