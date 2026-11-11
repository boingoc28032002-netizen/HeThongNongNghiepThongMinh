// Diem vao: noi cac module lai voi nhau
import {$} from "./utils/dom.js";
import {wsUrl} from "./config.js";
import {UI} from "./state/store.js";
import {handleMessage} from "./state/handlers.js";
import {startMqtt} from "./mqtt/client.js";
import {loadIcons} from "./ui/icons.js";
import {buildZoneCards} from "./ui/zones.js";
import {initChartHover} from "./ui/charts/line-chart.js";
import {initTabs} from "./ui/tabs.js";
import {initToolbar} from "./ui/toolbar.js";
import {initControls} from "./ui/controls.js";
import {initPages} from "./ui/pages.js";
import {render} from "./ui/render.js";

$("wsUrl").textContent=wsUrl;
loadIcons();
buildZoneCards();
initChartHover();
initTabs();
initToolbar();
initControls();
initPages();

startMqtt(wsUrl,
  st=>{UI.broker=st;render();},
  (topic,payload)=>{handleMessage(topic,payload);render();});
render();
