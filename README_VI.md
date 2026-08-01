# Mihomo 1.19.29 — Windows macOS-like WireGuard build overlay

Gói này được giải nén **đè vào thư mục gốc của nhánh Mihomo 1.19.29** rồi push lên GitHub. Workflow sẽ tự:

1. tải đúng dependency từ `go.mod`;
2. tạo thư mục `vendor`;
3. chỉ chuyển `adapter/outbound/wireguard.go` sang stack macOS-like;
4. giữ OpenVPN và MASQUE dùng `NewStackDevice()` gốc;
5. build Windows amd64 v2 thành đúng `verge-mihomo.exe`;
6. tải `wintun.dll` chính thức, kiểm tra SHA-256 và đóng gói artifact.

## Cách dùng

Sao chép hai thư mục sau vào root repository:

```text
.github/workflows/build-windows-macoslike.yml
tools/macoslike/
```

Sau đó commit và push. Vào **Actions → Build Windows macOS-like Mihomo → Run workflow**. Kết quả tải ở mục Artifacts:

```text
verge-mihomo-windows-macoslike-amd64-v2.zip
├── verge-mihomo.exe
├── wintun.dll
├── LICENSE-mihomo.txt
├── LICENSE-wintun.txt
├── BUILD_INFO.txt
└── SHA256SUMS.txt
```

Không đổi tên `verge-mihomo.exe` hoặc `wintun.dll` khi chép vào Clash Verge.

## Những thay đổi đã được khóa phạm vi

- `adapter/outbound/wireguard.go`: chỉ WireGuard gọi `NewStackDeviceMacOSLike()`.
- `sing-wireguard/device_stack.go`: mỗi WireGuard vẫn có `stack.Stack`, PortManager, TCP/UDP state và địa chỉ riêng.
- `gVisor stack.go`: thêm cờ profile **per-stack**, không dùng biến global.
- `gVisor connect.go`: SYN của profile mới theo thứ tự XNU:

```text
MSS → NOP → Window Scale → SACK Permitted → Timestamp
```

- Padding cuối TCP options dùng EOL/zero theo XNU.
- Dải ephemeral port đổi từ gVisor `16000+` sang XNU `49152–65535`.
- Không ép keepalive 15 giây cho mọi TCP connection của profile macOS-like.
- TTL/Hop Limit 64, SACK và CUBIC vốn đã gần giá trị Unix/macOS nên không sửa mù.

## Nhiều SOCKS và nhiều WireGuard

Logic gốc vẫn giữ nguyên:

```text
SOCKS 10881 → WG-01 → stack macOS-like 01
SOCKS 10882 → WG-02 → stack macOS-like 02
SOCKS 10883 → WG-03 → stack macOS-like 03
```

Một stack lỗi không dùng chung PortManager/TCP state với stack khác.

## Mức độ chính xác

Đây là **baseline có căn cứ từ mã XNU**, không phải tuyên bố “Mac thật 100%”. Các giá trị phụ thuộc phiên bản macOS, MTU và đường truyền như advertised window, Window Scale thực tế, ECN, ACK delay, recovery và IPv6 flow label phải được hiệu chỉnh bằng PCAP thu từ máy Mac mục tiêu và PCAP ở máy chủ ngoài sau S9/NAT.

Không nên khóa MSS thành 1460: Mihomo WireGuard mặc định MTU 1408 nên MSS phải theo Path MTU; ép sai sẽ tạo fingerprint bất thường hoặc phân mảnh.

Xem thêm `tools/macoslike/PROFILE_STATUS.md` và `tools/macoslike/TEST_AFTER_BUILD.md`.
