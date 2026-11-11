#!/usr/bin/env sh
# Mo dashboard bang server tinh (can Python 3)
cd "$(dirname "$0")/../dashboard" || exit 1
echo "Dashboard: http://localhost:8080/"
python3 -m http.server 8080
