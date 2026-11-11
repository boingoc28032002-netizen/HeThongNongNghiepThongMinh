// Bieu do duong (SVG) + tooltip khi re chuot
import {$} from "../../utils/dom.js";
import {S, UI} from "../../state/store.js";
import {curThr} from "../../state/selectors.js";
import {f1} from "../../utils/format.js";
import {ZCOL, ZSHAPE, ZDASH, STNAME} from "../../constants.js";

/* duong cong tron (monotone cubic) di qua cac diem, khong vuot qua gia tri that */
function smoothPath(p){
  const n=p.length,f=v=>v.toFixed(1);
  if(n<2)return "";
  let d="M"+f(p[0][0])+","+f(p[0][1]);
  if(n===2)return d+"L"+f(p[1][0])+","+f(p[1][1]);
  const dx=[],m=[],t=[];
  for(let i=0;i<n-1;i++){dx[i]=p[i+1][0]-p[i][0];m[i]=dx[i]?(p[i+1][1]-p[i][1])/dx[i]:0;}
  t[0]=m[0];t[n-1]=m[n-2];
  for(let i=1;i<n-1;i++)t[i]=m[i-1]*m[i]<=0?0:(m[i-1]+m[i])/2;
  for(let i=0;i<n-1;i++){
    if(m[i]===0){t[i]=t[i+1]=0;continue;}
    const a=t[i]/m[i],b=t[i+1]/m[i],s=a*a+b*b;
    if(s>9){const k=3/Math.sqrt(s);t[i]=k*a*m[i];t[i+1]=k*b*m[i];}
  }
  for(let i=0;i<n-1;i++){const h=dx[i]/3;
    d+="C"+f(p[i][0]+h)+","+f(p[i][1]+t[i]*h)+" "+f(p[i+1][0]-h)+","+f(p[i+1][1]-t[i+1]*h)+" "+f(p[i+1][0])+","+f(p[i+1][1]);}
  return d;
}
function marker(shape,x,y,col){
  if(shape==="circle")return '<circle cx="'+x+'" cy="'+y+'" r="4" fill="'+col+'" stroke="#fff" stroke-width="1.6"/>';
  if(shape==="square")return '<rect x="'+(x-3.4)+'" y="'+(y-3.4)+'" width="6.8" height="6.8" fill="'+col+'"/>';
  return '<polygon points="'+x+','+(y-4.6)+' '+(x+4.6)+','+y+' '+x+','+(y+4.6)+' '+(x-4.6)+','+y+'" fill="'+col+'"/>';
}
let CC=null;   // boi canh bieu do cho tooltip
export function renderChart(){
  const tab=UI.chart,svg=$("chart");
  const W=640,H=270,L=44,R=tab==="combo"?40:14,T=12,B=30;
  const titles={soil:"Biến động độ ẩm đất",water:"Biến động mực nước",light:"Biến động ánh sáng",temp:"Biến động nhiệt độ (°C)",combo:"Nhiệt độ và độ ẩm đất cùng trục thời gian"};
  $("chartTitle").textContent=titles[tab];
  const data=UI.range==="all"?S.hist:S.hist.slice(-60);
  let tMax=50;
  data.forEach(d=>{if(d.temp!==null&&d.temp!==undefined&&d.temp>tMax-2)tMax=Math.ceil((d.temp+2)/10)*10;});
  const TH=curThr();
  let series=[],th=[],leftMax=100;
  if(tab==="soil"||tab==="combo"){
    const zs=UI.zone==="all"?[0,1,2]:[+UI.zone];
    series=zs.map(z=>({name:"Vùng "+(z+1),col:ZCOL[z],shape:ZSHAPE[z],dash:ZDASH[z],den:100,get:d=>d.soil[z]}));
    th=[{v:TH[0],den:100,l:TH[0]+": bắt đầu tưới"},{v:TH[1],den:100,l:TH[1]+": dừng tưới"}];
    if(tab==="combo")series.push({name:"Nhiệt độ (°C, trục phải)",col:"#dc2626",shape:"circle",dash:"10 3 2 3",den:tMax,get:d=>d.temp});
  }else if(tab==="water"){series=[{name:"Mực nước",col:"#2563eb",shape:"circle",dash:"",den:100,get:d=>d.water}];th=[{v:20,den:100,l:"20: chặn tưới",below:true},{v:25,den:100,l:"25: phục hồi"}];}
  else if(tab==="light"){series=[{name:"Ánh sáng",col:"#d97706",shape:"diamond",dash:"",den:100,get:d=>d.light}];th=[{v:15,den:100,l:"15: vào chế độ đêm",below:true},{v:80,den:100,l:"80: rất sáng"}];}
  else{leftMax=tMax;series=[{name:"Nhiệt độ",col:"#dc2626",shape:"circle",dash:"",den:tMax,get:d=>d.temp}];
    th=[{v:15,den:tMax,l:"15: mát, tưới muộn hơn",below:true},{v:32,den:tMax,l:"32: nóng, tưới sớm hơn"},{v:40,den:tMax,l:"40: cảnh báo quá nóng"}];}
  const yf=f=>T+(H-T-B)*(1-Math.max(0,Math.min(1,f)));
  let h='';
  for(let k=0;k<=4;k++){const f=k/4;
    h+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yf(f)+'" y2="'+yf(f)+'" stroke="#edf1f7"/><text x="'+(L-8)+'" y="'+(yf(f)+4)+'" font-size="11" text-anchor="end" fill="#8b97a8">'+(+(f*leftMax).toFixed(1))+(tab==="temp"?"":"%")+'</text>';
    if(tab==="combo")h+='<text x="'+(W-R+6)+'" y="'+(yf(f)+4)+'" font-size="11" fill="#dc2626">'+(+(f*tMax).toFixed(1))+'</text>';
  }
  const thLines=()=>{let o='';th.forEach(q=>{const yy=yf(q.v/q.den);o+='<line x1="'+L+'" x2="'+(W-R)+'" y1="'+yy+'" y2="'+yy+'" stroke="#6b7280" stroke-dasharray="5 4"/>';
    o+='<text x="'+(W-R-4)+'" y="'+(yy+(q.below?14:-4))+'" font-size="11" text-anchor="end" fill="#6b7280">'+q.l+'</text>';});return o;};
  let x=null,anyNight=false,anyHarsh=false;
  if(data.length>=2){
    const t0=data[0].t,t1=data[data.length-1].t,span=Math.max(0.001,t1-t0);
    x=t=>L+(W-L-R)*(t-t0)/span;
    for(let i=0;i<data.length;i++){            // to nen: ban dem, nang gat, bom chay
      const xa=x(data[i].t),xb=i+1<data.length?x(data[i+1].t):xa+4,wd=Math.max(2,xb-xa).toFixed(1);
      const rc=(col,op)=>'<rect x="'+xa.toFixed(1)+'" y="'+T+'" width="'+wd+'" height="'+(H-T-B)+'" fill="'+col+'" opacity="'+op+'"/>';
      if(data[i].night){h+=rc("#475569",".16");anyNight=true;}
      if(data[i].harsh){h+=rc("#ea580c",".18");anyHarsh=true;}
      if(data[i].pump)h+=rc("#2563eb",".10");
    }
    h+=thLines();
    for(let k=0;k<=4;k++){const tt=t0+span*k/4;h+='<text x="'+x(tt).toFixed(1)+'" y="'+(H-10)+'" font-size="11" text-anchor="'+(k===0?"start":(k===4?"end":"middle"))+'" fill="#8b97a8">'+tt.toFixed(0)+' s</text>';}
    series.forEach(s=>{
      const yy=v=>yf(v/s.den).toFixed(1);
      const pa=[];data.forEach(d=>{const v=s.get(d);if(v!==null&&v!==undefined)pa.push([x(d.t),+yy(v)]);});
      if(pa.length)h+='<path fill="none" stroke="'+s.col+'" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"'+(s.dash?' stroke-dasharray="'+s.dash+'"':'')+' d="'+smoothPath(pa)+'"/>';
      data.forEach((d,i)=>{const v=s.get(d);if(v===null||v===undefined)return;
        if(data.length<=30||i===data.length-1)h+=marker(s.shape,+x(d.t).toFixed(1),+yy(v),s.col);});
    });
    h+='<line id="cur" x1="0" x2="0" y1="'+T+'" y2="'+(H-B)+'" stroke="#111827" stroke-width="1" opacity="0"/>';
  }else{
    h+=thLines();
    h+='<text x="'+(W/2)+'" y="'+(H/2)+'" font-size="14" text-anchor="middle" fill="#6b7280">Đang chờ thêm số liệu từ thiết bị</text>';
  }
  svg.innerHTML=h;
  CC=(data.length>=2)?{data:data,x:x,series:series,W:W,L:L,R:R}:null;
  let lg='';
  series.forEach(s=>{lg+='<span><svg width="30" height="12"><line x1="0" x2="30" y1="6" y2="6" stroke="'+s.col+'" stroke-width="2.4" stroke-dasharray="'+s.dash+'"/>'+marker(s.shape,15,6,s.col)+'</svg>'+s.name+'</span>';});
  lg+='<span><svg width="16" height="12"><rect width="16" height="12" fill="#2563eb" opacity=".18"/></svg>Bơm chạy</span>';
  if(anyNight)lg+='<span><svg width="16" height="12"><rect width="16" height="12" fill="#475569" opacity=".3"/></svg>Ban đêm</span>';
  if(anyHarsh)lg+='<span><svg width="16" height="12"><rect width="16" height="12" fill="#ea580c" opacity=".35"/></svg>Nắng gắt (hoãn tưới)</span>';
  $("chartLegend").innerHTML=lg;
}
export function initChartHover(){
  const svg=$("chart"),tip=$("tip"),wrap=$("chartWrap");
  svg.addEventListener("mousemove",ev=>{
    if(!CC)return;
    const rect=svg.getBoundingClientRect(),xv=(ev.clientX-rect.left)/rect.width*CC.W;
    let best=0,bd=1e9;CC.data.forEach((d,i)=>{const dd=Math.abs(CC.x(d.t)-xv);if(dd<bd){bd=dd;best=i;}});
    const d=CC.data[best],cx=CC.x(d.t),cur=$("cur");
    if(cur){cur.setAttribute("x1",cx);cur.setAttribute("x2",cx);cur.setAttribute("opacity",".5");}
    let html='<b>t = '+d.t+' s</b>';
    CC.series.forEach(s=>{html+='<br><span style="color:'+s.col+'">&#9632;</span> '+s.name+': '+f1(s.get(d));});
    html+='<br>Bơm: '+(d.pump?"chạy":"tắt")+' ('+(STNAME[d.state]||d.state)+')';
    if(d.night)html+='<br>Ban đêm';
    if(d.harsh)html+='<br>Nắng gắt: hoãn tưới';
    tip.innerHTML=html;tip.style.display="block";
    const px=cx/CC.W*rect.width;
    tip.style.left=Math.max(0,Math.min(px+12,wrap.clientWidth-tip.offsetWidth-4))+"px";tip.style.top="10px";
  });
  svg.addEventListener("mouseleave",()=>{tip.style.display="none";const c=$("cur");if(c)c.setAttribute("opacity","0");});
}
