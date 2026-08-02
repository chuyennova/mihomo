# Kiểm tra sau khi build

## IPv4

Mở BrowserLeaks TCP qua đúng SOCKS/WireGuard. Với MTU 1360, mục tiêu:

```text
JA4T 26368_2-4-8-1-3_1320_7
TTL 64
MSS 1320
Window 26368
WS 7
Options MSS,SACK,Timestamp,NOP,WindowScale
```

## IPv6

BrowserLeaks TCP hiện không đủ để xác nhận IPv6. Bắt gói sau giải mã tại server WireGuard:

```bash
sudo tcpdump -ni wg0 -vv 'ip6 and (tcp or udp or icmp6)'
```

Wireshark filter cho SYN IPv6:

```text
ipv6 && tcp.flags.syn == 1 && tcp.flags.ack == 0
```

Mục tiêu ở interface WireGuard trước khi forward:

```text
Hop Limit 64
Traffic Class 0
TCP MSS 1300
TCP Window 25984
WS 7
Flow Label 0x80000–0xFFFFF
Cùng một flow: Flow Label không đổi
Flow mới: thường có Flow Label khác
```
