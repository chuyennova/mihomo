#!/usr/bin/env bash
set -euo pipefail
VERSION="v1.19.29-hybrid-4profiles-$(git rev-parse --short HEAD)"
BUILDTIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
go env
go build -v -tags with_gvisor -trimpath \
  -ldflags "-extldflags --static -X github.com/metacubex/mihomo/constant.Version=${VERSION} -X github.com/metacubex/mihomo/constant.BuildTime=${BUILDTIME} -w -s -buildid=" \
  -o dist/verge-mihomo.exe .
