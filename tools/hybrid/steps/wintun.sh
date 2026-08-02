#!/usr/bin/env bash
set -euo pipefail
curl --fail --location --retry 3 https://www.wintun.net/builds/wintun-0.14.1.zip -o wintun.zip
unzip -j wintun.zip "wintun/bin/amd64/wintun.dll" -d dist
unzip -j wintun.zip "wintun/LICENSE.txt" -d dist
mv dist/LICENSE.txt dist/LICENSE-wintun.txt
