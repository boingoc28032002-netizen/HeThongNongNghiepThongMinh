// Xac thuc phia trinh duyet (khong co may chu).
// Tai khoan luu trong localStorage cua trinh duyet nay, mat khau duoc bam PBKDF2-SHA256 kem salt rieng.
// Day chi la cong dang nhap cho giao dien, KHONG thay the xac thuc that tren may chu.
const USERS_KEY = "irrigation_users_v1";
const SESSION_KEY = "irrigation_session";
const REMEMBER_KEY = "irrigation_remember_user";
const LOCK_KEY = "irrigation_login_lock";
const ITER = 150000;
export const MAX_FAILS = 5, LOCK_MS = 30000;

const enc = new TextEncoder();
const toHex = b => [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join("");
const fromHex = h => new Uint8Array(h.match(/../g).map(x => parseInt(x, 16)));

function readJson(store, key, def){
  try{ const v = store.getItem(key); return v ? JSON.parse(v) : def; }catch(e){ return def; }
}
function loadUsers(){ return readJson(localStorage, USERS_KEY, {}); }
function saveUsers(u){ localStorage.setItem(USERS_KEY, JSON.stringify(u)); }

async function derive(password, saltBytes){
  if(!(window.crypto && crypto.subtle)) throw new Error("NO_CRYPTO");
  const key = await crypto.subtle.importKey("raw", enc.encode(password), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({name:"PBKDF2", hash:"SHA-256", salt:saltBytes, iterations:ITER}, key, 256);
  return toHex(bits);
}
function same(a, b){ // so sanh khong dung som
  if(a.length !== b.length) return false;
  let d = 0; for(let i = 0; i < a.length; i++) d |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return d === 0;
}

export const USERNAME_RE = /^[A-Za-z0-9_.-]{3,32}$/;
export const MIN_PASS = 6;

// Dang ky: tra ve {ok:true} hoac {ok:false, error}
export async function registerUser(username, password){
  if(!USERNAME_RE.test(username)) return {ok:false, error:"Tên đăng nhập 3-32 ký tự, chỉ gồm chữ, số, dấu . _ -"};
  if(password.length < MIN_PASS) return {ok:false, error:"Mật khẩu cần ít nhất " + MIN_PASS + " ký tự"};
  const users = loadUsers(), key = username.toLowerCase();
  if(users[key]) return {ok:false, error:"Tên đăng nhập đã tồn tại"};
  const salt = crypto.getRandomValues(new Uint8Array(16));
  users[key] = {name: username, salt: toHex(salt), hash: await derive(password, salt), created: Date.now()};
  saveUsers(users);
  return {ok:true};
}

function lockLeft(){
  const l = readJson(localStorage, LOCK_KEY, {n:0, until:0});
  return Math.max(0, l.until - Date.now());
}
export const lockSeconds = () => Math.ceil(lockLeft() / 1000);

// Dang nhap: tra ve {ok:true, name} hoac {ok:false, error}
export async function verifyLogin(username, password){
  if(lockLeft() > 0) return {ok:false, error:"Sai quá nhiều lần. Thử lại sau " + lockSeconds() + " giây"};
  const u = loadUsers()[username.toLowerCase()];
  // Voi tai khoan khong ton tai van tinh bam de thoi gian phan hoi khong lo ra
  const salt = u ? fromHex(u.salt) : crypto.getRandomValues(new Uint8Array(16));
  const h = await derive(password, salt);
  if(u && same(h, u.hash)){
    localStorage.removeItem(LOCK_KEY);
    return {ok:true, name:u.name};
  }
  const l = readJson(localStorage, LOCK_KEY, {n:0, until:0});
  l.n = (l.n || 0) + 1;
  if(l.n >= MAX_FAILS){ l.until = Date.now() + LOCK_MS; l.n = 0; }
  localStorage.setItem(LOCK_KEY, JSON.stringify(l));
  return {ok:false, error: l.until > Date.now() ? "Sai quá nhiều lần. Thử lại sau " + lockSeconds() + " giây" : "Sai tên đăng nhập hoặc mật khẩu"};
}

// Phien dang nhap: nho tai khoan -> localStorage (con sau khi dong trinh duyet), khong -> sessionStorage
export function startSession(name, remember){
  endSession();
  const v = JSON.stringify({user:name, at:Date.now()});
  (remember ? localStorage : sessionStorage).setItem(SESSION_KEY, v);
  try{ if(remember) localStorage.setItem(REMEMBER_KEY, name); else localStorage.removeItem(REMEMBER_KEY); }catch(e){}
}
export function endSession(){
  try{ sessionStorage.removeItem(SESSION_KEY); localStorage.removeItem(SESSION_KEY); }catch(e){}
}
export function getSession(){
  const s = readJson(sessionStorage, SESSION_KEY, null) || readJson(localStorage, SESSION_KEY, null);
  return s && s.user ? s : null;
}
export const rememberedUser = () => { try{ return localStorage.getItem(REMEMBER_KEY) || ""; }catch(e){ return ""; } };
