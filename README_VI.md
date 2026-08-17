# Mihomo v1.19.30 Hybrid 4 Network Profiles — Windows / Clash Verge

Đây là **overlay**, không phải toàn bộ source Mihomo. Nền bắt buộc là upstream sạch `v1.19.30`.

## Mục tiêu

Một `verge-mihomo.exe` chạy trên Windows/Clash Verge, chọn fingerprint mạng trước theo từng WireGuard outbound:

```yaml
network-profile: windows
network-profile: macos
network-profile: linux
network-profile: android
```

- `windows`: Wintun + Winsock/Windows TCP-IP thật, mỗi outbound một adapter lazy.
- `macos`: gVisor v1.19.30 đã port profile macOS-like.
- `linux`: gVisor v1.19.30 đã port profile Linux-like.
- `android`: gVisor v1.19.30 đã port profile Android-like.

## Khác biệt quan trọng so với hybrid v1.19.29

v1.19.30 upstream đã có `ip-stack` (`auto`, `gvisor`, `mips`). Overlay này **không xóa hoặc thay thế** kiến trúc mới đó.

- Không khai báo `network-profile` -> dùng nguyên `ip-stack` upstream v1.19.30.
- `network-profile: windows` -> `ip-stack.mode` phải bỏ trống hoặc `auto`.
- `network-profile: macos|linux|android` -> dùng gVisor profile-aware; không cho `ip-stack.mode: mips`.
- Build hybrid phải có tag `with_gvisor`.

AmneziaWG v3 của v1.19.30 được giữ nguyên trong đường tạo WireGuard engine.

## MTU

- `android`: mặc định 1360 nếu YAML không khai báo `mtu`.
- `windows`, `macos`, `linux`, và upstream/no-profile: mặc định 1408.
- YAML có `mtu`: luôn dùng đúng giá trị YAML.

## Cách dùng trên GitHub Web

1. Tạo branch `hybrid-v1.19.30` từ tag upstream sạch `v1.19.30`.
2. Chép đè toàn bộ nội dung ZIP overlay này vào root branch đó.
3. Commit.
4. Vào **Actions** -> **Build Windows Hybrid WireGuard Profiles v1.19.30 v1**.
5. Chờ workflow hoàn tất.

Artifact binary gồm:

- `verge-mihomo.exe`
- `wintun.dll`
- `LICENSE-wintun.txt`
- `SHA256SUMS.txt`
- `verge-mihomo-v1.19.30-hybrid-windows-amd64-v1.zip`

Artifact log luôn được upload kể cả build lỗi và chứa `full-build.log`, log từng bước, diagnostics, summary và source locks.

## Kiểm tra runtime

Khi profile được dùng lần đầu, log phải cho biết stack đã chọn. Windows sẽ tạo Wintun riêng; macOS/Linux/Android không tạo Wintun riêng mà tạo userspace gVisor stack riêng.

Xem `tools/hybrid/example-multi-wireguard.yaml` để kiểm thử bốn cổng độc lập.
