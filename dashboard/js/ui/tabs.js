// Cac nhom tab (bieu do, thanh, donut, nhat ky)
import {$} from "../utils/dom.js";
import {UI} from "../state/store.js";
import {render} from "./render.js";

function wireTabs(id,key){
  const el=$(id);
  el.addEventListener("click",e=>{
    const b=e.target.closest(".tab");if(!b)return;
    UI[key]=b.dataset.v;
    el.querySelectorAll(".tab").forEach(t=>t.setAttribute("aria-selected",t===b?"true":"false"));
    render();
  });
}

export function initTabs(){
  wireTabs("tabsChart","chart");wireTabs("tabsBar","bar");wireTabs("tabsDonut","donut");wireTabs("tabsEv","ev");
}
