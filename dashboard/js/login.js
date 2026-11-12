// Trang dang nhap / dang ky. Tai khoan luu tren may chu (xem auth.js va server/server.py).
import {$} from "./utils/dom.js";
import {getStatus, login, register, rememberedUser, setRememberedUser, USERNAME_RE, MIN_PASS} from "./auth.js";

const HOME = "index.html";
const card = $("card"), form = $("authForm"), msg = $("msg"), btn = $("btnSubmit");

const ICON_LOGIN = '<path d="M14 4h4a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-4"/><path d="M4 12h11M11 8l4 4-4 4"/>';
const ICON_ADD = '<circle cx="10" cy="8" r="4"/><path d="M2 21c0-4.2 3.4-6.8 8-6.8 1.2 0 2.2.2 3.2.6"/><path d="M18 14v6M15 17h6"/>';
const TEXT = {
  login:    {title: "Đăng nhập", sub: "Truy cập hệ thống để quản lý và giám sát nông nghiệp", go: "Đăng nhập", other: "Đăng ký tài khoản"},
  register: {title: "Tạo tài khoản", sub: "Đăng ký để quản lý và giám sát hệ thống tưới", go: "Tạo tài khoản", other: "Quay lại đăng nhập"},
};

let mode = "login", allowRegister = true, lockTimer = null;

function say(text, kind){
  msg.textContent = text || "";
  msg.className = "msg" + (text ? " show " + (kind || "err") : "");
}

function setMode(m, subOverride){
  mode = m;
  const reg = m === "register", t = TEXT[m];
  card.dataset.mode = m;
  $("ttl").textContent = t.title;
  $("sub").textContent = subOverride || t.sub;
  $("btnLabel").textContent = t.go;
  $("switchLabel").textContent = t.other;
  // Nut chinh: dang nhap = mui ten vao, dang ky = them nguoi. Nut phu thi nguoc lai.
  const main = btn.querySelector("svg"), alt = $("switchIcon");
  main.innerHTML = reg ? ICON_ADD : ICON_LOGIN;
  alt.setAttribute("fill", "none"); alt.setAttribute("stroke", "currentColor");
  alt.setAttribute("stroke-width", "2"); alt.setAttribute("stroke-linecap", "round"); alt.setAttribute("stroke-linejoin", "round");
  alt.innerHTML = reg ? ICON_LOGIN : ICON_ADD;
  document.querySelectorAll(".only-register").forEach(e => e.hidden = !reg);
  document.querySelectorAll(".only-login").forEach(e => e.hidden = reg || (e.id === "forgot" && !forgotOpen));
  $("pw").autocomplete = reg ? "new-password" : "current-password";
  $("pw").value = ""; $("pw2").value = "";
  $("pwHint").classList.remove("bad");
  if(!lockTimer) say("");
  history.replaceState(null, "", reg ? "#register" : location.pathname + location.search);
}

let forgotOpen = false;
$("lnkForgot").addEventListener("click", e => {
  e.preventDefault();
  forgotOpen = !forgotOpen;
  $("forgot").hidden = !forgotOpen;
  $("lnkForgot").setAttribute("aria-expanded", String(forgotOpen));
});
$("btnSwitch").addEventListener("click", () => { setMode(mode === "login" ? "register" : "login"); $("user").focus(); });

// Hien / an mat khau
document.querySelectorAll("[data-eye]").forEach(b => b.addEventListener("click", () => {
  const inp = $(b.dataset.eye), show = inp.type === "password";
  inp.type = show ? "text" : "password";
  b.setAttribute("aria-pressed", String(show));
  b.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
  b.classList.toggle("shown", show);
}));

$("pw").addEventListener("input", () => {
  if(mode !== "register") return;
  const n = $("pw").value.length;
  $("pwHint").classList.toggle("bad", n > 0 && n < MIN_PASS);
});

// Khoa nut khi bi gioi han so lan thu (may chu tra ve so giay phai cho)
function lock(secs){
  clearInterval(lockTimer);
  let left = secs;
  const tick = () => {
    if(left <= 0){ clearInterval(lockTimer); lockTimer = null; btn.disabled = false; say(""); return; }
    btn.disabled = true;
    say("Thử quá nhiều lần. Vui lòng thử lại sau " + left + " giây");
    left--;
  };
  tick(); lockTimer = setInterval(tick, 1000);
}

form.addEventListener("submit", async e => {
  e.preventDefault();
  if(btn.disabled) return;
  const user = $("user").value.trim(), pw = $("pw").value, reg = mode === "register";
  if(!user || !pw){ say("Vui lòng nhập tên đăng nhập và mật khẩu"); return; }
  if(reg){
    if(!USERNAME_RE.test(user)){ say("Tên đăng nhập 3-32 ký tự, chỉ gồm chữ, số, dấu . _ -"); $("user").focus(); return; }
    if(pw.length < MIN_PASS){ say("Mật khẩu cần ít nhất " + MIN_PASS + " ký tự"); $("pw").focus(); return; }
    if(pw !== $("pw2").value){ say("Hai mật khẩu không khớp"); $("pw2").focus(); return; }
  }
  btn.disabled = true; btn.classList.add("busy"); say("");
  const remember = $("remember").checked;
  const r = reg ? await register(user, pw) : await login(user, pw, remember);
  btn.classList.remove("busy");
  if(r.ok){
    // Chi nho ten dang nhap de dien san lan sau; tai khoan that nam tren may chu
    setRememberedUser(!reg && remember ? r.user.name : null);
    say(reg ? "Đã tạo tài khoản. Đang vào hệ thống..." : "Đăng nhập thành công...", "ok");
    location.replace(HOME);
    return;
  }
  if(r.status === 429 && r.retryAfter){ lock(r.retryAfter); return; }
  btn.disabled = false;
  say(r.error || "Có lỗi xảy ra, vui lòng thử lại");
  if(!reg && r.status === 401){ $("pw").select(); }
});

async function start(){
  const s = await getStatus();
  if(!s.ok){ say(s.error); return; }
  if(s.user){ location.replace(HOME); return; }          // da dang nhap (cookie con han)
  allowRegister = s.allowRegister;
  $("btnSwitch").hidden = !allowRegister;
  document.querySelector(".or").hidden = !allowRegister;

  const wantsRegister = allowRegister && (location.hash === "#register" || !s.hasUsers);
  if(!s.hasUsers && allowRegister) setMode("register", "Chưa có tài khoản nào. Tài khoản đầu tiên sẽ là quản trị viên.");
  else setMode(wantsRegister ? "register" : "login");
  if(!s.hasUsers && !allowRegister) say("Chưa có tài khoản nào. Quản trị viên cần tạo bằng: python server/manage.py add <tên>");
}

const last = rememberedUser();
$("user").value = last;
$("remember").checked = !!last;
start().then(() => { (last && mode === "login" ? $("pw") : $("user")).focus(); });
window.addEventListener("pageshow", e => { if(e.persisted) start(); });
