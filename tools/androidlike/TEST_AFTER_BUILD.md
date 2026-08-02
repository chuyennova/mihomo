# Kiểm thử sau build

1. Thay `verge-mihomo.exe` và `wintun.dll` trong Clash Verge.
2. Chạy ít nhất hai WireGuard/SOCKS đồng thời để kiểm tra cô lập.
3. Thu PCAP tại máy chủ kiểm thử hoặc endpoint do bạn kiểm soát.
4. Với MTU 1360, kiểm tra IPv4 JA4T `26368_2-4-8-1-3_1320_7`.
5. Kiểm tra IPv6 Flow Label: không đổi trong một flow, khác giữa các flow thông thường.
6. Kiểm tra TCP kết nối lâu không tự phát keepalive theo chu kỳ 15 giây.
7. Kiểm tra IPv4-only, IPv6-only và dual-stack riêng biệt.

TTL quan sát ở đích có thể thấp hơn 64 do số hop thực tế.
