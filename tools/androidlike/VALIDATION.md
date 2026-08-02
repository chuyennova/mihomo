# Validation gates

Workflow chỉ tạo artifact khi qua tất cả bước:

1. Xác nhận đúng module Mihomo và đúng commit dependency.
2. `go mod vendor` từ dependency đã khóa.
3. Kiểm tra SHA-256 của từng file nguồn sẽ vá.
4. Áp patch, `gofmt`, verify và kiểm tra idempotent.
5. Xác nhận các file TCP/UDP/IPv4 ngoài phạm vi không đổi hash.
6. Chạy unit test gVisor IPv6 và sing-wireguard.
7. Compile package outbound của Mihomo.
8. Build đầy đủ Windows amd64 `GOAMD64=v2`.
9. Kiểm tra SHA-256 Wintun chính thức trước khi đóng gói.

## Workflow hygiene v1.1.1

- Kiểm tra SHA vẫn fail-closed nhưng chạy ở chế độ im lặng khi thành công, tránh annotation đỏ giả.
- Checkout và upload artifact dùng action Node.js 24.
- Artifact chỉ được tải lên sau khi unit test, compile gate và build Windows hoàn tất.
