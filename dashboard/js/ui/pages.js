// Chuyen trang theo menu: moi muc menu hien dung cac khoi co data-pages tuong ung
import {$} from "../utils/dom.js";

const TITLES={overview:"Tổng quan hệ thống",zones:"Giám sát khu vực tưới",charts:"Biểu đồ dữ liệu",log:"Nhật ký hoạt động",config:"Cấu hình hệ thống"};

function show(v){
  if(!TITLES[v])v="overview";
  document.querySelectorAll("[data-pages]").forEach(e=>{e.hidden=!e.dataset.pages.split(" ").includes(v);});
  document.querySelectorAll(".nav-i[data-view]").forEach(a=>{
    const on=a.dataset.view===v;
    a.classList.toggle("active",on);
    if(on)a.setAttribute("aria-current","page");else a.removeAttribute("aria-current");
  });
  $("pageTitle").textContent=TITLES[v];
  const m=document.querySelector(".main");if(m)m.scrollTop=0;
}

export function initPages(){
  document.querySelectorAll(".nav-i[data-view]").forEach(a=>a.addEventListener("click",e=>{
    e.preventDefault();
    history.replaceState(null,"","#"+a.dataset.view);
    show(a.dataset.view);
  }));
  window.addEventListener("hashchange",()=>show(location.hash.slice(1)));
  show(location.hash.slice(1));
}
