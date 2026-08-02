# Kiểm tra sau build

1. Thay `verge-mihomo.exe` và `wintun.dll` vào Clash Verge.
2. Dùng YAML WireGuard cũ, không thêm `network-profile`.
3. TCP/IPv4: xác nhận TTL 64, DF, IP ID tăng theo flow, port 32768–60999, SYN Window làm tròn theo MSS.
4. TCP/IPv6: xác nhận Hop Limit 64 và Flow Label ổn định trong cùng flow, khác giữa các flow.
5. UDP/IPv4: thử cả connected UDP và `sendto()` unconnected; kiểm tra DF/IP ID và lỗi khi datagram vượt MTU.
6. UDP/IPv6/QUIC: xác nhận Flow Label dùng cùng quy luật hash như TCP nhưng khác theo protocol/tuple; datagram vượt PMTU phải trả lỗi thay vì tạo Fragment Header ở chế độ mặc định.
7. Xác nhận nhiều WireGuard outbound có state, salt, port và IP ID riêng.

BrowserLeaks chỉ kiểm tra TCP/IPv4. Để xác nhận IPv6 phải bắt PCAP ở đầu ra tunnel và so với máy Linux thật có cùng MTU, cùng đích và cùng loại lưu lượng.
