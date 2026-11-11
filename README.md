# Hệ thống tưới nước thông minh (Raspberry Pi 5 + MQTT + Dashboard)

Đồ án: điều khiển tưới tự động 3 vùng dựa trên độ ẩm đất, mực nước bể, ánh sáng và nhiệt độ.
Phần cứng được mô phỏng trong Proteus (Raspberry Pi 5), dữ liệu được đẩy qua MQTT lên dashboard web
để giám sát và điều khiển từ xa.

## Chức năng

- Tưới tự động 3 vùng theo ngưỡng độ ẩm (mặc định bắt đầu < 40, dừng ≥ 60), ngưỡng tự điều chỉnh theo nhiệt độ
- Chặn tưới khi nước trong bể thấp, giới hạn thời gian tưới tối đa, báo lỗi cảm biến
- Chế độ ban đêm, hoãn tưới khi nắng gắt
- Màn hình LCD 16x2, LED trạng thái và còi báo động trên mạch
- Ghi dữ liệu vào SQLite, gửi dữ liệu và sự kiện qua MQTT
- Dashboard: KPI, biểu đồ, thống kê theo vùng, nhật ký sự kiện
- Trang đăng nhập / đăng ký (`dashboard/login.html`), dashboard chỉ mở được sau khi đăng nhập
- Điều khiển từ dashboard: tự động / thủ công, mở đóng van từng vùng, đổi ngưỡng, dừng khẩn cấp
- Failsafe: ở chế độ thủ công mà mất MQTT quá 60 s thì thiết bị tự về chế độ tự động

## Sơ đồ hệ thống

```
 Proteus (RPi5 + cảm biến + relay)         Mosquitto broker             Trình duyệt
 firmware/main.py  ── MQTT :1883 ──────▶  irrigation/#  ◀── WebSocket :9001 ── dashboard/
                   ◀── irrigation/cmd ────────────────────────── lệnh điều khiển ──
```

Chi tiết: [docs/architecture.md](docs/architecture.md) · Topic và định dạng JSON: [docs/mqtt-topics.md](docs/mqtt-topics.md)

## Cấu trúc thư mục

```
firmware/            Code chạy trên Raspberry Pi (trong Proteus)
simulation/          Project Proteus (.pdsprj)
dashboard/           Giao diện web (HTML + CSS + JavaScript ES modules)
  index.html         dashboard (yêu cầu đăng nhập)
  login.html         trang đăng nhập / đăng ký
  css/               base, layout, components, charts, responsive
  js/
    main.js          điểm vào
    auth.js          tài khoản, băm mật khẩu, phiên đăng nhập
    login.js         logic trang đăng nhập
    config.js        địa chỉ broker, tên topic, khóa localStorage
    constants.js     màu, tên trạng thái, lý do kết thúc tưới
    mqtt/            codec gói tin MQTT + client WebSocket
    state/           trạng thái, thống kê, xử lý bản tin
    ui/              các thành phần giao diện (thẻ vùng, KPI, biểu đồ, nhật ký, điều khiển)
    utils/           hàm tiện ích
  assets/icons.svg
tools/               cấu hình Mosquitto và script chạy nhanh
docs/                tài liệu
```

## Yêu cầu

- Proteus 8.x có mô hình Raspberry Pi (mở `simulation/Smart_Irrigation_RPi5.pdsprj`)
- [Mosquitto](https://mosquitto.org/download/) (broker MQTT)
- Python 3 (chỉ để phục vụ file tĩnh cho dashboard)
- Trình duyệt hiện đại (Chrome, Edge, Firefox)

## Cách chạy

1. **Chạy broker.** Windows: chạy `tools\run-broker.bat`. Hoặc tự chạy:
   ```
   mosquitto -c tools/mosquitto.conf -v
   ```
   Broker nghe cổng 1883 (MQTT, cho firmware) và 9001 (WebSocket, cho dashboard).
2. **Chạy dashboard.** Windows: chạy `tools\run-dashboard.bat`. Linux/macOS: `sh tools/run-dashboard.sh`.
   Hoặc:
   ```
   cd dashboard
   python -m http.server 8080
   ```
   rồi mở http://localhost:8080/ . Dashboard dùng ES modules nên **không** mở bằng double-click vào `index.html` được.
3. **Chạy mô phỏng.** Mở project Proteus, đảm bảo linh kiện Raspberry Pi trỏ tới `firmware/main.py`, bấm Run.
   Khi firmware kết nối được broker, thanh trên cùng của dashboard hiện "Đã nối broker" và "Thiết bị: online".

Nếu broker ở máy khác: mở dashboard với `?ws=ws://<địa-chỉ>:9001`, và sửa `MQTT_HOST` trong `firmware/main.py`.

## Đăng nhập

Mở http://localhost:8080/ sẽ được chuyển tới `login.html`. Lần đầu bấm tab **Đăng ký** để tạo tài khoản.
Tài khoản lưu trong `localStorage` của trình duyệt (mật khẩu băm PBKDF2-SHA256 kèm salt), tick **Nhớ tài khoản** để giữ phiên sau khi đóng trình duyệt.
Sai 5 lần thì khóa 30 giây. Dashboard là web tĩnh, không có máy chủ, nên đây chỉ là cổng đăng nhập ở phía giao diện:
nó không ngăn được người đã truy cập được broker MQTT. Cần bảo mật thật thì thêm xác thực cho Mosquitto (`password_file`).
Đăng nhập dùng Web Crypto nên phải mở qua `localhost` hoặc HTTPS.

## Cấu hình firmware

Các hằng số cấu hình nằm đầu từng phần trong `firmware/main.py`: `CONFIG` (ngưỡng tưới),
`MQTT_*` (broker), `DB_DIR` (thư mục lưu SQLite), `ENABLE_OUTPUTS` (False = chạy khô, chỉ ghi log).
Chân GPIO và kênh ADC (MCP3008) được khai báo ngay phần đầu của file.

## Tiến độ

Xem lịch sử commit và các tag trong repository.
