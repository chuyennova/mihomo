# Trạng thái profile v2

Đã chỉnh:

- Đường active-open TCP SYN của WireGuard.
- Window 65535 và Window Scale 4.
- Option order và EOL padding theo profile XNU/macOS phổ biến.
- DF trên SYN; gVisor để IPv4 ID bằng 0 cho atomic datagram.
- Dải source port per-stack 49152-65535.
- Bỏ forced keepalive 15 giây cho WireGuard profile mới.
- Cô lập profile theo từng WireGuard stack.

Giữ nguyên có chủ đích:

- MSS theo route MTU.
- TTL/Hop Limit 64 vốn đã phù hợp.
- SACK và CUBIC.
- Listener nhiều SOCKS và SpecialProxy.

Chưa cam kết mô phỏng hoàn toàn mọi hành vi XNU dài hạn như recovery, delayed ACK, ISN và mọi biến thể theo phiên bản macOS. Cần đo PCAP ngoài Internet để hiệu chỉnh tiếp.
