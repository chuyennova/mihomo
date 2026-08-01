# Kiểm tra đã thực hiện

- Giải nén lại trực tiếp `mihomo-1.19.29(8).zip` và xác nhận `adapter/outbound/wireguard.go` trùng SHA-256 với file dùng để tạo patch.
- Chạy `apply_macoslike.py` trên source sạch cùng đúng các file dependency bị khóa.
- Chạy `gofmt` trên toàn bộ sáu file Go được sửa.
- Chạy `apply_macoslike.py --verify-only` thành công.
- Áp thử toàn bộ năm file `.patch` bằng `patch -p1`, sau đó verify thành công.
- Parse workflow YAML thành công.

Chưa compile full EXE trong container vì toàn bộ dependency Go không tải xong trong thời hạn môi trường. Workflow GitHub sẽ compile thật và dừng ngay nếu API/anchor không khớp.
