# Integration report — v1.19.30 hybrid 4 profiles

## Thiết kế

v1.19.30 đã refactor WireGuard quanh `IPStackOption`, `ipStack`, `wireguardDevice` và `newIPStack()`. Bản port giữ lớp này làm upstream path và thêm `network-profile` như selector bên ngoài.

### Không có `network-profile`

Đi theo `newIPStack()` của upstream với `ip-stack.mode: auto|gvisor|mips`.

### `windows`

Tạo Wintun lazy theo outbound, cấu hình address/route riêng và tạo socket Winsock bị ghim interface bằng `IP_UNICAST_IF`/`IPV6_UNICAST_IF`. IPv4 TCP không hard-bind `/32`; IPv6/UDP bind địa chỉ tunnel như hybrid v1.19.29 đã kiểm chứng.

### `macos`, `linux`, `android`

`sing-wireguard` mới được mở rộng bằng `NetworkProfile` immutable trên mỗi `StackDevice`. Mỗi outbound tạo stack riêng; không có biến global chọn profile.

## Port gVisor lên commit mới

Không áp nguyên patch v1.19.29. Các thay đổi được rebase lên gVisor `3cc44cf9ac22` và giữ code PMTU/DF mới của upstream v1.19.30.

- macOS: Darwin SYN option order, WS/window, port range, TCP/UDP IPv6 flow label.
- Linux: port range, PMTU/DF, per-socket IPv4 ID, MSS-aware receive window, IPv6 flow label.
- Android: port range, Android IPv6 SipHash flow label, không cưỡng bức TCP keepalive 15/15; Android profile đặt PMTU `DONT` để không bị thay đổi thành DF-on do PMTU default mới của gVisor v1.19.30.

## Lifecycle

Device/stack không tạo khi chỉ parse YAML. Traffic đầu tiên của từng outbound mới tạo stack/device dưới mutex riêng. Creation failure có backoff riêng 1s -> 30s. Một outbound lỗi không đổi profile hoặc đóng device của outbound khác.

## AmneziaWG

Đường lazy vẫn giữ nhánh upstream:

- `Version == 3` -> `amneziav3.NewDevice`
- version khác -> legacy `amnezia.NewDevice`
- WireGuard thường -> `device.NewDevice`

## Build

Workflow tạo vendor mới từ `go.mod/go.sum`, xác minh SHA source dependency, copy vendor overlay khóa cứng, gofmt, test gVisor/sing-wireguard/adapter, cross-compile Windows và package Wintun.
