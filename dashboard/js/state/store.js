// Trang thai giao dien (UI) va du lieu thong ke (S), luu vao localStorage
import {STORAGE_KEY} from "../config.js";

export const UI={broker:"connecting",device:null,drops:0,zone:"all",range:"60",chart:"soil",bar:"count",donut:"zone",ev:"all"};
export let S=null;
export function setS(v){S=v;}   // S bi gan lai khi bat dau lan chay moi
export function fresh(run){return {run:run,r:null,hist:[],events:[],sessions:[],open:null,zoneCnt:[0,0,0],zoneDur:[0,0,0],
  stateTime:{IDLE:0,OPENING:0,RUNNING:0,CLOSING:0},prevT:null,prevState:null,waterLow:0,waterBlock:false,msgs:0,
  zs:{sum:[0,0,0],n:[0,0,0]},light:{min:null,max:null},tmp:{min:null,max:null},t0:null};}

export function save(){try{localStorage.setItem(STORAGE_KEY,JSON.stringify(S));}catch(e){}}
export function load(){try{const s=JSON.parse(localStorage.getItem(STORAGE_KEY)||"null");if(s&&s.stateTime&&s.zs){s.tmp=s.tmp||{min:null,max:null};return s;}}catch(e){}return fresh(null);}
S=load();
