# Dấu vết SYN mong đợi của v2

Với IPv4, SACK và Timestamp bật bình thường:

```text
Initial TTL:       64
Window:            65535
Window Scale:      4
IP DF:             1
IPv4 ID:           0 (atomic datagram)
TCP options:       MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding
Option kind order: 2-1-3-1-1-8-4-0
Source port stack: 49152-65535
ECN:               giữ mặc định hiện tại
```

MSS phụ thuộc MTU của WireGuard:

```text
MTU 1360 -> MSS 1320
MTU 1408 -> MSS 1368
MTU 1500 -> MSS 1460
```

Không ép MSS 1460 khi tunnel nhỏ hơn 1500.

## Những phần S9 có thể thay đổi

Sau khi S9 giải mã WireGuard và NAT ra 4G:

- TTL bị giảm theo số hop.
- NAT có thể đổi source port.
- MSS có thể bị firewall/MSS-clamp sửa.
- Router hoặc mạng nhà cung cấp có thể xử lý ECN/fragmentation.

Các trường Window, Window Scale và TCP option order thông thường phải còn nguyên. Nếu chúng không đúng, core hoặc patch chưa được sử dụng đúng.
