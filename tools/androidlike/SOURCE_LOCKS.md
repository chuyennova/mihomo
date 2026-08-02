# Source locks

Overlay chỉ áp dụng cho đúng Mihomo `v1.19.29` và dependency đã khóa trong `go.mod`:

```text
github.com/metacubex/sing-wireguard v0.0.0-20260520151737-7e7c7c1b854c
github.com/metacubex/gvisor v0.0.0-20251227095601-261ec1326fe8
```

SHA-256 nguồn trước khi vá:

```text
adapter/outbound/wireguard.go
fc3d6082ffc067c0bad762b6670b6372626aa59767c98c4e92ed3a9d1a2290d8

vendor/github.com/metacubex/sing-wireguard/device_stack.go
c56e9fc817f88a4649340c1e76b619ba3bf98aaf2b2b9517b3b78e75381dac4e

vendor/github.com/metacubex/sing-wireguard/gonet.go
ce2d97aacc48768ce853356dcc51a06f0dd993c9918fa4ef7df2febb294f17e0

vendor/github.com/metacubex/gvisor/pkg/tcpip/stack/registration.go
f750f90953f7db1acd52b4a81a55460f354260bd06e9535fc7777ac53130b921

vendor/github.com/metacubex/gvisor/pkg/tcpip/network/ipv6/ipv6.go
daa09ef779d2a15dca690b2a1d46ec1d5eb1bff15d9e4c59062daac6f84c8e8e
```

Nếu hash lệch, script dừng thay vì vá nhầm phiên bản.
