# Kiểm tra sau build

1. Thay đúng hai file trong thư mục core Clash Verge:

```text
verge-mihomo.exe
wintun.dll
```

2. Tắt hoàn toàn Clash Verge rồi mở lại.
3. Xác nhận Clash Verge đang chạy đúng file mới bằng version hoặc SHA-256.
4. Dùng một cổng SOCKS khóa trực tiếp vào một WireGuard.
5. Kiểm tra TCP fingerprint từ một máy chủ ngoài Internet.

Kết quả chính cần thấy:

```text
Window Size: 65535
Window Scale: 4
TCP Options: MSS, NOP, WINDOW, NOP, NOP, TIMESTAMP, SACK_PERM, EOL
Initial TTL: 64
DF: bật
```

MSS được phép khác 1460 nếu MTU tunnel nhỏ hơn 1500.

Nếu vẫn thấy `26368` và `WS=7`, đang chạy EXE cũ hoặc workflow chưa áp patch v2.

Nếu options vẫn là `MSS,NOP,WS,SACK,TS`, đang chạy patch v1.
