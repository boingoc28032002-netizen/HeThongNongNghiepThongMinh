#!/usr/bin/env python3
"""May chu dashboard: phuc vu giao dien (dashboard/) va API tai khoan.

Chay:  python server/server.py            (mac dinh http://localhost:8080/)
       python server/server.py --port 9000 --host 127.0.0.1 --no-register

Chi dung thu vien chuan cua Python 3, khong can cai them gi.
Tai khoan luu trong data/accounts.db tren may chu, dung chung cho moi trinh duyet / thiet bi.
"""
import argparse
import json
import os
import sys
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accounts  # noqa: E402

DASH_DIR = Path(__file__).resolve().parent.parent / "dashboard"
COOKIE = "irrigation_sid"
MAX_BODY = 4096
CFG = {"allow_register": True, "secure_cookie": False}


class Handler(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
                      ".svg": "image/svg+xml", ".json": "application/json", ".jpg": "image/jpeg",
                      ".png": "image/png", ".html": "text/html; charset=utf-8", "": "application/octet-stream"}
    server_version = "SmartIrrigation/1.0"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DASH_DIR), **kw)

    # ---------- tien ich ----------
    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", getattr(self, "_cc", "no-cache"))
        super().end_headers()

    def _token(self):
        c = SimpleCookie()
        try:
            c.load(self.headers.get("Cookie", ""))
        except Exception:
            return None
        m = c.get(COOKIE)
        return m.value if m else None

    def _user(self):
        return accounts.session_user(self._token())

    def _ip(self):
        return self.client_address[0]

    def _cookie_header(self, token, max_age=None):
        parts = [f"{COOKIE}={token}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if max_age is not None:
            parts.append(f"Max-Age={max_age}")
        if CFG["secure_cookie"] or self.headers.get("X-Forwarded-Proto") == "https":
            parts.append("Secure")
        return "; ".join(parts)

    def _json(self, status, obj, cookie=None):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cc = "no-store"
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, where):
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", where)
        self._cc = "no-store"
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _read_json(self):
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return None, "Yêu cầu không hợp lệ"
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return None, "Yêu cầu không hợp lệ"
        if n <= 0 or n > MAX_BODY:
            return None, "Yêu cầu không hợp lệ"
        try:
            data = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None, "Yêu cầu không hợp lệ"
        return (data, None) if isinstance(data, dict) else (None, "Yêu cầu không hợp lệ")

    def _same_origin(self):
        origin = self.headers.get("Origin")
        if not origin:
            return True
        return urlparse(origin).netloc == self.headers.get("Host")

    # ---------- GET ----------
    def _is_protected(self):
        """True neu URL tro toi dashboard/index.html (ke ca '/', '//index.html', INDEX.HTML tren Windows...)."""
        fs = self.translate_path(self.path)
        if os.path.isdir(fs):
            fs = os.path.join(fs, "index.html")
        try:
            return os.path.samefile(fs, DASH_DIR / "index.html")
        except OSError:
            return False

    def do_GET(self):
        path = urlparse(self.path).path
        if path.startswith("/api/"):
            return self.api_get(path)
        if self._is_protected():
            if not self._user():
                return self._redirect("/login.html")
            self._cc = "no-store"
        return super().do_GET()

    def do_HEAD(self):
        if self._is_protected():
            if not self._user():
                return self._redirect("/login.html")
            self._cc = "no-store"
        return super().do_HEAD()

    def list_directory(self, path):                  # khong liet ke thu muc
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def api_get(self, path):
        if path == "/api/status":
            u = self._user()
            return self._json(200, {
                "ok": True, "user": u and {"name": u["name"], "role": u["role"]},
                "hasUsers": accounts.user_count() > 0, "allowRegister": CFG["allow_register"]})
        if path == "/api/me":
            u = self._user()
            if not u:
                return self._json(401, {"ok": False, "error": "Chưa đăng nhập"})
            return self._json(200, {"ok": True, "user": {"name": u["name"], "role": u["role"]}})
        self._json(404, {"ok": False, "error": "Không tìm thấy"})

    # ---------- POST ----------
    def do_POST(self):
        path = urlparse(self.path).path
        if not path.startswith("/api/"):
            return self.send_error(HTTPStatus.NOT_FOUND)
        if not self._same_origin():
            return self._json(403, {"ok": False, "error": "Yêu cầu bị từ chối"})
        if path == "/api/logout":
            accounts.end_session(self._token())
            return self._json(200, {"ok": True}, cookie=self._cookie_header("", 0))
        data, err = self._read_json()
        if err:
            return self._json(400, {"ok": False, "error": err})
        if path == "/api/login":
            return self.api_login(data)
        if path == "/api/register":
            return self.api_register(data)
        self._json(404, {"ok": False, "error": "Không tìm thấy"})

    def _locked(self, secs):
        return self._json(429, {"ok": False, "retryAfter": secs,
                                "error": f"Thử quá nhiều lần. Vui lòng thử lại sau {secs} giây"})

    def api_login(self, d):
        username, password, remember = d.get("username"), d.get("password"), bool(d.get("remember"))
        if not isinstance(username, str) or not isinstance(password, str) or not username or not password \
                or len(username) > 64 or len(password) > accounts.MAX_PASS:
            return self._json(400, {"ok": False, "error": "Vui lòng nhập tên đăng nhập và mật khẩu"})
        k_user, k_ip = f"login|{self._ip()}|{username.lower()}", f"login|{self._ip()}|*"
        left = max(accounts.rate_locked(k_user), accounts.rate_locked(k_ip))
        if left:
            return self._locked(left)
        u = accounts.authenticate(username, password)
        if not u:
            left = max(accounts.rate_hit(k_user, accounts.LOGIN_USER_LIMIT),
                       accounts.rate_hit(k_ip, accounts.LOGIN_IP_LIMIT))
            if left:
                return self._locked(left)
            return self._json(401, {"ok": False, "error": "Sai tên đăng nhập hoặc mật khẩu"})
        accounts.rate_clear(k_user)
        token, ttl = accounts.create_session(u["id"], remember)
        self._json(200, {"ok": True, "user": {"name": u["name"], "role": u["role"]}},
                   cookie=self._cookie_header(token, ttl if remember else None))

    def api_register(self, d):
        if not CFG["allow_register"]:
            return self._json(403, {"ok": False, "error": "Máy chủ đang tắt chức năng đăng ký. Hãy liên hệ quản trị viên"})
        username, password = d.get("username"), d.get("password")
        err = accounts.validate_credentials(username, password)
        if err:
            return self._json(400, {"ok": False, "error": err})
        k = f"register|{self._ip()}"
        left = accounts.rate_locked(k)
        if left:
            return self._locked(left)
        u, err = accounts.create_user(username, password)
        if err:
            return self._json(409, {"ok": False, "error": err})
        accounts.rate_hit(k, accounts.REGISTER_IP_LIMIT)
        token, _ = accounts.create_session(u["id"], False)
        self._json(201, {"ok": True, "user": {"name": u["name"], "role": u["role"]}},
                   cookie=self._cookie_header(token))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default="0.0.0.0", help="địa chỉ lắng nghe (mặc định 0.0.0.0: cho cả máy khác trong mạng LAN)")
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--no-register", action="store_true", help="tắt đăng ký công khai (chỉ quản trị viên tạo tài khoản bằng manage.py)")
    ap.add_argument("--secure-cookie", action="store_true", help="đặt cờ Secure cho cookie (khi chạy sau HTTPS)")
    ap.add_argument("--db", help="đường dẫn file SQLite (mặc định data/accounts.db)")
    a = ap.parse_args()
    if a.db:
        accounts.DB_PATH = Path(a.db)
    CFG["allow_register"] = not a.no_register
    CFG["secure_cookie"] = a.secure_cookie
    accounts.init_db()
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    shown = "localhost" if a.host in ("0.0.0.0", "") else a.host
    print(f"Dashboard: http://{shown}:{a.port}/   (Ctrl+C để dừng)")
    print(f"Tài khoản lưu tại: {accounts.DB_PATH}")
    if not CFG["allow_register"]:
        print("Đăng ký công khai: TẮT")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nĐã dừng.")


if __name__ == "__main__":
    main()
