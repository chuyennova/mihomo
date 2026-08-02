# Mihomo v1.19.29 — Windows Linux-like WireGuard v2

Bản build riêng chạy trên Windows/Clash Verge nhưng mọi WireGuard outbound tự dùng stack Linux-like. **Không có và không cần `network-profile: linux` trong YAML.**

## Dùng trên GitHub

1. Tạo branch `linuxlike-v1.19.29` từ source Mihomo v1.19.29 gốc.
2. Chép đè toàn bộ nội dung ZIP overlay vào thư mục gốc repository.
3. Commit và chạy workflow:

```text
Build Windows Linux-like Mihomo v2
```

Artifact:

```text
verge-mihomo-windows-linuxlike-v2-amd64.zip
├── verge-mihomo.exe
├── wintun.dll
├── BUILD_INFO.txt
├── SHA256SUMS.txt
├── LICENSE-mihomo.txt
└── LICENSE-wintun.txt
```

## Phạm vi

Chỉ `adapter/outbound/wireguard.go` gọi constructor Linux-like. OpenVPN, MASQUE, TUN thông thường và các outbound khác giữ nguyên.

## Thay đổi chính

- Giữ TCP SYN option order Linux vốn có của gVisor.
- TTL/Hop Limit giữ `64`.
- Source port `32768–60999`.
- SYN receive window gần 65 KB và làm tròn theo MSS.
- Không cưỡng bức TCP keepalive `15/15`.
- TCP IPv4 bật PMTU/DF từ SYN và dùng IP ID riêng theo socket.
- UDP IPv4 bật PMTU/DF và IP ID riêng theo socket.
- IPv6 TCP/UDP dùng Flow Label ổn định theo flow hash, trong dải stateless Linux.
- MTU vẫn lấy từ YAML; mặc định Mihomo `1408` không bị ép đổi.

Workflow khóa đúng dependency của Mihomo 1.19.29, patch theo anchor nghiêm ngặt, chạy `gofmt`, verify, compile-check và chỉ sau đó mới build Windows.
