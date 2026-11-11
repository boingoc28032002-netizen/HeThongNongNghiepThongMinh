// The tung vung tuoi: dung khung HTML mot lan, sau do cap nhat so lieu
import {$} from "../utils/dom.js";
import {S} from "../state/store.js";
import {zoneSt, curDur} from "../state/selectors.js";
import {fmtDur, f1} from "../utils/format.js";

export function buildZoneCards(){
  const zonesEl=$("zones");
  for(let i=0;i<3;i++){
    const c=document.createElement("div");c.className="card zone";c.id="z"+i;
    c.innerHTML='<div class="zh"><div class="zt"><span class="plant na" id="pl'+i+'"><svg class="ic"><use href="#i-drop"/></svg></span>Vùng '+(i+1)+'</div><span class="chip" id="zc'+i+'">Chưa có dữ liệu</span></div>'+
     '<div class="zlab">Độ ẩm đất</div>'+
     '<div class="zrow"><div class="zval"><span id="zv'+i+'">-</span><small>%</small></div>'+
     '<div class="gauge"><div class="band" id="zb'+i+'"></div><div class="fillg" id="zg'+i+'" style="width:0"></div>'+
     '<div class="mk" id="zm1'+i+'" style="left:40%"><span>40</span></div><div class="mk" id="zm2'+i+'" style="left:60%"><span>60</span></div></div></div>'+
     '<div class="znote" id="zn'+i+'"></div>'+
     '<button class="btn zsw" id="zsw'+i+'" data-z="'+i+'" disabled>Mở van</button>'+
     '<div class="zstats"><div><b id="zvalve'+i+'">-</b>Van</div><div><b id="zcnt'+i+'">0</b>Số lần tưới</div><div><b id="zdur'+i+'">0 s</b>Thời gian bơm</div></div>';
    zonesEl.appendChild(c);
  }
}

export function renderZoneCards(r,TH){
  for(let i=0;i<3;i++){
    const v=r?r.soil[i]:null,has=v!==null&&v!==undefined;
    $("zg"+i).style.width=(has?Math.max(0,Math.min(100,v)):0)+"%";
    $("zb"+i).style.left=TH[0]+"%";$("zb"+i).style.width=(TH[1]-TH[0])+"%";
    $("zm1"+i).style.left=TH[0]+"%";$("zm1"+i).firstChild.textContent=TH[0];
    $("zm2"+i).style.left=TH[1]+"%";$("zm2"+i).firstChild.textContent=TH[1];
    $("zv"+i).textContent=has?f1(v):"-";
    let note="",chip="Chưa có dữ liệu",cls="chip",pl="na";
    if(r){
      if(!has){note="Cảm biến lỗi, vùng này bị dừng";pl="na";}
      else if(v<TH[0]){note="Khô, cần tưới";pl="dry";}
      else if(v>=TH[1]){note="Đủ ẩm";pl="ok";}
      else{note="Trong khoảng "+TH[0]+"-"+TH[1]+", giữ nguyên trạng thái";pl="mid";}
      const zs=zoneSt(i);
      if(zs==="RUNNING"){chip="Đang tưới";cls="chip on";}
      else if(zs==="OPENING"){chip="Đang mở van";cls="chip wait";}
      else if(zs==="CLOSING"){chip="Đang đóng van";cls="chip wait";}
      else chip=r.valves[i]?"Van mở":"Nghỉ";
      if(zs==="IDLE"&&!r.valves[i]&&r.defer&&r.defer[i]){chip="Hoãn tưới";cls="chip wait";note="Hoãn vì nắng gắt (đất chưa nguy cấp)";}
    }
    $("zn"+i).textContent=note;$("zc"+i).textContent=chip;$("zc"+i).className=cls;$("pl"+i).className="plant "+pl;
    $("z"+i).className="card zone"+((r&&zoneSt(i)!=="IDLE")?" active":"");
    $("zvalve"+i).textContent=r?(r.valves[i]?"Mở":"Đóng"):"-";
    $("zcnt"+i).textContent=S.zoneCnt[i];$("zdur"+i).textContent=fmtDur(curDur(i));
  }
}
