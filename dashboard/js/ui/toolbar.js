// Bo loc vung / pham vi, nut tai lai va toan man hinh
import {$} from "../utils/dom.js";
import {UI} from "../state/store.js";
import {render} from "./render.js";
import {fetchSession, logout} from "../auth.js";

export function initToolbar(){
  // Ten tai khoan lay tu may chu; het phien (401) thi quay lai trang dang nhap. Loi mang thi bo qua.
  const check=()=>fetchSession().then(u=>{if(!u)location.replace("login.html");else $("tUser").textContent=u.name;}).catch(()=>{});
  check();
  setInterval(check,60000);
  $("btnLogout").addEventListener("click",()=>{logout().finally(()=>location.replace("login.html"));});
  $("selZone").addEventListener("change",e=>{UI.zone=e.target.value;render();});
  $("selRange").addEventListener("change",e=>{UI.range=e.target.value;render();});
  $("btnReload").addEventListener("click",()=>location.reload());
  $("btnFull").addEventListener("click",()=>{if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>{});});
}
