@echo off
rem Mo dashboard bang server tinh (can Python). Dashboard dung ES modules nen khong mo bang double-click duoc.
cd /d "%~dp0..\dashboard"
start "" "http://localhost:8080/"
python -m http.server 8080
