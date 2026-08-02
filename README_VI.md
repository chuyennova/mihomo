# Mihomo v1.19.29 — Windows Linux-like WireGuard v4

Bản build riêng chạy trên Windows/Clash Verge; mọi WireGuard outbound tự dùng stack Linux-like. **Không có và không cần `network-profile: linux` trong YAML.**

## Dùng trên GitHub

1. Mở branch `linuxlike-v1.19.29` đã tạo từ source Mihomo v1.19.29 gốc.
2. Chép đè toàn bộ nội dung ZIP overlay vào thư mục gốc repository.
3. Commit và chạy workflow:

```text
Build Windows Linux-like Mihomo v4
```

Artifact:

```text
verge-mihomo-windows-linuxlike-v4-amd64.zip
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
- TTL/Hop Limit giữ `64`; source port `32768–60999`.
- SYN receive window gần 65 KB, làm tròn theo MSS; không ép cứng Window Scale.
- Không cưỡng bức TCP keepalive `15/15`.
- TCP/IPv4 bật PMTU/DF từ SYN và dùng IP ID tăng riêng theo socket.
- UDP/IPv4 bật PMTU/DF; chỉ socket UDP đã `connect()` dùng IP ID tăng riêng. UDP `sendto()` chưa kết nối giữ atomic ID bằng `0` khi DF bật.
- Gói IPv4 có DF và gói IPv6 dùng PMTU mà vượt MTU đều trả `message too long`, không bị source-fragment ngoài ý muốn.
- TCP/UDP IPv6 dùng chung flow hash có salt theo từng WireGuard stack, xoay trái 16 bit, đưa vào dải Flow Label stateless và giữ PMTU mặc định kiểu Linux.
- MTU vẫn lấy từ YAML; mặc định Mihomo `1408` không bị ép đổi.

Workflow khóa đúng dependency của Mihomo 1.19.29, patch theo anchor nghiêm ngặt, chạy `gofmt`, verify, compile-check rồi mới build Windows.
