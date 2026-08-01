# Dấu vết mong đợi của v3.2.1

## IPv4 TCP SYN

```text
Initial TTL:       64
Window:            65535
Window Scale:      4
DF:                1
IPv4 ID:           0 với atomic datagram
TCP options:       MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding
Option kind order: 2-1-3-1-1-8-4-0
Source port stack: 49152–65535
```

Với MTU `1360`:

```text
IPv4 MSS = 1360 - 20 IPv4 - 20 TCP = 1320
```

## IPv6 TCP SYN

```text
Initial Hop Limit: 64
Traffic Class:     0 khi socket không đặt DSCP/ECN
Flow Label:        0–1048575, ngẫu nhiên theo flow
Window:            65535
Window Scale:      4
TCP options:       MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding
Option kind order: 2-1-3-1-1-8-4-0
Extension Headers: không có ở SYN thông thường
```

Với MTU `1360`:

```text
IPv6 MSS = 1360 - 40 IPv6 - 20 TCP = 1300
```

Flow Label phải:

- Giữ nguyên trên các packet thuộc cùng một TCP connection.
- Thường đổi khi tạo TCP connection mới.
- Thường khác `0`; giá trị `0` có xác suất khoảng 1/1.048.576 và không được coi là lỗi nếu chỉ xuất hiện hiếm.

## IPv6 UDP/QUIC

```text
Hop Limit:         64
Traffic Class:     theo socket, mặc định 0
Flow Label:        ngẫu nhiên 20-bit và ổn định theo UDP socket
Extension Headers: không có ở datagram thông thường
```

QUIC transport fingerprint vẫn do ứng dụng/Chromium quyết định; patch này chỉ điều chỉnh lớp IPv6/UDP của userspace stack.

## Những phần S9 hoặc nhà mạng có thể thay đổi

- Hop Limit/TTL giảm theo số hop.
- NAT có thể đổi source port.
- Firewall có thể MSS-clamp.
- Router có thể xử lý ECN hoặc fragment/Packet Too Big.

TCP Window, Window Scale, option order và Flow Label bình thường phải được giữ nguyên đầu-cuối; nếu Flow Label luôn `0` qua nhiều kết nối độc lập, v3.2.1 có thể chưa được áp hoặc một thiết bị trung gian đã ghi đè.
