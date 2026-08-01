# Trạng thái profile v3.2 IPv6

## Đã chỉnh và khóa theo từng WireGuard stack

### TCP chung cho IPv4 và IPv6

- Active-open Window `65535`.
- Window Scale `4`.
- TCP options `MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding`.
- Dải source port nội bộ `49152–65535`.
- SACK, Timestamp và CUBIC.
- Không cưỡng chế keepalive `15 giây`.

### IPv4

- Initial TTL `64`.
- SYN bật DF.
- Atomic IPv4 datagram có ID `0`.
- MSS lấy từ MTU thật.

### IPv6

- Initial Hop Limit `64`.
- MSS lấy từ MTU thật, gồm header IPv6 40 byte.
- Traffic Class lấy từ socket; mặc định `0` khi ứng dụng không đặt DSCP/ECN.
- Không tự thêm extension header vào traffic thông thường.
- Flow Label ngẫu nhiên 20-bit theo đúng phép mask của XNU; giá trị `0` rất hiếm nhưng hợp lệ:
  - TCP: cấp một lần cho endpoint và giữ nguyên trong kết nối.
  - UDP: cấp một lần cho socket; cấp mới sau disconnect.
- Flow Label chỉ được bật ở stack WireGuard macOS-like; stack mặc định không đổi.

## Không cam kết quá mức

Bản này đảm bảo core phát đúng profile được định nghĩa ở trên. Nó không tuyên bố sao chép bit-for-bit mọi biến thể của mọi phiên bản macOS, vì XNU và cấu hình runtime có thể thay đổi theo phiên bản, ứng dụng, MTU, ECN và route. Các hành vi dài hạn như delayed ACK, recovery, RTO, ISN và toàn bộ ICMPv6/PMTUD vẫn cần PCAP ngoài Internet nếu muốn hiệu chỉnh sâu hơn.

## Sửa lỗi tương thích gVisor UDP trong v3.2

- Không thay chữ ký hàm nội bộ `udp.newEndpoint`, vì `udp/forwarder.go` cũng gọi hàm này.
- Endpoint tạo qua protocol macOS-like được gắn profile sau khi constructor gốc hoàn tất.
- Endpoint tạo bởi UDP forwarder vẫn dùng hành vi mặc định và không bị nil-pointer khi disconnect.
