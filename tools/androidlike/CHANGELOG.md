# Changelog

## v1.1.0

- Giảm phạm vi patch: không tạo TCP/UDP protocol Android riêng khi gVisor mặc định đã đúng mục tiêu IPv4.
- Thêm port range `32768–60999` cho từng stack.
- Chuyển IPv6 Flow Label xuống lớp IPv6 chung để bao phủ TCP, UDP/QUIC và ICMPv6.
- Dùng SipHash-2-4 với secret riêng từng stack.
- Thêm rotate 16 bit và Linux stateless flag `0x80000`.
- Thêm unit test SipHash, độ ổn định theo flow, khác biệt theo stack và ICMPv6 identity.
- Thêm khóa SHA nguồn, kiểm tra phạm vi patch và compile gate trong GitHub Actions.
