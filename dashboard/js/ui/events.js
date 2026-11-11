// Bang nhat ky su kien
import {$} from "../utils/dom.js";
import {S, UI} from "../state/store.js";
import {esc} from "../utils/format.js";
import {STNAME, REASON, WARN_REASON} from "../constants.js";

function evRow(p){
  const zone=p.zone===null?"-":"Vùng "+(p.zone+1);
  let txt="",tag="";
  if(p.kind==="state"){
    txt=(STNAME[p.from]||p.from)+" → "+(STNAME[p.to]||p.to);
    const n=p.note;
    if(n.indexOf("need soil=")===0)txt+=" (đất "+n.slice(10)+")";
    else if(REASON[n]){txt+=" ("+REASON[n]+")";if(WARN_REASON[n])tag='<span class="tag warn">Cảnh báo</span>';}
  }else if(p.kind==="water"){
    txt=(p.level==="low"?"Mực nước xuống thấp: ":"Mực nước đã phục hồi: ")+p.val;
    tag=p.level==="low"?'<span class="tag warn">Cảnh báo</span>':'<span class="tag ok">Phục hồi</span>';
  }else if(p.kind==="env"){
    txt=p.text;tag=p.tag==="warn"?'<span class="tag warn">Cảnh báo</span>':(p.tag==="ok"?'<span class="tag ok">Phục hồi</span>':"");
  }else txt=p.note;
  return '<tr><td class="n">t = '+p.t+'</td><td>'+zone+'</td><td>'+esc(txt)+tag+'</td></tr>';
}
export function renderEvents(){
  let list=S.events.slice();
  if(UI.ev==="cycle")list=list.filter(p=>p.kind==="state");
  else if(UI.ev==="env")list=list.filter(p=>p.kind==="env");
  else if(UI.ev==="warn")list=list.filter(p=>(p.kind==="water"&&p.level==="low")||(p.kind==="state"&&WARN_REASON[p.note])||(p.kind==="env"&&p.tag==="warn"));
  list=list.reverse().slice(0,60);
  $("evBody").innerHTML=list.length?list.map(evRow).join(""):'<tr><td colspan="3" class="hint">Chưa có sự kiện nào phù hợp trong lần chạy này.</td></tr>';
}
