// Cac the KPI ben trai: do am, muc nuoc, anh sang, nhiet do, bom, hoat dong
import {$} from "../utils/dom.js";
import {S, UI} from "../state/store.js";
import {zoneSt, totalDur} from "../state/selectors.js";
import {f1, fmtDur} from "../utils/format.js";
import {STNAME} from "../constants.js";

function tempLabel(r,TH){
  if(r.temp===null||r.temp===undefined)return "Chưa có số liệu (LM35 chưa nối hoặc lỗi)";
  const bn={normal:"Bình thường",hot:"Nóng: tưới sớm hơn",cool:"Mát: tưới muộn hơn"}[r.band]||"";
  let t=bn+" (ngưỡng "+TH[0]+"/"+TH[1]+")";
  if(r.temp>=40)t="Quá nóng! "+t;else if(r.temp<10)t="Quá lạnh! "+t;
  return t;
}
function setTri(el,cls){el.className="tri "+cls;}

export function renderKpis(r,TH){
  if(r){
    const vs=r.soil.filter(v=>v!==null);
    if(vs.length){
      const avg=vs.reduce((a,b)=>a+b,0)/vs.length;
      $("kSoil").textContent=avg.toFixed(1);
      if(avg>=TH[1]){setTri($("kSoilTri"),"up");$("kSoilL").textContent="Đủ ẩm";}
      else if(avg<TH[0]){setTri($("kSoilTri"),"down");$("kSoilL").textContent="Khô, cần tưới";}
      else{setTri($("kSoilTri"),"mid");$("kSoilL").textContent="Trong khoảng "+TH[0]+"-"+TH[1];}
      $("kSoilMin").textContent=Math.min.apply(null,vs).toFixed(1);$("kSoilMax").textContent=Math.max.apply(null,vs).toFixed(1);
    }
    $("kWater").textContent=f1(r.water);
    const low=r.water===null||r.water<20||S.waterBlock===true;
    setTri($("kWaterTri"),low?"down":"up");$("kWaterL").textContent=low?(r.water!==null&&r.water>=20?"Đang chờ phục hồi (cần từ 25)":"Nước thấp, chặn tưới"):"Đủ nước để tưới";
    $("kLight").textContent=f1(r.light);$("kLightMin").textContent=f1(S.light.min);$("kLightMax").textContent=f1(S.light.max);
    $("kLightL").textContent="Cường độ hiện tại (thang 0-100)"+(r.harsh?" · Nắng gắt":(r.night?" · Ban đêm":""));
    const hasT=r.temp!==null&&r.temp!==undefined;
    $("kTemp").textContent=hasT?f1(r.temp):"-";
    $("kTempMin").textContent=S.tmp.min===null?"-":f1(S.tmp.min);$("kTempMax").textContent=S.tmp.max===null?"-":f1(S.tmp.max);
    $("kTempL").textContent=tempLabel(r,TH);
    $("kPump").textContent=r.pump?"ON":"OFF";$("kPump").classList.toggle("on",!!r.pump);
    $("kPumpL").textContent=(function(){const rz=[0,1,2].filter(k=>zoneSt(k)==="RUNNING").map(k=>k+1);return r.pump&&rz.length?("Đang tưới Vùng "+rz.join(", ")):(STNAME[r.state]||r.state);})();
  }
  $("kCnt").textContent=S.sessions.length;$("kDur").textContent=fmtDur(totalDur());
  const obs=(S.prevT!==null&&S.t0!==null)?S.prevT-S.t0:0;
  $("kDuty").textContent=obs>0?Math.min(100,totalDur()/obs*100).toFixed(1)+"%":"-";
  $("kDrops").textContent=UI.drops;$("kWlow").textContent=S.waterLow;
}
