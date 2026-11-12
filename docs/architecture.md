# Kiến trúc hệ thống

## Các thành phần

| Thành phần | Vị trí | Vai trò |
|---|---|---|
| Firmware | `firmware/main.py` | Đọc cảm biến qua MCP3008, quyết định tưới, điều khiển relay, LCD/LED/còi, ghi SQLite, publish MQTT |
| Mô phỏng | `simulation/*.pdsprj` | Mạch Raspberry Pi 5, cảm biến (chiết áp mô phỏng độ ẩm, mực nước), relay bơm và 3 van |
| Broker | Mosquitto | Chuyển bản tin giữa firmware và dashboard |
| Dashboard | `dashboard/` | Hiển thị số liệu, thống kê, gửi lệnh điều khiển |
| Máy chủ web | `server/` | Phục vụ dashboard, API tài khoản (đăng ký / đăng nhập / phiên), lưu SQLite `data/accounts.db` |

## Firmware (main.py)

Chạy trong Proteus VSM nên giữ một file duy nhất. Các khối chính:

- `IrrigationController`: máy trạng thái IDLE → OPENING → RUNNING → CLOSING cho từng vùng, xử lý ngưỡng,
  nhiệt độ, ban đêm, nắng gắt, chế độ thủ công, dừng khẩn cấp
- Đọc ADC và quy đổi: `raw_to_pct`, `raw_to_temp`, bộ lọc `TempFilter`
- GPIO: bơm (K1) và 3 van (K2–K4) qua relay
- SQLite: bảng `runs`, `readings`, `events`
- `MqttLite`: client MQTT 3.1.1 tối giản, không chặn vòng lặp, tự nối lại
- Giao diện trên mạch: `Lcd16x2`, LED, `Buzzer`

## Dashboard

Không dùng framework. Mỗi module có một trách nhiệm:

```
broker ──▶ mqtt/client.js ──▶ state/handlers.js ──▶ state/store.js (S, UI)
                                                         │
                                                         ▼
                                                   ui/render.js ──▶ header, zones, kpis,
                                                                    charts/*, events, controls
```

- `mqtt/`: mã hóa/giải mã gói tin MQTT, kết nối WebSocket, tự nối lại sau 3 s
- `state/`: `S` là thống kê của lần chạy hiện tại (lưu localStorage), `UI` là lựa chọn của người dùng;
  `parser.js` chuyển chuỗi sự kiện thành đối tượng; `handlers.js` cập nhật thống kê
- `ui/`: các hàm `render*` đọc `S`/`UI` rồi vẽ lại; `controls.js` gửi lệnh qua `publish()`

Thống kê (số lần tưới, thời gian bơm, độ ẩm trung bình...) được tính ngay trong trình duyệt từ các bản tin nhận được.
Bản tin gửi lúc dashboard mất kết nối không được gửi bù.

## Máy chủ web và tài khoản (`server/`)

```
trình duyệt ── GET /index.html ──▶ server.py ── có cookie phiên hợp lệ? ── không ──▶ 302 login.html
            ── POST /api/login | /api/register | /api/logout, GET /api/me | /api/status ──▶ accounts.py ──▶ data/accounts.db
```

- Bảng `users` (tên, băm mật khẩu, vai trò), `sessions` (băm token, hạn dùng), `rate` (đếm lần thử sai / đăng ký).
- Chỉ thư mục `dashboard/` được phục vụ nên `data/` và mã máy chủ không tải về được.
- POST yêu cầu `Content-Type: application/json` và kiểm tra `Origin` trùng `Host` (chống CSRF, kết hợp cookie `SameSite=Lax`).
- Dashboard (MQTT qua WebSocket) vẫn nối thẳng tới Mosquitto, không đi qua máy chủ này.
