# Kiểm tra sau build

1. Thay `verge-mihomo.exe` và `wintun.dll` vào Clash Verge.
2. Dùng YAML WireGuard cũ, không thêm `network-profile`.
3. Kiểm tra TCP/IPv4 và TCP/IPv6 bằng PCAP tại đầu ra tunnel.
4. Kiểm tra UDP/IPv4 bằng DNS hoặc QUIC; UDP/IPv6 bằng QUIC nếu server hỗ trợ.
5. Xác nhận nhiều WireGuard outbound có source port, IP ID và flow state riêng.

Không kết luận chỉ từ một website fingerprint; nên so PCAP với một máy Ubuntu/Linux thật có cùng MTU và cùng đích kiểm tra.
