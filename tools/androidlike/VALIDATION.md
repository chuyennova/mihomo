# Validation

Workflow tự động:

- khóa đúng Mihomo/sing-wireguard/gVisor;
- vendor dependency trước khi patch;
- exact-match patch và `gofmt`;
- verify profile chỉ tác động WireGuard;
- compile các package đã sửa;
- build Windows amd64 `GOAMD64=v2`, `CGO_ENABLED=0`, tag `with_gvisor`;
- đóng gói đúng `verge-mihomo.exe` và `wintun.dll`.
