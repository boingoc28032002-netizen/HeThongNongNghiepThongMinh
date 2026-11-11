// Ma hoa / giai ma goi tin MQTT 3.1.1 (toi gian, chi du de subscribe + publish QoS 0)
// MQTT_CODEC_BEGIN
export const enc = new TextEncoder(), dec = new TextDecoder();
export function mqStr(s){const b=enc.encode(s);const r=new Uint8Array(2+b.length);r[0]=b.length>>8;r[1]=b.length&255;r.set(b,2);return r;}
export function mqLen(n){const a=[];do{let d=n%128;n=Math.floor(n/128);if(n>0)d|=128;a.push(d);}while(n>0);return Uint8Array.from(a);}
export function concat(){let n=0;for(const p of arguments)n+=p.length;const r=new Uint8Array(n);let o=0;for(const p of arguments){r.set(p,o);o+=p.length;}return r;}
export function packet(first,body){return concat(Uint8Array.of(first),mqLen(body.length),body);}
export function connectPacket(id){return packet(0x10,concat(mqStr("MQTT"),Uint8Array.of(4,0x02,0,30),mqStr(id)));}
export function subscribePacket(pid,filter){return packet(0x82,concat(Uint8Array.of(pid>>8,pid&255),mqStr(filter),Uint8Array.of(0)));}
export function parsePackets(buf){
  const out=[];let i=0;
  while(buf.length-i>=2){
    let j=i+1,mult=1,len=0,ok=false;
    while(j<buf.length){const d=buf[j++];len+=(d&127)*mult;if(!(d&128)){ok=true;break;}mult*=128;if(mult>2097152)throw new Error("do dai khong hop le");}
    if(!ok||buf.length-j<len)break;
    out.push({type:buf[i]>>4,flags:buf[i]&15,body:buf.subarray(j,j+len)});
    i=j+len;
  }
  return {packets:out,rest:buf.subarray(i)};
}
export function decodePublish(p){
  const tl=(p.body[0]<<8)|p.body[1];let off=2+tl;if(((p.flags>>1)&3)>0)off+=2;
  return {topic:dec.decode(p.body.subarray(2,2+tl)),payload:dec.decode(p.body.subarray(off)),retain:!!(p.flags&1)};
}
// MQTT_CODEC_END
