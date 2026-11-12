#!/usr/bin/env python3
"""Quan ly tai khoan tren may chu (dung khi quen mat khau, tao tai khoan, xoa tai khoan).

  python server/manage.py list
  python server/manage.py add <ten>          tao tai khoan (hoi mat khau)
  python server/manage.py passwd <ten>       dat lai mat khau (dang xuat moi thiet bi cua tai khoan do)
  python server/manage.py delete <ten>
"""
import getpass
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import accounts  # noqa: E402


def ask_password():
    p1 = getpass.getpass("Mật khẩu mới: ")
    if p1 != getpass.getpass("Nhập lại mật khẩu: "):
        sys.exit("Hai mật khẩu không khớp")
    return p1


def fmt(t):
    return time.strftime("%Y-%m-%d %H:%M", time.localtime(t)) if t else "-"


def main(argv):
    accounts.init_db()
    cmd = argv[1] if len(argv) > 1 else ""
    name = argv[2] if len(argv) > 2 else ""
    if cmd == "list":
        rows = accounts.list_users()
        if not rows:
            print("Chưa có tài khoản nào.")
        for r in rows:
            print(f"{r['username']:<24}{r['role']:<8} tạo {fmt(r['created_at'])}   đăng nhập gần nhất {fmt(r['last_login'])}")
    elif cmd == "add" and name:
        u, err = accounts.create_user(name, ask_password())
        sys.exit(err) if err else print(f"Đã tạo tài khoản {u['name']} ({u['role']})")
    elif cmd == "passwd" and name:
        ok, err = accounts.set_password(name, ask_password())
        sys.exit(err) if not ok else print("Đã đặt lại mật khẩu")
    elif cmd == "delete" and name:
        print("Đã xóa" if accounts.delete_user(name) else "Không có tài khoản này")
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv)
