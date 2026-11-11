// Ve lai toan bo giao dien tu trang thai hien tai
import {S} from "../state/store.js";
import {curThr} from "../state/selectors.js";
import {renderHeader} from "./header.js";
import {renderZoneCards} from "./zones.js";
import {renderKpis} from "./kpis.js";
import {renderChart} from "./charts/line-chart.js";
import {renderBars} from "./charts/bar-chart.js";
import {renderDonut} from "./charts/donut-chart.js";
import {renderEvents} from "./events.js";
import {renderCtl} from "./controls.js";

export function render(){
  renderHeader();
  const r=S.r,TH=curThr();
  renderZoneCards(r,TH);
  renderKpis(r,TH);
  renderChart();renderBars();renderDonut();renderEvents();renderCtl();
}
