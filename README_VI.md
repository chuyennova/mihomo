# Mihomo 1.19.29 Android-like v1.1.0 — Overlay

Đây chỉ là **gói phụ**, không chứa toàn bộ mã nguồn Mihomo.

## Cài vào GitHub

1. Đứng tại branch `androidlike-v1.19.29` được tạo từ tag `v1.19.29`.
2. Chép toàn bộ nội dung gói này vào thư mục gốc repository.
3. Vào **Actions** → chạy `Build Windows Android-like Mihomo v1.1.0 IPv6`.
4. Tải artifact ZIP, dùng `verge-mihomo.exe` và `wintun.dll` với Clash Verge.

## Cách hoạt động

- Không thêm `network-profile` vào YAML.
- Tất cả WireGuard outbound của core chuyên dụng này dùng Android-like gVisor stack.
- Chạy nhiều WireGuard; mỗi outbound có stack, port state và IPv6 secret riêng.
- YAML có `mtu` thì giữ nguyên; nếu thiếu sẽ mặc định `1360`.

## Nâng cấp v1.1.0

- Giữ nguyên đường TCP/IPv4 gVisor đã khớp fingerprint Android mục tiêu.
- Dải port nội bộ Android/Linux: `32768–60999`.
- IPv6 Flow Label dùng keyed SipHash, ổn định theo flow.
- Flow Label nằm trong dải stateless Linux mặc định `0x80000–0xFFFFF`.
- Áp dụng cho TCP, UDP/QUIC và ICMPv6.
- Không ép TCP keepalive 15 giây cho mọi kết nối Android-like.
