@echo off
rem Chay Mosquitto voi cau hinh cua du an (1883 + WebSockets 9001)
set MOSQ="C:\Program Files\mosquitto\mosquitto.exe"
if not exist %MOSQ% (
  echo Khong tim thay Mosquitto tai %MOSQ%. Hay cai Mosquitto hoac sua duong dan trong file nay.
  pause
  exit /b 1
)
%MOSQ% -c "%~dp0mosquitto.conf" -v
