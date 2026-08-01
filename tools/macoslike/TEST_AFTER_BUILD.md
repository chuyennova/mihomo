# Kiểm tra sau build v3.2

1. Thay đúng hai file trong thư mục core Clash Verge:

```text
verge-mihomo.exe
wintun.dll
```

2. Tắt hoàn toàn Clash Verge rồi mở lại.
3. Kiểm tra version hoặc SHA-256 để chắc chắn đang chạy EXE v3.2.
4. Dùng một SOCKS listener khóa trực tiếp vào một WireGuard.

## IPv4 mong đợi

```text
Window Size: 65535
Window Scale: 4
TCP Options: MSS, NOP, WINDOW, NOP, NOP, TIMESTAMP, SACK_PERM, EOL
Initial TTL: 64
DF: bật
IPv4 ID: 0
MTU 1360 → MSS 1320
```

Nếu vẫn thấy `26368`, `WS=7` hoặc option order `MSS,NOP,WS,SACK,TS`, đang chạy EXE/patch cũ.

## IPv6 mong đợi

Với MTU `1360`:

```text
Initial Hop Limit: 64
MSS: 1300
Window Size: 65535
Window Scale: 4
TCP Options: MSS,NOP,WS,NOP,NOP,TS,SACK,EOL
Traffic Class: 0 nếu không bật ECN/DSCP
Flow Label: thường khác 0; 0 hiếm vẫn hợp lệ
Extension Header: không có ở SYN thông thường
```

Khi bắt nhiều packet trong cùng một TCP connection, Flow Label phải giống nhau. Khi tạo kết nối mới hoàn toàn, nhãn thường phải đổi. UDP/IPv6 cũng phải có nhãn ổn định theo socket. Nếu nhiều kết nối/socket độc lập đều luôn bằng 0 thì mới coi là bất thường.

Không thể dùng các trường IPv4 `DF`, `IP ID` hoặc header checksum để đánh giá IPv6 vì IPv6 không có các trường đó.
