// Ham dinh dang chuoi
export function fmtDur(s){s=Math.round(s);if(s<60)return s+" s";return Math.floor(s/60)+" phút "+("0"+(s%60)).slice(-2)+" s";}
export function f1(v){return v===null||v===undefined?"-":(+v).toFixed(1);}
export function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
