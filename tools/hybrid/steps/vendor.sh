#!/usr/bin/env bash
set -euo pipefail

# The repository may contain a stale/partial vendor tree from an earlier upload.
# Recreate it deterministically from the locked go.mod/go.sum every run.
rm -rf vendor
GOWORK=off GOFLAGS=-mod=mod go mod download
GOWORK=off GOFLAGS=-mod=mod go mod vendor

test -f vendor/modules.txt
# Validate the freshly generated vendor tree before patching it.
GOWORK=off GOFLAGS=-mod=vendor go list -m >/dev/null
sha256sum vendor/modules.txt
