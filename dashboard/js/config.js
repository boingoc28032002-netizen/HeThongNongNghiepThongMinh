// Cau hinh chung cua dashboard
export const STORAGE_KEY = "irrigation_dash_v2";   // khoa localStorage luu thong ke

// Dia chi broker (WebSockets). Co the doi bang tham so URL: ?ws=ws://dia-chi:9001
export const wsUrl = new URLSearchParams(location.search).get("ws") || "ws://127.0.0.1:9001";

// Cac topic MQTT (phai khop voi MQTT_BASE trong firmware/main.py)
const BASE = "irrigation";
export const TOPICS = {
  all: BASE + "/#",
  status: BASE + "/status",
  readings: BASE + "/readings",
  events: BASE + "/events",
  cmd: BASE + "/cmd",
};
