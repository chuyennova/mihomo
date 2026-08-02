# Mihomo v1.19.29 — Windows Android-like WireGuard v1.0.0 IPv6

Overlay build `verge-mihomo.exe` chạy trên Windows/Clash Verge nhưng dùng gVisor Android/Linux-like cho **mọi WireGuard outbound**.

## Đưa lên GitHub

1. Tạo nhánh từ source Mihomo `v1.19.29`, nên đặt tên `androidlike-v1.19.29`.
2. Chép đè toàn bộ nội dung ZIP overlay vào thư mục gốc repository.
3. Commit và chạy workflow:

```text
Build Windows Android-like Mihomo v1.0.0 IPv6
```

Artifact:

```text
verge-mihomo-windows-androidlike-v1.0.0-ipv6-amd64.zip
├── verge-mihomo.exe
├── wintun.dll
├── BUILD_INFO.txt
└── SHA256SUMS.txt
```

## YAML

Không thêm `network-profile`. YAML WireGuard cũ giữ nguyên. Nếu không khai báo `mtu`, core dùng `1360`; nếu đã khai báo thì giữ đúng giá trị YAML.

## Mục tiêu tại MTU 1360

```text
IPv4: TTL 64, MSS 1320, window 26368, WS 7
TCP options: MSS,SACK,Timestamp,NOP,WindowScale
JA4T: 26368_2-4-8-1-3_1320_7
IPv6: Hop Limit 64, MSS 1300, window 25984, WS 7
```

Mỗi WireGuard có gVisor stack, port/state và IPv6 flow-label secret riêng. Không tạo Wintun riêng cho từng WireGuard.

Profile này chỉ thay dấu vết L3/L4 bên trong WireGuard; User-Agent, TLS, HTTP/2 và QUIC vẫn thuộc trình duyệt/GPM.
