#!/usr/bin/env bash
set -euo pipefail
go test github.com/metacubex/gvisor/pkg/tcpip/network/ipv6
go test github.com/metacubex/gvisor/pkg/tcpip/transport/tcp
go test github.com/metacubex/gvisor/pkg/tcpip/transport/udp
go test ./adapter/outbound
