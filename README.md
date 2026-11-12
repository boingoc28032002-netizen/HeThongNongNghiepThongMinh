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
- Đăng nhập / đăng ký tài khoản (`dashboard/login.html`); tài khoản lưu trên máy chủ, dashboard chỉ mở được sau khi đăng nhập
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
server/              Máy chủ Python (chỉ dùng thư viện chuẩn): phục vụ dashboard + API tài khoản
  server.py          chạy dashboard, /api/register, /api/login, /api/logout, /api/me
  accounts.py        SQLite: tài khoản, băm mật khẩu, phiên đăng nhập, giới hạn thử sai
  manage.py          quản trị tài khoản: list / add / passwd / delete
data/                accounts.db (tự tạo khi chạy máy chủ, không đưa lên git)
dashboard/           Giao diện web (HTML + CSS + JavaScript ES modules)
  index.html         dashboard (yêu cầu đăng nhập)
  login.html         trang đăng nhập / đăng ký
  css/               base, layout, components, charts, login, responsive
  js/
    main.js          điểm vào
    auth.js          gọi API tài khoản của máy chủ
    login.js         logic trang đăng nhập
    config.js        địa chỉ broker, tên topic, khóa localStorage
    constants.js     màu, tên trạng thái, lý do kết thúc tưới
    mqtt/            codec gói tin MQTT + client WebSocket
    state/           trạng thái, thống kê, xử lý bản tin
    ui/              các thành phần giao diện (thẻ vùng, KPI, biểu đồ, nhật ký, điều khiển)
    utils/           hàm tiện ích
  assets/            icons.svg, login-scene.jpg (nền), logo.png
tools/               cấu hình Mosquitto và script chạy nhanh
docs/                tài liệu
```

## Yêu cầu

- Proteus 8.x có mô hình Raspberry Pi (mở `simulation/Smart_Irrigation_RPi5.pdsprj`)
- [Mosquitto](https://mosquitto.org/download/) (broker MQTT)
- Python 3 (chạy máy chủ dashboard và quản lý tài khoản, không cần cài thêm thư viện)
- Trình duyệt hiện đại (Chrome, Edge, Firefox)

## Cách chạy

1. **Chạy broker.** Windows: chạy `tools\run-broker.bat`. Hoặc tự chạy:
   ```
   mosquitto -c tools/mosquitto.conf -v
   ```
   Broker nghe cổng 1883 (MQTT, cho firmware) và 9001 (WebSocket, cho dashboard).
2. **Chạy máy chủ dashboard.** Windows: chạy `tools\run-dashboard.bat`. Linux/macOS: `sh tools/run-dashboard.sh`.
   Hoặc:
   ```
   python server/server.py --port 8080
   ```
   rồi mở http://localhost:8080/ . Phải chạy bằng `server/server.py` (không dùng `python -m http.server`) vì đăng nhập cần API của máy chủ.
   Dashboard dùng ES modules nên cũng **không** mở bằng double-click vào `index.html` được.
3. **Chạy mô phỏng.** Mở project Proteus, đảm bảo linh kiện Raspberry Pi trỏ tới `firmware/main.py`, bấm Run.
   Khi firmware kết nối được broker, thanh trên cùng của dashboard hiện "Đã nối broker" và "Thiết bị: online".

Nếu broker ở máy khác: mở dashboard với `?ws=ws://<địa-chỉ>:9001`, và sửa `MQTT_HOST` trong `firmware/main.py`.

## Đăng nhập

Mở http://localhost:8080/ sẽ được chuyển tới `login.html`.

- **Tài khoản lưu trên máy chủ** (`data/accounts.db`), không lưu trong trình duyệt. Tạo một lần là đăng nhập được trên mọi trình duyệt / thiết bị truy cập cùng máy chủ.
- Lần đầu chưa có tài khoản nào: trang tự mở chế độ **Tạo tài khoản**, tài khoản đầu tiên là quản trị viên (`admin`). Sau đó bấm **Đăng ký tài khoản** để tạo thêm.
- Mật khẩu từ 8 ký tự, băm PBKDF2-SHA256 (600.000 vòng, salt riêng). Phiên đăng nhập là cookie `HttpOnly` + `SameSite=Lax`; trong CSDL chỉ lưu băm của token.
- **Nhớ tài khoản**: giữ đăng nhập 30 ngày và điền sẵn tên đăng nhập lần sau (không tick thì phiên hết hạn sau 12 giờ hoặc khi đóng trình duyệt).
- Sai 5 lần liên tiếp thì khóa 30 giây (tính theo địa chỉ IP + tài khoản). Mỗi IP đăng ký tối đa 10 tài khoản / giờ.
- `index.html` được máy chủ chặn: chưa đăng nhập thì chuyển sang `login.html`, không tải được dashboard.
- **Quên mật khẩu**: chưa có email khôi phục. Quản trị viên đặt lại bằng lệnh `python server/manage.py passwd <tên>`
  (xem thêm `list`, `add`, `delete`). Đặt lại mật khẩu sẽ đăng xuất tài khoản đó khỏi mọi thiết bị.
- Tùy chọn máy chủ: `--host 127.0.0.1` (chỉ máy này), `--no-register` (tắt đăng ký công khai, quản trị viên tạo bằng `manage.py add`),
  `--secure-cookie` (khi chạy sau HTTPS), `--db <file>`.

Lưu ý: cổng đăng nhập chỉ bảo vệ giao diện web. Người truy cập được broker MQTT vẫn gửi lệnh được;
cần bảo mật thật thì thêm xác thực cho Mosquitto (`password_file`). Mạng LAN dùng HTTP thường nên cookie không được mã hóa;
muốn ra Internet hãy đặt sau HTTPS (reverse proxy) và bật `--secure-cookie`.

## Cấu hình firmware

Các hằng số cấu hình nằm đầu từng phần trong `firmware/main.py`: `CONFIG` (ngưỡng tưới),
`MQTT_*` (broker), `DB_DIR` (thư mục lưu SQLite), `ENABLE_OUTPUTS` (False = chạy khô, chỉ ghi log).
Chân GPIO và kênh ADC (MCP3008) được khai báo ngay phần đầu của file.

## Tiến độ

Xem lịch sử commit và các tag trong repository.
