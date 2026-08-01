# Source locks used for this patch

```text
Mihomo base: 1.19.29 (user ZIP mihomo-1.19.29(7).zip)
github.com/metacubex/sing-wireguard:
  v0.0.0-20260520151737-7e7c7c1b854c
github.com/metacubex/gvisor:
  v0.0.0-20251227095601-261ec1326fe8
Wintun:
  0.14.1
  SHA256 07c256185d6ee3652e09fa55c0b673e2624b565e02c4b9091c79ca7d2f24ef51
```

`apply_macoslike.py` dùng exact-match và sẽ dừng build nếu source/dependency thay đổi khiến patch không còn khớp. Đây là chủ ý để tránh tạo binary đã vá thiếu mà không báo lỗi.
