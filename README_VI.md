# Mihomo v1.19.29 — Windows macOS-like WireGuard v2

Bộ overlay này dùng cho nhánh `macoslike-v1.19.29` tạo từ tag gốc `v1.19.29`.
Nó không dùng nhánh Windows Winsock cũ.

## Cách đưa lên GitHub

Chép đè toàn bộ nội dung overlay vào thư mục gốc repository. Các file cũ trong:

- `.github/workflows/build-windows-macoslike.yml`
- `tools/macoslike/`

phải được thay bằng bản v2 này. Sau đó commit trực tiếp vào nhánh `macoslike-v1.19.29` và chạy workflow **Build Windows macOS-like Mihomo v2**.

## Artifact

Workflow tạo:

```text
verge-mihomo-windows-macoslike-v2-amd64.zip
├── verge-mihomo.exe
├── wintun.dll
├── BUILD_INFO.txt
├── SHA256SUMS.txt
├── LICENSE-mihomo.txt
└── LICENSE-wintun.txt
```

Tên `verge-mihomo.exe` và `wintun.dll` giữ đúng để Clash Verge sử dụng.

## Phạm vi patch

Chỉ WireGuard outbound dùng profile mới. OpenVPN, MASQUE, listener, tunnel, rule và cơ chế nhiều cổng SOCKS giữ nguyên.

Mỗi WireGuard vẫn tạo một gVisor stack riêng:

```text
SOCKS 10881 -> WG-01 -> stack 01
SOCKS 10882 -> WG-02 -> stack 02
SOCKS 10883 -> WG-03 -> stack 03
```

## Sửa lỗi của v1

Bản v1 cho ra `window=26368`, `WS=7`, DF tắt và option order chưa đúng. Bản v2 sửa chính xác đường tạo active SYN:

- Window: `65535`
- Window Scale: `4`
- TTL/Hop Limit mặc định: `64`
- IPv4 DF: bật trên SYN
- IPv4 ID: `0` cho atomic datagram
- TCP options: `MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding`
- Ephemeral port nội bộ: `49152-65535`
- Không cưỡng chế keepalive 15 giây cho profile này
- MSS vẫn tính từ MTU thực tế, không ép sai thành 1460

Xem `tools/macoslike/EXPECTED_FINGERPRINT.md` trước khi kiểm thử.
