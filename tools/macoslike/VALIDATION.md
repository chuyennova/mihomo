# Kiểm tra đã thực hiện cho v3.2.1

- Giải nén trực tiếp `mihomo-1.19.29(10).zip`.
- Đối chiếu dependency bị khóa trong `go.mod`:
  - `sing-wireguard` commit `7e7c7c1b854c`.
  - `gvisor` commit `261ec1326fe8`.
- So sánh mã gốc với v2 và xác định phần còn thiếu nằm ở đường truyền Flow Label từ TCP/UDP xuống IPv6 base header.
- Chạy `apply_macoslike.py` trên source sạch và đúng các dependency bị khóa.
- Chạy `gofmt` trên 11 file Go được sửa.
- Chạy `apply_macoslike.py --verify-only` thành công.
- Tạo và áp tuần tự đủ 6 file `.patch` bằng `patch -p1` trên source sạch.
- Sau `gofmt`, kết quả từ 6 patch giống byte-for-byte với kết quả của script tự động.
- Kiểm tra constructor macOS-like chỉ xuất hiện trong `wireguard.go`; OpenVPN và MASQUE không bị đổi.
- Kiểm tra cả TCP lẫn UDP macOS-like đều truyền Flow Label vào IPv6 header.
- Kiểm tra toàn bộ call-site của `udp.newEndpoint`: giữ nguyên chữ ký gốc để `udp/forwarder.go` không bị lỗi biên dịch.
- Thêm verify bắt buộc kiểm tra `udp/forwarder.go` và cấm chữ ký `newEndpoint(*protocol, ...)` không an toàn.
- Đối chiếu hành vi auto Flow Label của XNU: profile v3.2.1 dùng giá trị ngẫu nhiên 20-bit và không cưỡng chế loại bỏ giá trị 0.
- Parse cấu trúc workflow và kiểm tra đầy đủ các file vendor cần vá.
- Đối chiếu trực tiếp API gVisor bị khóa: `Stack.SecureRNG()` trả `cryptorand.RNG` theo giá trị, còn `(*RNG).Uint32()` dùng pointer receiver.
- Sửa cả TCP và UDP sang biến cục bộ addressable trước khi gọi `Uint32()`.
- Thêm kiểm tra cấm `SecureRNG().Uint32()` để lỗi này không tái xuất hiện.

Đã kiểm tra patch theo hai đường độc lập: script tự động và áp tuần tự 6 file patch; sau `gofmt` hai kết quả giống byte-for-byte. Môi trường container không tải hoàn tất toàn bộ module cache nên chưa thể tuyên bố đã compile EXE tại đây; workflow GitHub sẽ compile thật và dừng nếu còn lỗi API.
