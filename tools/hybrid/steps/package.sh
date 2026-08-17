#!/usr/bin/env bash
set -euo pipefail
cd dist
sha256sum verge-mihomo.exe wintun.dll > SHA256SUMS.txt
zip -9 verge-mihomo-v1.19.30-hybrid-windows-amd64-v1.zip verge-mihomo.exe wintun.dll LICENSE-wintun.txt SHA256SUMS.txt
