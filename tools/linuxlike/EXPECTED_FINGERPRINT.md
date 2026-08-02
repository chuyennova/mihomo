# Expected Linux-like network profile

- Scope: WireGuard outbound only.
- TCP options: giữ thứ tự Linux gốc của gVisor.
- TTL/Hop Limit: `64`.
- Ephemeral ports: `32768–60999`.
- TCP SYN window: gần `65535`, làm tròn theo MSS.
- Window Scale: gVisor tự tính; không ép cứng.
- TCP keepalive: không tự bật.
- IPv4 TCP: DF bật từ SYN; IP ID riêng theo socket và tăng theo packet/segment.
- IPv4 UDP: PMTU mặc định kiểu Linux; DF bật khi phù hợp; datagram quá MTU trả lỗi; IP ID riêng theo socket.
- IPv6 Flow Label: hash ổn định theo flow, dải `0x80000–0xFFFFF`.
- MTU: giữ cấu hình Mihomo; mặc định `1408`.
