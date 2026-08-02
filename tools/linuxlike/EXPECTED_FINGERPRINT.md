# Expected Linux-like network profile v3

- Scope: chỉ WireGuard outbound.
- TCP options: giữ thứ tự Linux gốc của gVisor.
- TTL/Hop Limit: `64`.
- Ephemeral ports: `32768–60999`.
- TCP SYN window: gần `65535`, làm tròn theo MSS.
- Window Scale: gVisor tự tính; không ép cứng.
- TCP keepalive: không tự bật.
- IPv4 TCP: DF bật từ SYN; IP ID riêng theo socket và tăng theo segment.
- IPv4 UDP connected: PMTU/DF; IP ID riêng theo socket.
- IPv4 UDP unconnected: khi DF bật dùng atomic IP ID `0`; không giả bộ đếm socket.
- IPv4 packet có DF và vượt MTU: trả `message too long`, không phân mảnh cục bộ.
- IPv6 TCP/UDP: cùng một hash namespace theo từng stack; tuple gồm địa chỉ, port và protocol; xoay trái 16 bit; Flow Label trong dải `0x80000–0xFFFFF`.
- MTU: giữ cấu hình Mihomo; mặc định `1408`.
