"""Kho tai khoan tren may chu (SQLite).

- Mat khau luu dang PBKDF2-SHA256 (600.000 vong) kem salt rieng, khong bao gio luu mat khau goc.
- Phien dang nhap: token ngau nhien gui cho trinh duyet qua cookie HttpOnly,
  trong CSDL chi luu SHA-256 cua token nen lo file CSDL cung khong dung lai duoc phien.
- Gioi han dang nhap sai / dang ky qua nhieu nam trong bang `rate`.
"""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.environ.get("IRRIGATION_DB") or ROOT / "data" / "accounts.db")

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
MIN_PASS, MAX_PASS = 8, 128
PBKDF2_ITER = 600_000
SESSION_HOURS = 12            # khong tick "Nho tai khoan"
REMEMBER_DAYS = 30            # co tick "Nho tai khoan"

# Gioi han: (so lan, cua so thoi gian giay, khoa giay)
LOGIN_USER_LIMIT = (5, 600, 30)     # sai 5 lan tren cung (IP, tai khoan) -> khoa 30 s
LOGIN_IP_LIMIT = (30, 600, 120)     # sai 30 lan tu mot IP -> khoa 120 s
REGISTER_IP_LIMIT = (10, 3600, 600) # dang ky 10 tai khoan / gio / IP


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def init_db():
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id          INTEGER PRIMARY KEY AUTOINCREMENT,
          username    TEXT NOT NULL,
          username_lc TEXT NOT NULL UNIQUE,
          pw_hash     TEXT NOT NULL,
          role        TEXT NOT NULL DEFAULT 'user',
          created_at  INTEGER NOT NULL,
          last_login  INTEGER
        );
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY,
          user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          created_at INTEGER NOT NULL,
          expires_at INTEGER NOT NULL,
          remember   INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
        CREATE TABLE IF NOT EXISTS rate(
          key          TEXT PRIMARY KEY,
          count        INTEGER NOT NULL,
          window_start REAL NOT NULL,
          locked_until REAL NOT NULL DEFAULT 0
        );
        """)


# ---------- mat khau ----------
def hash_password(password, salt=None, iters=PBKDF2_ITER):
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iters)
    return f"pbkdf2_sha256${iters}${salt.hex()}${dk.hex()}"


def verify_password(password, stored):
    try:
        algo, iters, salt, want = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iters)).hex()
        return hmac.compare_digest(got, want)
    except (ValueError, TypeError):
        return False


_DUMMY = hash_password("dummy-password-for-timing")   # de tai khoan khong ton tai cung ton thoi gian bam


def validate_credentials(username, password):
    """Tra ve chuoi loi (tieng Viet) hoac None neu hop le."""
    if not isinstance(username, str) or not USERNAME_RE.match(username):
        return "Tên đăng nhập 3-32 ký tự, chỉ gồm chữ, số, dấu . _ -"
    if not isinstance(password, str) or len(password) < MIN_PASS:
        return f"Mật khẩu cần ít nhất {MIN_PASS} ký tự"
    if len(password) > MAX_PASS:
        return f"Mật khẩu tối đa {MAX_PASS} ký tự"
    return None


# ---------- tai khoan ----------
def user_count():
    with connect() as con:
        return con.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def create_user(username, password, role=None):
    """Tra ve (user_dict, None) hoac (None, loi). Tai khoan dau tien la quan tri vien."""
    err = validate_credentials(username, password)
    if err:
        return None, err
    pw_hash = hash_password(password)
    with connect() as con:
        try:
            con.execute("BEGIN IMMEDIATE")
            if role is None:
                role = "admin" if con.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0 else "user"
            cur = con.execute(
                "INSERT INTO users(username, username_lc, pw_hash, role, created_at) VALUES(?,?,?,?,?)",
                (username, username.lower(), pw_hash, role, int(time.time())))
            con.commit()
        except sqlite3.IntegrityError:
            con.rollback()
            return None, "Tên đăng nhập đã tồn tại"
    return {"id": cur.lastrowid, "name": username, "role": role}, None


def authenticate(username, password):
    """Tra ve user_dict neu dung, nguoc lai None."""
    with connect() as con:
        row = con.execute("SELECT * FROM users WHERE username_lc=?", (str(username).lower(),)).fetchone()
        ok = verify_password(password, row["pw_hash"] if row else _DUMMY)
        if not (row and ok):
            return None
        con.execute("UPDATE users SET last_login=? WHERE id=?", (int(time.time()), row["id"]))
        return {"id": row["id"], "name": row["username"], "role": row["role"]}


def set_password(username, password):
    err = validate_credentials(username, password)
    if err and "Mật khẩu" in err:
        return False, err
    with connect() as con:
        cur = con.execute("UPDATE users SET pw_hash=? WHERE username_lc=?", (hash_password(password), username.lower()))
        if cur.rowcount == 0:
            return False, "Không có tài khoản này"
        con.execute("DELETE FROM sessions WHERE user_id=(SELECT id FROM users WHERE username_lc=?)", (username.lower(),))
    return True, None


def delete_user(username):
    with connect() as con:
        return con.execute("DELETE FROM users WHERE username_lc=?", (username.lower(),)).rowcount > 0


def list_users():
    with connect() as con:
        return [dict(r) for r in con.execute(
            "SELECT username, role, created_at, last_login FROM users ORDER BY id")]


# ---------- phien dang nhap ----------
def _th(token):
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def create_session(user_id, remember):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    ttl = REMEMBER_DAYS * 86400 if remember else SESSION_HOURS * 3600
    with connect() as con:
        con.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
        con.execute("INSERT INTO sessions(token_hash,user_id,created_at,expires_at,remember) VALUES(?,?,?,?,?)",
                    (_th(token), user_id, now, now + ttl, 1 if remember else 0))
    return token, ttl


def session_user(token):
    if not token or len(token) > 100:
        return None
    try:
        h = _th(token)
    except UnicodeEncodeError:
        return None
    with connect() as con:
        row = con.execute(
            "SELECT u.id, u.username, u.role FROM sessions s JOIN users u ON u.id=s.user_id "
            "WHERE s.token_hash=? AND s.expires_at>?", (h, int(time.time()))).fetchone()
    return {"id": row["id"], "name": row["username"], "role": row["role"]} if row else None


def end_session(token):
    if token and len(token) <= 100:
        try:
            with connect() as con:
                con.execute("DELETE FROM sessions WHERE token_hash=?", (_th(token),))
        except UnicodeEncodeError:
            pass


# ---------- gioi han so lan thu ----------
def rate_locked(key):
    """So giay con bi khoa (0 = khong khoa)."""
    with connect() as con:
        r = con.execute("SELECT locked_until FROM rate WHERE key=?", (key,)).fetchone()
    return max(0, int(round(r["locked_until"] - time.time()))) if r else 0


def rate_hit(key, limit):
    """Ghi nhan mot lan (sai / dang ky). Vuot nguong thi khoa. Tra ve so giay bi khoa (0 neu chua)."""
    n, window, lock = limit
    now = time.time()
    with connect() as con:
        r = con.execute("SELECT count, window_start FROM rate WHERE key=?", (key,)).fetchone()
        if not r or now - r["window_start"] > window:
            count, start = 1, now
        else:
            count, start = r["count"] + 1, r["window_start"]
        locked = 0.0
        if count >= n:
            locked, count, start = now + lock, 0, now
        con.execute("INSERT OR REPLACE INTO rate(key,count,window_start,locked_until) VALUES(?,?,?,?)",
                    (key, count, start, locked))
    return int(round(lock)) if locked else 0


def rate_clear(key):
    with connect() as con:
        con.execute("DELETE FROM rate WHERE key=?", (key,))
