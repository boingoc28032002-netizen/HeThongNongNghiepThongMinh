// Ket noi MQTT qua WebSockets: tu dong noi lai, subscribe irrigation/#, publish lenh
import {enc, mqStr, concat, packet, connectPacket, subscribePacket, parsePackets, decodePublish} from "./codec.js";
import {TOPICS} from "../config.js";

export let WS=null;   // WebSocket dang dung, de gui lenh dieu khien
export function startMqtt(url,onState,onMessage){
  let ws=null,buf=new Uint8Array(0),ping=null;
  function connect(){
    onState("connecting");
    try{ws=new WebSocket(url,"mqtt");}catch(e){setTimeout(connect,3000);return;}
    ws.binaryType="arraybuffer";WS=ws;
    ws.onopen=()=>{ws.send(connectPacket("dash_"+Math.random().toString(16).slice(2,8)));};
    ws.onmessage=(ev)=>{
      try{
        buf=concat(buf,new Uint8Array(ev.data));
        const r=parsePackets(buf);buf=r.rest;
        for(const p of r.packets){
          if(p.type===2){
            if(p.body[1]===0){ws.send(subscribePacket(1,TOPICS.all));onState("online");
              clearInterval(ping);ping=setInterval(()=>{try{ws.send(Uint8Array.of(0xC0,0));}catch(e){}},20000);}
            else onState("refused");
          }else if(p.type===3){const m=decodePublish(p);onMessage(m.topic,m.payload,m.retain);}
        }
      }catch(e){console.error(e);}
    };
    ws.onclose=()=>{clearInterval(ping);buf=new Uint8Array(0);onState("offline");setTimeout(connect,3000);};
    ws.onerror=()=>{try{ws.close();}catch(e){}};
  }
  connect();
}

export function isOpen(){return !!WS&&WS.readyState===1;}
export function publish(topic,payload){WS.send(packet(0x30,concat(mqStr(topic),enc.encode(payload))));}
