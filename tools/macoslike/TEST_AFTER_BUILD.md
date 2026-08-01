# Kiểm thử bắt buộc sau build

## 1. Kiểm tra Clash Verge

- Chép `verge-mihomo.exe` và `wintun.dll` cạnh core Clash Verge.
- Chạy kiểm tra cấu hình của Clash Verge.
- Xác nhận nhiều listener SOCKS cùng mở.

## 2. Kiểm tra cô lập nhiều WireGuard

- Mở đồng thời ít nhất 3 SOCKS.
- Mỗi SOCKS truy cập một máy chủ ghi nhận IP riêng.
- Tắt WG-02; WG-01 và WG-03 vẫn phải hoạt động.
- Kiểm tra DNS, TCP và UDP không chuyển nhầm outbound.

## 3. Thu packet ở phía ngoài

Packet phải được bắt tại máy chủ Internet **sau khi qua S9**, không chỉ bắt trong Windows:

- IPv4 SYN và IPv6 SYN.
- SYN retransmission khi cố ý drop packet đầu.
- ACK khi tải file.
- FIN/RST khi đóng kết nối.
- Phân bố source port qua ít nhất 200 kết nối.

Kỳ vọng baseline:

```text
TTL/Hop Limit ban đầu: 64 trước số hop
TCP options: MSS,NOP,WS,SACK,TS
Ephemeral source port: 49152–65535
Không xuất hiện keepalive đều 15 giây trên mọi kết nối
```

## 4. Không đánh giá chỉ bằng một trang fingerprint

So sánh PCAP với một máy Mac thật có cùng:

- phiên bản macOS mục tiêu;
- IPv4/IPv6;
- MTU/path gần tương đương;
- loại kết nối Wi-Fi/Ethernet.

Sau đó mới chỉnh window, WS, ECN, ACK hoặc recovery. Không suy đoán các giá trị này từ tên hệ điều hành.
