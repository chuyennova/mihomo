# Mihomo v1.19.29 — Windows macOS-like WireGuard v3.2.1 IPv6

Bộ overlay này dùng cho nhánh `macoslike-v1.19.29` được tạo trực tiếp từ tag gốc `v1.19.29`. Nó giữ nguyên kiến trúc nhiều SOCKS → nhiều WireGuard của Mihomo và chỉ thay profile userspace network stack của WireGuard.

## Cách cập nhật trên GitHub

Chép đè toàn bộ nội dung ZIP vào thư mục gốc repository, đặc biệt:

```text
.github/workflows/build-windows-macoslike.yml
tools/macoslike/
README_VI.md
```

Commit vào nhánh `macoslike-v1.19.29`, rồi chạy workflow:

```text
Build Windows macOS-like Mihomo v3.2.1 IPv6
```

Artifact tạo ra:

```text
verge-mihomo-windows-macoslike-v3.2.1-ipv6-amd64.zip
├── verge-mihomo.exe
├── wintun.dll
├── BUILD_INFO.txt
├── SHA256SUMS.txt
├── LICENSE-mihomo.txt
└── LICENSE-wintun.txt
```

Hai tên `verge-mihomo.exe` và `wintun.dll` được giữ đúng để Clash Verge sử dụng.

## Phạm vi

Chỉ `adapter/outbound/wireguard.go` chọn constructor macOS-like. OpenVPN, MASQUE, listener, tunnel, rule và cơ chế `listeners[].proxy` không bị đổi.

```text
SOCKS 10881 → WG-01 → stack macOS-like 01
SOCKS 10882 → WG-02 → stack macOS-like 02
SOCKS 10883 → WG-03 → stack macOS-like 03
```

Mỗi WireGuard vẫn có TCP, UDP, source-port allocator và trạng thái lỗi riêng.

## Sửa lỗi build của v3.2

Không dùng ZIP v3.2 cũ. `Stack.SecureRNG()` trả về `rand.RNG` theo giá trị, trong khi `RNG.Uint32()` là pointer receiver. Vì giá trị trả về trực tiếp không addressable, biểu thức `p.stack.SecureRNG().Uint32()` không biên dịch. V3.2.1 giữ RNG của từng stack nhưng đặt nó vào biến cục bộ trước khi gọi:

```go
rng := p.stack.SecureRNG()
return rng.Uint32() & 0x000fffff
```

Workflow có kiểm tra cấm lại biểu thức lỗi cũ ở cả TCP và UDP.

## Khác biệt so với v2

V2 đã làm đúng TCP SYN IPv4 và phần TCP dùng chung cho IPv6. V3.2 giữ lớp IPv6 của v3, sửa lỗi tương thích UDP forwarder và làm bộ sinh Flow Label gần hành vi XNU hơn:

- Đưa `IPv6FlowLabel` từ transport xuống đúng IPv6 base header.
- TCP/IPv6 nhận một Flow Label ngẫu nhiên 20-bit và giữ ổn định suốt một kết nối. Giá trị 0 rất hiếm nhưng được giữ lại vì XNU cũng chỉ lấy số ngẫu nhiên rồi mask 20 bit.
- UDP/IPv6, bao gồm luồng nền cho QUIC khi đi qua UDP, nhận một Flow Label ổn định theo socket; sau disconnect sẽ cấp nhãn mới.
- Hop Limit vẫn là `64`.
- Traffic Class giữ theo socket; mặc định bình thường là `0` khi không bật ECN/DSCP.
- Không tự thêm extension header vào gói TCP SYN/UDP thông thường.
- MSS vẫn tính theo MTU thật: MTU `1360` cho IPv4 MSS `1320`, IPv6 MSS `1300`.

## Dấu vết TCP giữ từ v2

```text
Window:            65535
Window Scale:      4
TCP options:       MSS,NOP,WS,NOP,NOP,TS,SACK,EOL+padding
IPv4 TTL:          64
IPv4 DF:           bật trên SYN
Atomic IPv4 ID:    0
Source-port stack: 49152–65535
```

Đọc `tools/macoslike/EXPECTED_FINGERPRINT.md` và `TEST_AFTER_BUILD.md` trước khi kiểm thử.
