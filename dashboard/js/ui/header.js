// Thanh tieu de: trang thai broker / thiet bi / lan chay va banner canh bao
import {$} from "../utils/dom.js";
import {S, UI} from "../state/store.js";

export function renderHeader(){
  const bOk=UI.broker==="online",dOn=UI.device==="online";
  $("pBroker").className="pill "+(bOk?"good":"bad");
  $("tBroker").textContent=bOk?"Đã nối broker":(UI.broker==="refused"?"Broker từ chối":"Đang nối lại broker");
  $("pDev").className="pill "+(UI.device===null?"":(dOn?"good":"bad"));
  $("tDev").textContent=UI.device===null?"Thiết bị: chưa rõ":(dOn?"Thiết bị: online":"Thiết bị: offline");
  $("tRun").textContent=S.run===null?"Chưa có lần chạy":("Lần chạy "+S.run+(S.r?" · t = "+S.r.t+" s":""));
  document.body.classList.toggle("stale",!bOk||!dOn);
  if(!bOk)$("banner").textContent="Chưa nối được broker. Kiểm tra Mosquitto đang chạy và đã mở cổng WebSockets 9001.";
  else if(!dOn)$("banner").textContent=S.r?("Thiết bị đang offline. Số liệu hiển thị là bản tin cuối cùng (lần chạy "+S.r.run+", t = "+S.r.t+" s)."):"Thiết bị đang offline và chưa có số liệu.";
}
