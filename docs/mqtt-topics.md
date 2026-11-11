# Topic MQTT

Tiền tố `irrigation` (`MQTT_BASE` trong firmware, `TOPICS` trong `dashboard/js/config.js`). QoS 0.

| Topic | Hướng | Retain | Nội dung |
|---|---|---|---|
| `irrigation/status` | thiết bị → dashboard | có | `online` khi kết nối; `offline` do broker phát (Last Will) khi mất kết nối |
| `irrigation/readings` | thiết bị → dashboard | có | JSON số liệu, gửi mỗi `MQTT_PUB_EVERY` tick (mặc định 20 tick = 5 s mô phỏng) |
| `irrigation/events` | thiết bị → dashboard | không | JSON sự kiện dạng văn bản |
| `irrigation/cmd` | dashboard → thiết bị | không | JSON lệnh điều khiển |

## `irrigation/readings`

```json
{"run":3,"t":125.0,"state":"RUNNING","zone":0,
 "soil":[35.2,58.0,61.4],"soil4":50.0,"water":72.0,"light":55.0,
 "temp":28.5,"band":"normal","night":0,"harsh":0,"defer":[0,0,0],"thr":[40.0,60.0],
 "pump":1,"valves":[1,0,0],"mode":"auto"}
```

| Trường | Ý nghĩa |
|---|---|
| `run` | số thứ tự lần chạy (khóa chính bảng `runs` trong SQLite) |
| `t` | giây mô phỏng của Proteus, không phải giờ thật |
| `state`, `zone` | trạng thái máy trạng thái (IDLE/OPENING/RUNNING/CLOSING) và vùng đang tưới (`null` nếu không có) |
| `soil` | độ ẩm 3 vùng, thang 0–100; `null` nếu cảm biến lỗi |
| `soil4` | kênh RV4, không tham gia điều khiển |
| `water`, `light`, `temp` | mực nước (0–100), ánh sáng (0–100), nhiệt độ (°C, `null` nếu chưa nối LM35) |
| `band` | dải nhiệt: `normal`, `hot`, `cool` |
| `night`, `harsh` | 1 nếu đang ban đêm / nắng gắt |
| `defer` | vùng nào đang bị hoãn tưới vì nắng gắt |
| `thr` | ngưỡng [bắt đầu, dừng] đang áp dụng (đã hiệu chỉnh theo nhiệt độ) |
| `pump`, `valves` | trạng thái relay bơm và 3 van |
| `mode` | `auto` hoặc `manual` |

## `irrigation/events`

```json
{"run":3,"t":125.00,"text":"STATE OPENING -> RUNNING zone=0 t=125.0"}
```

`text` là chuỗi do firmware sinh ra, dashboard phân tích trong `dashboard/js/state/parser.js`
(`STATE`, `WATER`, `TEMP`, `NIGHT`, `HARSH`, `DEFER`, `MODE`, `MANUAL`, `STOP`, `THR`, `CMD rejected`).
Nếu thêm loại sự kiện mới ở firmware, cần thêm mẫu tương ứng trong `parser.js`.

## `irrigation/cmd`

| Lệnh | JSON |
|---|---|
| Đổi chế độ | `{"cmd":"mode","value":"auto"}` hoặc `{"cmd":"mode","value":"manual"}` |
| Mở/đóng van (chỉ ở chế độ thủ công) | `{"cmd":"zone","z":0,"on":1}` (z = 0, 1, 2) |
| Đổi ngưỡng | `{"cmd":"thr","start":40,"stop":60}` |
| Dừng khẩn cấp | `{"cmd":"stop"}` |

Thiết bị phản hồi bằng một bản tin trên `irrigation/events`; lệnh sai bị từ chối với `CMD rejected: ...`.
