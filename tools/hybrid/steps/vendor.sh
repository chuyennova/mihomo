#!/usr/bin/env bash
set -euo pipefail
GOFLAGS=-mod=mod go mod download
GOFLAGS=-mod=mod go mod vendor
