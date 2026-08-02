# Mihomo v1.19.29 Hybrid — Windows / macOS / Linux / Android

Đây là **overlay**, không chứa lại toàn bộ source Mihomo. Áp toàn bộ file trong ZIP này lên đúng baseline `mihomo-1.19.29(14).zip`, sau đó chạy workflow `Build Windows Hybrid WireGuard Profiles`.

## Đầu ra

- `verge-mihomo.exe`
- `wintun.dll`
- gói ZIP cho Clash Verge trên Windows
- `summary.txt` và `full-build.log` luôn được upload, kể cả build lỗi

## Chọn profile theo từng WireGuard outbound

```yaml
network-profile: windows
network-profile: macos
network-profile: linux
network-profile: android
```

Không khai báo `network-profile` thì mặc định là `windows`.

## Kiến trúc

- `windows`: Wintun/Winsock thật, lazy-create theo từng outbound.
- `macos`: gVisor stack riêng, port 49152–65535, Darwin SYN/window/IPv6 Flow Label.
- `linux`: gVisor stack riêng, Linux port range, PMTU/DF, IPv4 ID, IPv6 Flow Label.
- `android`: gVisor stack riêng, Android/Linux port range, SipHash IPv6 Flow Label; TCP/IPv4 giữ hành vi Android-like đã chốt.

Mỗi outbound có device/stack, mutex, lỗi, retry, port allocator, TCP/UDP và trạng thái Flow Label riêng. Không có biến global chọn profile.

## MTU

- YAML có `mtu`: dùng đúng giá trị YAML.
- Android không khai báo `mtu`: mặc định `1360`.
- Windows/macOS/Linux không khai báo `mtu`: mặc định `1408`.

## Cách áp

1. Giải nén baseline Mihomo v1.19.29 vào repository.
2. Chép đè toàn bộ nội dung overlay này vào root repository.
3. Commit lên branch `hybrid-v1.19.29`.
4. Mở Actions và chạy `Build Windows Hybrid WireGuard Profiles`.
5. Tải artifact binary nếu build thành công; nếu lỗi, tải `hybrid-build-logs-*`.

Không áp tiếp ba overlay macOS/Linux/Android cũ sau overlay này. `apply_hybrid.py` đã hợp nhất chúng ở cấp dependency.

## Trạng thái xác minh

- Đã đối chiếu hash bốn ZIP với các bản trước: nội dung trùng hoàn toàn.
- Đã kiểm tra và gofmt ba file core Mihomo của hybrid.
- Script vá dùng exact-match trên dependency khóa cứng.
- Đã tải đúng các file source tại commit khóa của `sing-wireguard` và gVisor, áp patch thật, verify và `gofmt` thành công trên toàn bộ 13 file dependency bị tác động.
- Môi trường hiện tại không tải được toàn bộ Go module graph và chỉ có Go 1.23.2; compile cuối bằng MetaCubeX Go 1.26 phải được xác nhận bằng workflow GitHub Actions đi kèm. Xem `tools/hybrid/STATIC_CHECK_REPORT.txt`.

## Ghi log CI v2

Workflow v2 gọi mọi script qua `bash`, đồng thời sửa quyền thực thi sau checkout nên không còn phụ thuộc executable bit khi upload từ Windows/GitHub Web. Mỗi bước tạo một file riêng trong `logs/steps/`, ghi chung vào `full-build.log`, lưu exit code trong `.ci-status/` và khi lỗi tạo thêm chẩn đoán trong `logs/diagnostics/`. Bước `Finalize all logs` luôn chạy và không được phép che mất lỗi gốc.
