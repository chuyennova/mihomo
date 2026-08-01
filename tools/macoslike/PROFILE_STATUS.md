# Trạng thái profile macOS-like

## Đã sửa — độ tin cậy cao

| Thành phần | Mihomo/gVisor gốc | Profile mới | Căn cứ |
|---|---|---|---|
| TCP SYN option order | Linux-like: MSS, SACK, TS, NOP, WS | XNU: MSS, NOP, WS, SACK, TS | `xnu/bsd/netinet/tcp_output.c` |
| TCP option tail padding | NOP | EOL + zero | `tcp_output.c` |
| Ephemeral port range | Bắt đầu từ 16000 | 49152–65535 | `xnu/bsd/netinet/in_pcb.c` |
| Keepalive | Ép bật 15s/15s cho mọi TCP dial | Không ép bật trên profile | macOS không bật SO_KEEPALIVE cho mọi socket mặc định |
| Phạm vi profile | Có nguy cơ global | Cờ riêng cho từng `stack.Stack` | đảm bảo nhiều WG độc lập |

## Đã gần XNU nên giữ nguyên

- IPv4 TTL mặc định: 64.
- IPv6 Hop Limit mặc định: 64.
- TCP timestamp granularity: khoảng 1 ms.
- SACK: bật.
- Congestion control: CUBIC.
- IPv4 atomic packet với DF: IP ID bằng 0 theo RFC 6864.
- MSS: tính từ MTU của route; không khóa cứng.

## Chưa được phép đoán — cần PCAP để hiệu chỉnh

- SYN advertised window và Window Scale theo phiên bản macOS.
- ECN/AccECN trên từng loại mạng.
- Initial congestion window và biến thể CUBIC của XNU.
- Delayed ACK, ACK ratio, ACK timer.
- RTO, TLP, RACK/SACK recovery và retransmission schedule.
- IPv6 flow label.
- UDP buffer/ICMP behavior.
- Source-port selection sequence ngoài dải port.
- QUIC transport parameters: phần lớn do Chromium, không phải TCP stack Mihomo.

## Intel và Apple Silicon

Không tạo hai profile riêng ở giai đoạn này. Cùng phiên bản macOS dùng chung XNU TCP/IP code; phiên bản macOS, interface, MTU và router có ảnh hưởng lớn hơn kiến trúc CPU. Chỉ tách profile khi PCAP thực tế cho thấy khác biệt ổn định.
