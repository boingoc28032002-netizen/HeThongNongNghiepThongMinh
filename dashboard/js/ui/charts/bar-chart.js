// Thanh ngang so sanh theo vung
import {$} from "../../utils/dom.js";
import {S, UI} from "../../state/store.js";
import {curDur} from "../../state/selectors.js";
import {fmtDur, f1} from "../../utils/format.js";
import {ZCOL} from "../../constants.js";

export function renderBars(){
  const kind=UI.bar;
  const titles={count:"Số lần tưới theo vùng",dur:"Thời gian bơm theo vùng",avg:"Độ ẩm trung bình theo vùng"};
  $("barTitle").textContent=titles[kind];
  const vals=[0,1,2].map(z=>kind==="count"?S.zoneCnt[z]:(kind==="dur"?curDur(z):(S.zs.n[z]?S.zs.sum[z]/S.zs.n[z]:0)));
  const mx=kind==="avg"?100:Math.max(1,...vals);
  let h='';
  vals.forEach((v,z)=>{
    const txt=kind==="count"?(v+" lần"):(kind==="dur"?fmtDur(v):f1(v));
    h+='<div class="hbar"><span>Vùng '+(z+1)+'</span><div class="track"><div class="fl" style="width:'+(v/mx*100).toFixed(1)+'%;background:'+ZCOL[z]+'"></div></div><b>'+txt+'</b></div>';
  });
  $("bars").innerHTML=h;
  const last=S.sessions.length?S.sessions[S.sessions.length-1]:null;
  $("barHint").textContent=last?("Lần tưới gần nhất: Vùng "+(last.zone+1)+", "+fmtDur(last.dur)+", bắt đầu lúc t = "+last.start.toFixed(1)+" s."):"Chưa có lần tưới nào hoàn tất trong lần chạy này.";
}
