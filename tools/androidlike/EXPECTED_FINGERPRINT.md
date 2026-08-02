# Expected network profile

Với WireGuard MTU `1360`:

```text
IPv4 TCP SYN
Initial TTL: 64
TOS / ECN: 0 / Not-ECT
MSS: 1320
Window: 26368
Window Scale: 7
Options: MSS,SACK,Timestamp,NOP,WindowScale
JA4T: 26368_2-4-8-1-3_1320_7

IPv6 TCP SYN
Hop Limit: 64
Traffic Class: 0 mặc định
MSS: 1300
Window: 25984
Window Scale: 7
Options: MSS,SACK,Timestamp,NOP,WindowScale
Flow Label: 20-bit, ổn định theo 5-tuple, secret riêng từng WireGuard stack
```

Source port, IPv4 ID, sequence number và timestamp phải thay đổi tự nhiên; không hardcode giá trị từ một lần đo.
