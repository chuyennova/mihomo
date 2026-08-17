# Mihomo v1.19.30 Hybrid 4 Network Profiles v2 — Windows / Clash Verge

Đây là **overlay**, không phải toàn bộ source Mihomo. Nền bắt buộc là upstream sạch `v1.19.30`.

## 4 profile

```yaml
network-profile: windows
network-profile: macos
network-profile: linux
network-profile: android
```

- `windows`: Wintun + Winsock/Windows TCP-IP thật, mỗi outbound một adapter lazy.
- `macos`: gVisor macOS-like.
- `linux`: gVisor Linux-like.
- `android`: gVisor Android-like.

Không khai báo `network-profile` thì giữ nguyên `ip-stack: auto|gvisor|mips` của upstream v1.19.30.

## V2 thay đổi gì so với V1

1. **IPv6 Linux/Android được làm sát kernel hơn**:
   - Hop Limit giữ 64.
   - Automatic Flow Label dùng canonical flow tuple + SipHash-2-4 + rotate-left 16 + mask 20 bit.
   - Không còn ép cứng `0x80000` stateless-range bit. Linux/Android kernel chỉ OR bit này khi `flowlabel_state_ranges` được bật; mặc định không bật.
   - Linux TCP/UDP giữ cùng flow-label helper; Linux ICMPv6/non-port traffic cũng có đường auto-label ở IPv6 network layer.
   - Android TCP/UDP/ICMPv6 dùng cùng kernel-like flow hash; các hành vi Android riêng khác (DF/PMTU/TCP/MTU) vẫn giữ.

2. **macOS không bị sửa IPv4 đang ổn**. IPv6 tiếp tục dùng Hop Limit 64 và flow label 20-bit theo endpoint/socket profile như V1. V2 không tuyên bố thuật toán Flow Label là bit-for-bit XNU khi chưa có bằng chứng nguồn đủ mạnh.

3. **Windows giữ nguyên native**: IPv4/IPv6 do Winsock + Windows kernel xử lý, socket IPv6 được bind đúng địa chỉ WireGuard và ghim interface bằng `IPV6_UNICAST_IF`.

4. **Profile Audit trong build**:
   - sinh `logs/profile-audit.txt` và `logs/profile-audit.json`;
   - kiểm tra selector 4 profile, native Windows IPv6, Hop Limit, Linux/Android flow-label path, không ép stateless bit;
   - chạy regression tests SipHash/flow tuple/Hop Limit;
   - nếu audit fail, workflow đỏ nhưng log vẫn luôn được upload.

5. **Dependency graph được khóa**: V2 dùng đúng `go.mod/go.sum` đã tạo ra binary V1 build thành công và không chạy `go mod tidy` trong CI nữa. Điều này tránh toolchain mới tự rewrite dependency graph giữa các lần build.

## MTU

- `android`: mặc định 1360 nếu YAML không khai báo `mtu`.
- `windows`, `macos`, `linux`, và upstream/no-profile: mặc định 1408.
- YAML có `mtu`: luôn ưu tiên giá trị YAML.

## Build trên GitHub Web

1. Dùng branch `hybrid-v1.19.30`.
2. Chép đè toàn bộ nội dung ZIP overlay này vào root branch.
3. Commit.
4. Vào **Actions** -> **Build Windows Hybrid WireGuard Profiles v1.19.30 v2**.
5. Chờ workflow hoàn tất.

Artifact binary:

- `verge-mihomo.exe`
- `wintun.dll`
- `LICENSE-wintun.txt`
- `SHA256SUMS.txt`
- `verge-mihomo-v1.19.30-hybrid-windows-amd64-v2.zip`

Artifact diagnostics luôn được upload kể cả build lỗi. Ngoài `full-build.log`, log từng bước và summary, V2 có thêm:

```text
logs/profile-audit.txt
logs/profile-audit.json
logs/diagnostics/profile-audit.*
```

## Giới hạn của build audit

Build audit chứng minh code path, thuật toán và regression properties trong binary source. Nó không thể chứng minh 100% packet sau khi đi qua WireGuard server/NAT vẫn giữ nguyên. Wire-level cuối cùng vẫn nên xác nhận bằng packet capture khi có điều kiện.
