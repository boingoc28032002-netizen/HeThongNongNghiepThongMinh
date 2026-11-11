// Bieu do donut ti trong thoi gian
import {$} from "../../utils/dom.js";
import {S, UI} from "../../state/store.js";
import {curDur, totalDur} from "../../state/selectors.js";
import {fmtDur} from "../../utils/format.js";
import {ZCOL, STNAME, STCOL} from "../../constants.js";

export function renderDonut(){
  let segs=[],centerTop="",centerSub="";
  if(UI.donut==="zone"){
    $("donutTitle").textContent="Tỉ trọng thời gian bơm theo vùng";
    segs=[0,1,2].map(z=>({label:"Vùng "+(z+1),val:curDur(z),col:ZCOL[z]}));
    centerTop=fmtDur(totalDur());centerSub="tổng bơm";
  }else{
    $("donutTitle").textContent="Tỉ trọng thời gian theo trạng thái";
    segs=["IDLE","OPENING","RUNNING","CLOSING"].map(k=>({label:STNAME[k],val:S.stateTime[k],col:STCOL[k]}));
    centerTop=fmtDur(segs.reduce((a,s)=>a+s.val,0));centerSub="tổng quan sát";
  }
  const tot=segs.reduce((a,s)=>a+s.val,0),C=2*Math.PI*54;
  let h='<circle cx="80" cy="80" r="54" fill="none" stroke="#eef0f3" stroke-width="26"/>',cum=0;
  if(tot>0)segs.forEach(s=>{if(s.val<=0)return;const len=C*s.val/tot;
    h+='<circle cx="80" cy="80" r="54" fill="none" stroke="'+s.col+'" stroke-width="26" stroke-dasharray="'+len.toFixed(2)+' '+(C-len).toFixed(2)+'" stroke-dashoffset="'+(-cum).toFixed(2)+'" transform="rotate(-90 80 80)"/>';cum+=len;});
  h+='<text x="80" y="78" text-anchor="middle" font-size="13" font-weight="700" fill="#1d2330">'+(tot>0?centerTop:"Chưa có")+'</text><text x="80" y="95" text-anchor="middle" font-size="10" fill="#6b7280">'+(tot>0?centerSub:"số liệu")+'</text>';
  $("donut").innerHTML=h;
  $("dleg").innerHTML=segs.map(s=>'<div><i style="background:'+s.col+'"></i>'+s.label+'<b>'+(tot>0?(s.val/tot*100).toFixed(1)+"%":"-")+'</b></div>').join("");
}
