// Ham doc/tinh nhanh tu trang thai S
import {S} from "./store.js";

export function zoneSt(i){   // trang thai rieng cua tung vung (tu su kien STATE), du phong theo van + bom
  const r=S.r;if(!r)return "IDLE";
  const st=S.zst&&S.zst[i];
  if(st&&(st!=="IDLE"||!r.valves[i]))return st;
  return r.valves[i]?(r.pump?"RUNNING":"OPENING"):"IDLE";
}
export function curDur(z){const o=S.opens&&S.opens[z];return S.zoneDur[z]+((o&&S.r)?Math.max(0,S.r.t-o.start):0);}
export function totalDur(){return curDur(0)+curDur(1)+curDur(2);}
export function curThr(){const r=S.r;return (r&&r.thr&&r.thr[0]!==null&&r.thr[1]!==null&&r.thr[0]!==undefined)?[+r.thr[0],+r.thr[1]]:[40,60];}
