// Trang dang nhap / dang ky
import {$} from "./utils/dom.js";
import {registerUser, verifyLogin, startSession, getSession, rememberedUser, lockSeconds, MIN_PASS} from "./auth.js";

const HOME = "index.html";
if(getSession()) location.replace(HOME);

let mode = "login";
const form = $("authForm"), msg = $("msg"), btn = $("btnSubmit");

function say(text, kind){
  msg.textContent = text || "";
  msg.className = "msg" + (text ? " show " + (kind || "err") : "");
}
function setMode(m){
  mode = m;
  const reg = m === "register";
  $("tabLogin").setAttribute("aria-selected", String(!reg));
  $("tabRegister").setAttribute("aria-selected", String(reg));
  $("tabLogin").classList.toggle("on", !reg);
  $("tabRegister").classList.toggle("on", reg);
  $("rowConfirm").hidden = !reg;
  $("rowOpts").hidden = reg;
  $("btnLabel").textContent = reg ? "Tạo tài khoản" : "Đăng nhập";
  $("pw").autocomplete = reg ? "new-password" : "current-password";
  $("forgot").hidden = true;
  say("");
}
$("tabLogin").addEventListener("click", () => setMode("login"));
$("tabRegister").addEventListener("click", () => setMode("register"));

// Hien / an mat khau
document.querySelectorAll("[data-eye]").forEach(b => b.addEventListener("click", () => {
  const inp = $(b.dataset.eye), show = inp.type === "password";
  inp.type = show ? "text" : "password";
  b.setAttribute("aria-pressed", String(show));
  b.setAttribute("aria-label", show ? "Ẩn mật khẩu" : "Hiện mật khẩu");
  b.classList.toggle("shown", show);
}));

$("lnkForgot").addEventListener("click", e => { e.preventDefault(); $("forgot").hidden = !$("forgot").hidden; });

$("user").value = rememberedUser();
$("remember").checked = !!$("user").value;
if($("user").value) $("pw").focus(); else $("user").focus();

form.addEventListener("submit", async e => {
  e.preventDefault();
  const user = $("user").value.trim(), pw = $("pw").value;
  if(!user || !pw){ say("Vui lòng nhập tên đăng nhập và mật khẩu"); return; }
  if(mode === "register"){
    if(pw.length < MIN_PASS){ say("Mật khẩu cần ít nhất " + MIN_PASS + " ký tự"); return; }
    if(pw !== $("pw2").value){ say("Hai mật khẩu không khớp"); return; }
  }
  btn.disabled = true; btn.classList.add("busy"); say("");
  try{
    if(mode === "register"){
      const r = await registerUser(user, pw);
      if(!r.ok){ say(r.error); return; }
      const v = await verifyLogin(user, pw);
      startSession(v.name, false);
      location.replace(HOME);
    }else{
      const r = await verifyLogin(user, pw);
      if(!r.ok){ say(r.error); $("pw").select(); return; }
      startSession(r.name, $("remember").checked);
      location.replace(HOME);
    }
  }catch(err){
    say(err.message === "NO_CRYPTO"
      ? "Trình duyệt chặn mã hóa trên địa chỉ này. Hãy mở qua http://localhost:8080 hoặc HTTPS."
      : "Có lỗi xảy ra: " + err.message);
  }finally{
    btn.disabled = false; btn.classList.remove("busy");
  }
});

if(lockSeconds() > 0) say("Sai quá nhiều lần. Thử lại sau " + lockSeconds() + " giây");
