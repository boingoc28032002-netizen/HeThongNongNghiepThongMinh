// Khu dieu khien: che do, dung khan cap, mo/dong van, doi nguong. Gui lenh qua MQTT.
import {$} from "../utils/dom.js";
import {S, UI} from "../state/store.js";
import {isOpen, publish} from "../mqtt/client.js";
import {TOPICS} from "../config.js";

let ctlTimer=null;
function ctlMsg(t,bad){const n=$("ctlMsg");n.textContent=t;n.style.color=bad?"var(--red)":"var(--muted)";clearTimeout(ctlTimer);ctlTimer=setTimeout(()=>{n.textContent="";},7000);}
function sendCmd(o,label){
  if(!isOpen()||UI.broker!=="online"){ctlMsg("Chưa nối broker, lệnh không được gửi.",true);return false;}
  try{
    publish(TOPICS.cmd,JSON.stringify(o));
    ctlMsg("Đã gửi: "+label+". Trạng thái cập nhật khi thiết bị phản hồi.");return true;
  }catch(e){ctlMsg("Gửi lệnh lỗi: "+e.message,true);return false;}
}
export function renderCtl(){
  const r=S.r,can=UI.broker==="online"&&UI.device==="online",sup=!!r&&r.mode!==undefined,mode=sup?r.mode:"auto";
  document.querySelectorAll("#segMode button").forEach(b=>{b.setAttribute("aria-pressed",String(sup&&b.dataset.m===mode));b.disabled=!(can&&sup);});
  $("btnStop").disabled=!(can&&sup);$("btnThr").disabled=!(can&&sup);
  $("ctlNote").textContent=!sup?"Thiết bị chưa báo chế độ vận hành (cần main.py bản có nhận lệnh).":
    (!can?"Không điều khiển được khi mất kết nối.":
    (mode==="manual"?"Thủ công: tự mở/đóng van từng vùng, bơm tự chạy khi có van mở. Nước thấp và thời gian tối đa vẫn tự ngắt.":
    "Tự động: hệ thống tự quyết định theo độ ẩm, nhiệt độ, ánh sáng."));
  for(let i=0;i<3;i++){
    const b=$("zsw"+i),open=!!(r&&r.valves[i]);
    b.textContent=open?"Đóng van":"Mở van";b.classList.toggle("on",open);
    b.disabled=!(can&&sup&&mode==="manual");
    b.title=b.disabled?"Chuyển sang chế độ Thủ công để dùng":"";
  }
}

export function initControls(){
  $("segMode").addEventListener("click",e=>{
    const b=e.target.closest("button");if(!b||b.disabled)return;
    if(b.dataset.m==="auto")sendCmd({cmd:"mode",value:"auto"},"chế độ tự động");
    else if(confirm("Chuyển sang thủ công? Các van đang tưới sẽ đóng, sau đó bạn tự mở từng vùng."))sendCmd({cmd:"mode",value:"manual"},"chế độ thủ công");
  });
  $("btnStop").addEventListener("click",()=>{if(!$("btnStop").disabled)sendCmd({cmd:"stop"},"DỪNG KHẨN CẤP");});
  $("zones").addEventListener("click",e=>{
    const b=e.target.closest(".zsw");if(!b||b.disabled||!S.r)return;
    const z=+b.dataset.z,on=S.r.valves[z]?0:1;
    sendCmd({cmd:"zone",z:z,on:on},"Vùng "+(z+1)+(on?": mở van":": đóng van"));
  });
  $("btnThr").addEventListener("click",()=>{
    const a=+$("inStart").value,b=+$("inStop").value;
    if(!(a>=0&&b<=100&&b-a>=10)){ctlMsg("Ngưỡng không hợp lệ: cần 0 ≤ bắt đầu < dừng ≤ 100 và cách nhau ít nhất 10.",true);return;}
    sendCmd({cmd:"thr",start:a,stop:b},"ngưỡng "+a+"/"+b);
  });
}
