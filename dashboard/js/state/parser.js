// Phan tich chuoi su kien tu thiet bi thanh doi tuong co cau truc
export function parseEvent(e){
  const text=String(e.text);
  let m=/^STATE (\w+) -> (\w+) zone=(\w+) t=[\d.]+ ?(.*)$/.exec(text);
  if(m)return {t:e.t,kind:"state",from:m[1],to:m[2],zone:m[3]==="None"?null:+m[3],note:m[4]||""};
  m=/^WATER (low|ok) ([\d.]+)/.exec(text);
  if(m)return {t:e.t,kind:"water",level:m[1],val:m[2],zone:null,note:""};
  const ev=(zone,txt,tag)=>({t:e.t,kind:"env",zone:zone,tag:tag||"",text:txt});
  m=/^TEMP band (\w+) -> (\w+) (\S+)/.exec(text);
  if(m){const nm={normal:"bình thường",hot:"nóng",cool:"mát"};return ev(null,"Dải nhiệt "+(nm[m[1]]||m[1])+" → "+(nm[m[2]]||m[2])+" ("+m[3]+"), ngưỡng tưới đổi theo");}
  m=/^TEMP (hot|cold) alarm (on|off)/.exec(text);
  if(m)return ev(null,(m[1]==="hot"?"Quá nóng":"Quá lạnh")+(m[2]==="on"?": bật cảnh báo":": hết cảnh báo"),m[2]==="on"?"warn":"ok");
  m=/^TEMP (fault|ok)$/.exec(text);
  if(m)return ev(null,m[1]==="fault"?"Cảm biến nhiệt độ lỗi, dùng ngưỡng mặc định":"Cảm biến nhiệt độ hoạt động lại",m[1]==="fault"?"warn":"ok");
  m=/^NIGHT (on|off)/.exec(text);
  if(m)return ev(null,m[1]==="on"?"Trời tối: vào chế độ đêm":"Trời sáng: hết chế độ đêm");
  m=/^HARSH (on|off)/.exec(text);
  if(m)return ev(null,m[1]==="on"?"Nắng gắt: hoãn tưới các vùng chưa nguy cấp":"Hết nắng gắt");
  m=/^DEFER zone=(\d+) (on harsh|off)/.exec(text);
  if(m)return ev(+m[1],m[2]==="off"?"Hết hoãn tưới":"Hoãn tưới vì nắng gắt");
  m=/^MODE (\w+)/.exec(text);
  if(m)return ev(null,"Chuyển chế độ "+(m[1]==="manual"?"thủ công":"tự động"));
  m=/^MANUAL zone=(\d+) (on|off)/.exec(text);
  if(m)return ev(+m[1],"Thủ công: "+(m[2]==="on"?"mở van":"đóng van"));
  m=/^STOP all/.exec(text);
  if(m)return ev(null,"DỪNG KHẨN CẤP: tắt bơm và mọi van, chuyển sang thủ công","warn");
  m=/^THR (\d+) (\d+)/.exec(text);
  if(m)return ev(null,"Đổi ngưỡng tưới: bắt đầu "+m[1]+", dừng "+m[2]);
  m=/^CMD rejected: (.*)$/.exec(text);
  if(m)return ev(null,"Thiết bị từ chối lệnh: "+m[1],"warn");
  return {t:e.t,kind:"other",zone:null,note:text};
}
