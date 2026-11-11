// Bo loc vung / pham vi, nut tai lai va toan man hinh
import {$} from "../utils/dom.js";
import {UI} from "../state/store.js";
import {render} from "./render.js";
import {getSession, endSession} from "../auth.js";

export function initToolbar(){
  const ses=getSession();
  if(ses)$("tUser").textContent=ses.user;
  $("btnLogout").addEventListener("click",()=>{endSession();location.replace("login.html");});
  $("selZone").addEventListener("change",e=>{UI.zone=e.target.value;render();});
  $("selRange").addEventListener("change",e=>{UI.range=e.target.value;render();});
  $("btnReload").addEventListener("click",()=>location.reload());
  $("btnFull").addEventListener("click",()=>{if(document.fullscreenElement)document.exitFullscreen();else document.documentElement.requestFullscreen().catch(()=>{});});
}
