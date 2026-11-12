
@echo off
title Smart Irrigation Dashboard

cd /d "%~dp0.."

echo ========================================
echo       SMART IRRIGATION DASHBOARD
echo ========================================
echo.

echo Starting Dashboard Backend...
echo URL: http://localhost:8082/
echo.

start "" "http://localhost:8082/"

python server\server.py --host 127.0.0.1 --port 8082

echo.
echo Dashboard Backend has stopped.
pause
