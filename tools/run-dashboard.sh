#!/usr/bin/env sh
# Chay may chu dashboard + tai khoan (can Python 3)
cd "$(dirname "$0")/.." || exit 1
exec python3 server/server.py --port 8080
