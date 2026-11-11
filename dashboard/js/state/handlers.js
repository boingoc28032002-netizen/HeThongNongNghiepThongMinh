// Xu ly ban tin MQTT nhan duoc va cap nhat thong ke
import {S, setS, UI, fresh, save} from "./store.js";
import {parseEvent} from "./parser.js";
import {TOPICS} from "../config.js";

function reconcileZones(r){   // ban tin readings la nguon su that: van dong = vung da IDLE (bu cho STATE event bi mat luc offline / dung khan cap)
  if(!S.zst)S.zst={};if(!S.opens)S.opens={};
  for(let z=0;z<3;z++){
    if(r.valves[z])continue;
    if(S.zst[z]&&S.zst[z]!=="IDLE")S.zst[z]="IDLE";
    const o=S.opens[z];
    if(o){const end=Math.max(o.start,r.t),dur=end-o.start;
      S.sessions.push({zone:z,start:o.start,end:end,dur:dur,reason:"da dong (mat ban tin luc offline)"});
      S.zoneCnt[z]++;S.zoneDur[z]+=dur;delete S.opens[z];}
  }
}
export function addReading(r){
  if(r.run!==S.run)setS(fresh(r.run));
  reconcileZones(r);
  S.msgs++;
  if(r.temp===undefined)r.temp=null;
  if(S.prevT!==null&&r.t<=S.prevT){S.r=r;return;}   // ban tin retained gui lai, bo qua
  if(S.t0===null)S.t0=r.t;
  if(S.prevT!==null&&S.prevState&&S.stateTime[S.prevState]!==undefined)S.stateTime[S.prevState]+=r.t-S.prevT;
  S.hist.push({t:r.t,soil:r.soil,water:r.water,light:r.light,pump:r.pump,state:r.state,temp:r.temp,night:r.night||0,harsh:r.harsh||0});
  if(S.hist.length>600)S.hist.shift();
  for(let z=0;z<3;z++){const v=r.soil[z];if(v!==null){S.zs.sum[z]+=v;S.zs.n[z]++;}}
  if(r.light!==null){S.light.min=S.light.min===null?r.light:Math.min(S.light.min,r.light);
    S.light.max=S.light.max===null?r.light:Math.max(S.light.max,r.light);}
  if(r.temp!==null){S.tmp.min=S.tmp.min===null?r.temp:Math.min(S.tmp.min,r.temp);
    S.tmp.max=S.tmp.max===null?r.temp:Math.max(S.tmp.max,r.temp);}
  S.r=r;S.prevT=r.t;S.prevState=r.state;
}
export function addEvent(e){
  if(S.run===null||e.run>S.run)setS(fresh(e.run));
  if(e.run!==S.run)return;
  const p=parseEvent(e);
  S.events.push(p);if(S.events.length>300)S.events.shift();
  if(!S.opens)S.opens={};
  if(!S.zst)S.zst={};
  if(p.kind==="state"&&p.zone!==null)S.zst[p.zone]=p.to;
  if(p.kind==="state"&&p.to==="RUNNING"&&p.zone!==null)S.opens[p.zone]={zone:p.zone,start:p.t};
  else if(p.kind==="state"&&p.from==="RUNNING"&&p.zone!==null&&S.opens[p.zone]){
    const o=S.opens[p.zone];
    const dur=Math.max(0,p.t-o.start);
    S.sessions.push({zone:o.zone,start:o.start,end:p.t,dur:dur,reason:p.note});
    S.zoneCnt[o.zone]++;S.zoneDur[o.zone]+=dur;delete S.opens[p.zone];
  }else if(p.kind==="water"){if(p.level==="low"){S.waterLow++;S.waterBlock=true;}else S.waterBlock=false;}
}

// Dieu phoi ban tin theo topic. Khong bao gio nem loi (ban tin hong chi bi ghi log).
export function handleMessage(topic,payload){
  try{
    if(topic===TOPICS.status){
      if(UI.device==="online"&&payload!=="online")UI.drops++;
      UI.device=payload;
    }else if(topic===TOPICS.readings)addReading(JSON.parse(payload));
    else if(topic===TOPICS.events)addEvent(JSON.parse(payload));
    save();
  }catch(err){console.error("Ban tin loi",topic,err);}
}
