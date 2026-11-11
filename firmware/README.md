# Firmware

`main.py` chạy trong Proteus VSM cho Raspberry Pi (các module `goto`, `pio`, `cpu`, `VFP`, `FileStore` do Proteus cung cấp),
vì vậy file này không chạy trực tiếp bằng `python main.py` trên máy thường.

Trước khi chạy, kiểm tra:

- `DB_DIR`: thư mục lưu `irrigation.db`. Đổi thành đường dẫn phù hợp với máy của bạn.
- `MQTT_HOST` / `MQTT_PORT`: địa chỉ broker (mặc định `127.0.0.1:1883`).
- `ENABLE_OUTPUTS`: `False` = chạy khô (chỉ ghi log, không đóng relay).
