# Fingerprint mục tiêu

## IPv4 với MTU 1360

```text
Initial TTL: 64
TOS/ECN: 0 / Not-ECT
MSS: 1320
Window: 26368
Window Scale: 7
Options: MSS,SACK,Timestamp,NOP,WindowScale
JA4T: 26368_2-4-8-1-3_1320_7
DF/IPID: giữ nguyên hành vi gVisor đã đo thực tế
```

Source port, IPID, sequence và timestamp phải thay đổi tự nhiên; không hardcode giá trị của một lần đo.

## IPv6 với MTU 1360

```text
Hop Limit: 64
Traffic Class: 0
MSS: 1300
Window: 25984
Window Scale: 7
Options: MSS,SACK,Timestamp,NOP,WindowScale
Ephemeral ports: 32768–60999
Flow Label: 0x80000–0xFFFFF, ổn định trong cùng flow
```

IPv6 Flow Label được tạo riêng theo mỗi WireGuard stack và theo flow TCP, UDP/QUIC hoặc ICMPv6.
