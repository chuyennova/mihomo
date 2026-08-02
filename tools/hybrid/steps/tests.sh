#!/usr/bin/env bash
set -euo pipefail
GOWORK=off GOFLAGS=-mod=vendor go test github.com/metacubex/gvisor/pkg/tcpip/network/ipv6
GOWORK=off GOFLAGS=-mod=vendor go test github.com/metacubex/gvisor/pkg/tcpip/transport/tcp
GOWORK=off GOFLAGS=-mod=vendor go test github.com/metacubex/gvisor/pkg/tcpip/transport/udp
GOWORK=off GOFLAGS=-mod=vendor go test ./adapter/outbound
