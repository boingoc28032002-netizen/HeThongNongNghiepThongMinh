// Xac thuc qua may chu (server/server.py).
// Tai khoan nam trong CSDL tren may chu nen dang nhap duoc tren moi trinh duyet / thiet bi.
// Phien dang nhap la cookie HttpOnly do may chu cap, JavaScript khong doc duoc.
export const USERNAME_RE = /^[A-Za-z0-9_.-]{3,32}$/;
export const MIN_PASS = 8;

const REMEMBER_KEY = "irrigation_remember_user";   // chi nho TEN dang nhap de dien san o nhap, khong phai tai khoan

const NO_SERVER = "Không kết nối được máy chủ tài khoản. Hãy chạy tools\\run-dashboard.bat (hoặc python server/server.py) thay vì python -m http.server.";

async function call(method, url, body){
  let res;
  try{
    res = await fetch(url, {
      method, credentials: "same-origin", cache: "no-store",
      headers: body ? {"Content-Type": "application/json"} : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  }catch(e){
    return {ok: false, status: 0, error: "Không kết nối được máy chủ. Kiểm tra máy chủ đang chạy rồi thử lại."};
  }
  let data = null;
  try{ data = await res.json(); }catch(e){}
  if(!data) return {ok: false, status: res.status, error: NO_SERVER};   // vd: may chu tinh khong co /api
  return {...data, status: res.status};
}

// Trang thai may chu + nguoi dung hien tai: {ok, user|null, hasUsers, allowRegister}
export const getStatus = () => call("GET", "/api/status");

// Nguoi dung dang dang nhap, hoac null khi het phien (401). Loi mang -> nem loi de noi goi bo qua.
export async function fetchSession(){
  const r = await call("GET", "/api/me");
  if(r.status === 401) return null;
  if(r.ok) return r.user;
  throw new Error(r.error);
}

export const register = (username, password) => call("POST", "/api/register", {username, password});
export const login = (username, password, remember) => call("POST", "/api/login", {username, password, remember: !!remember});
export const logout = () => call("POST", "/api/logout", {});

export function rememberedUser(){ try{ return localStorage.getItem(REMEMBER_KEY) || ""; }catch(e){ return ""; } }
export function setRememberedUser(name){
  try{ if(name) localStorage.setItem(REMEMBER_KEY, name); else localStorage.removeItem(REMEMBER_KEY); }catch(e){}
}
