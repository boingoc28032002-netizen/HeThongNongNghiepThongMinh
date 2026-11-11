#!/usr/bin/env python3
# Main.py - GIAI DOAN 4F (Python VSM, Proteus RPI4 model)
# Gom (4F: them nhiet do LM35 + anh sang vao quyet dinh tuoi, canh bao, che do dem): khoi CONFIG cua Proteus (giu nguyen) + loi dieu khien 4A + lop phan cung + SQLite 4C + MQTT khong chan 4D.
# MAC DINH: ENABLE_OUTPUTS = True (dieu khien relay that). Dat False de chay kho (chi ghi log, khong xuat relay).

from goto import *
import time
import var
import pio
import resource

# Peripheral Configuration Code
#---CONFIG_BEGIN---
import cpu
import FileStore
import VFP

def peripheral_setup () :
# Peripheral Constructors
 pio.cpu=cpu.CPU ()
 pio.storage=FileStore.FileStore ()
 pio.server=VFP.VfpServer ()
 pio.storage.begin ()
 pio.server.begin (0)
# Install interrupt handlers

def peripheral_loop () :
 pio.server.poll ()

#---CONFIG_END---

import os
import traceback
import sqlite3
try:
    import json
except Exception:
    json = None   # khong co json: bo qua lenh tu dashboard, tuoi tu dong van chay

# irrigation_core.py - GIAI DOAN 4A + 4F: loi dieu khien tuoi (cac vung kho tuoi DONG THOI; them nhiet do, anh sang)
# Thuan Python, KHONG import cpu/pio/spidev/time. Thoi gian (giay mo phong)
# do ben goi truyen vao qua tham so now (dem tick: so tick * 0.05).
# Tuong thich Python 3.9. Dong log khong chua ky tu phan tram.

# ---- Cau hinh (gia tri thu nghiem, co the chinh) ----
CONFIG = {
    "start_below": 40.0,      # bat dau tuoi khi do am dat < 40 (theo de bai)
    "stop_at": 60.0,          # dung khi do am dat >= 60 (theo de bai); o giua 40-60 thi giu trang thai
    "water_low_below": 20.0,  # muc nuoc thap -> chan tuoi (GIA TRI TAM, chua duoc chot)
    "water_ok_at": 25.0,      # muc nuoc phuc hoi (tao tre, tranh nhap nhay)
    "valve_lead_s": 1.0,      # mo van truoc khi bat bom
    "valve_lag_s": 1.0,       # tat bom truoc, 1 s sau moi dong van
    "max_run_s": 300.0,       # BOM chay lien tuc toi da 300 s (5 phut); cung la gioi han moi vung
    "cooldown_s": 60.0,       # BOM nghi 60 s (1 phut) sau khi bi cat; cung la nghi toi thieu moi vung
    "max_parallel": 3,        # so vung duoc tuoi dong thoi (3 = vung nao kho la mo van ngay)
    "raw_max": 1023,
    # ---- Nhiet do / anh sang (4F). Tat ca la gia tri thu nghiem, co the chinh ----
    "temp_enabled": False,    # main.py dat True khi da noi LM35. False = bo qua nhiet do, khong bao loi cam bien
    "temp_cool_c": 15.0,      # duoi muc nay: tri tuoi thap hon (it bay hoi)
    "temp_hot_c": 32.0,       # tren muc nay: tri tuoi cao hon (dat kho nhanh)
    "temp_hyst_c": 1.0,       # tao tre cho cac moc nhiet do
    "temp_shift": 5.0,        # do doi cua start_below va stop_at o vung nong hoac mat
    "temp_alarm_hot_c": 40.0, # canh bao qua nong
    "temp_alarm_cold_c": 10.0,  # canh bao qua lanh
    "harsh_temp_on": 35.0,    # nang gat = nhiet do >= 35 VA anh sang >= 80
    "harsh_temp_off": 33.0,   # het nang gat khi nhiet do < 33 HOAC anh sang < 70
    "harsh_light_on": 80.0,
    "harsh_light_off": 70.0,
    "soil_critical": 20.0,    # dat kho duoi muc nay: tuoi ngay ke ca luc nang gat
    "night_on": 15.0,         # anh sang < 15: ban dem
    "night_off": 25.0,        # anh sang >= 25: ban ngay (tao tre)
}

ZONES = 3  # RV1/CH0->K2, RV2/CH1->K3, RV3/CH2->K4; RV4/CH3 khong tham gia dieu khien

IDLE, OPENING, RUNNING, CLOSING = "IDLE", "OPENING", "RUNNING", "CLOSING"


def raw_to_pct(raw, raw_max=1023):
    """Doi gia tri ADC 0..1023 sang thang 0..100. Tra None neu khong hop le."""
    if raw is None:
        return None
    try:
        raw = int(raw)
    except (TypeError, ValueError):
        return None
    if raw < 0 or raw > raw_max:
        return None
    return raw * 100.0 / raw_max


def raw_to_temp(raw, vref=5.0, raw_max=1023):
    """LM35: 10 mV moi do C. Tra None neu raw loi, day ho/ngan mach (raw = 0) hoac bao hoa (raw = raw_max)."""
    if raw is None:
        return None
    try:
        raw = int(raw)
    except (TypeError, ValueError):
        return None
    if raw <= 0 or raw >= raw_max:
        return None
    t = raw * vref / raw_max * 100.0
    if t < -10.0 or t > 110.0:
        return None
    return t


class TempFilter:
    """Trung vi n mau gan nhat. Mat mau lien tiep n lan thi tra None (cam bien loi that su)."""

    def __init__(self, n=5):
        self.n = n
        self.buf = []
        self.miss = 0
        self.value = None

    def push(self, t):
        if t is None:
            self.miss += 1
            if self.miss >= self.n:
                self.buf = []
                self.value = None
            return self.value
        self.miss = 0
        self.buf.append(t)
        if len(self.buf) > self.n:
            self.buf.pop(0)
        self.value = sorted(self.buf)[len(self.buf) // 2]
        return self.value


class IrrigationController:
    """Moi vung co may trang thai rieng; cac vung kho duoc mo van dong thoi, chung 1 bom.

    Bom bat khi co it nhat 1 vung o RUNNING, tat khi khong con vung nao RUNNING.
    update(now, soil, water, temp=None, light=None) tra ve (outputs, events):
      outputs = {"pump": bool, "valves": [bool, bool, bool]}  (muc LOGIC, chua phai muc GPIO)
      events  = list chuoi mo ta thay doi (de ghi log)
    soil: list 3 gia tri 0..100 (hoac None neu loi); water: 0..100 hoac None.
    temp: do C (hoac None); light: 0..100 (hoac None). Cam bien phu loi -> dung nguong mac dinh, KHONG dung tuoi.
    ctrl.state / ctrl.zone: trang thai tong hop de hien thi (zone = vung dang hoat dong co so nho nhat).
    """

    def __init__(self, cfg=None):
        self.cfg = dict(CONFIG)
        if cfg:
            self.cfg.update(cfg)
        self.zst = [IDLE] * ZONES     # trang thai tung vung
        self.t_state = [0.0] * ZONES  # thoi diem vao trang thai hien tai cua tung vung
        self.t_run_start = [0.0] * ZONES
        self.stop_reason = [""] * ZONES
        self.state = IDLE             # tong hop
        self.zone = None              # tong hop
        self.need = [False] * ZONES
        self.last_stop = [None] * ZONES
        self.water_low = False
        self.pump = False
        self.pump_since = None        # thoi diem bom bat dau chay lien tuc (None = bom dang tat)
        self.pump_rest_until = 0.0    # chua het thoi diem nay thi KHONG duoc mo van moi
        self.valves = [False] * ZONES
        # moi truong (4F)
        self.temp = None
        self.light = None
        self.temp_fault = False
        self.temp_band = "normal"     # normal / hot / cool
        self.temp_hot = False         # canh bao qua nong
        self.temp_cold = False        # canh bao qua lanh
        self.night = False
        self.harsh = False            # nang gat: hoan tuoi vung chua nguy cap
        self.deferred = [False] * ZONES
        self.eff_start = self.cfg["start_below"]
        self.eff_stop = self.cfg["stop_at"]
        # che do van hanh (dieu khien tu dashboard): auto / manual
        self.mode = "auto"
        self.manual = [False] * ZONES   # che do manual: vung nao duoc yeu cau mo

    # ---- tien ich ----
    def _outputs(self):
        return {"pump": self.pump, "valves": list(self.valves)}

    def _enter(self, z, state, now, events, note=""):
        events.append("STATE %s -> %s zone=%s t=%.2f %s" % (
            self.zst[z], state, z, now, note))
        self.zst[z] = state
        self.t_state[z] = now

    def _begin_closing(self, z, now, events, reason):
        if self.mode == "manual":
            self.manual[z] = False     # moi lan dong van (nuoc thap, qua gio, loi...) deu huy yeu cau thu cong
        self.stop_reason[z] = reason  # bom tu dong tat khi khong con vung RUNNING; van dong tre valve_lag_s
        self._enter(z, CLOSING, now, events, reason)

    def _summary(self):
        active = [z for z in range(ZONES) if self.zst[z] != IDLE]
        self.zone = active[0] if active else None
        sts = [self.zst[z] for z in active]
        if RUNNING in sts:
            self.state = RUNNING
        elif OPENING in sts:
            self.state = OPENING
        elif CLOSING in sts:
            self.state = CLOSING
        else:
            self.state = IDLE

    def _update_env(self, temp, light, events):
        """Nhiet do, anh sang: dai nhiet co tao tre, canh bao, ban dem, nang gat."""
        cfg = self.cfg
        h = cfg["temp_hyst_c"]
        self.temp = temp
        self.light = light
        fault = bool(cfg["temp_enabled"]) and temp is None
        if fault != self.temp_fault:
            self.temp_fault = fault
            events.append("TEMP fault" if fault else "TEMP ok")
        # dai nhiet: khong co so do thi dung nguong mac dinh
        band = self.temp_band
        if temp is None:
            band = "normal"
        elif band == "normal":
            if temp >= cfg["temp_hot_c"]:
                band = "hot"
            elif temp < cfg["temp_cool_c"]:
                band = "cool"
        elif band == "hot":
            if temp < cfg["temp_hot_c"] - h:
                band = "normal"
        else:
            if temp >= cfg["temp_cool_c"] + h:
                band = "normal"
        if band != self.temp_band:
            events.append("TEMP band %s -> %s %s" % (
                self.temp_band, band, "NA" if temp is None else "%.1f" % temp))
            self.temp_band = band
        shift = cfg["temp_shift"] if band == "hot" else (-cfg["temp_shift"] if band == "cool" else 0.0)
        self.eff_start = cfg["start_below"] + shift
        self.eff_stop = cfg["stop_at"] + shift
        # canh bao qua nong / qua lanh (co tao tre)
        if temp is None:
            hot = cold = False
        else:
            hot = (temp >= cfg["temp_alarm_hot_c"]) if not self.temp_hot else (temp >= cfg["temp_alarm_hot_c"] - h)
            cold = (temp < cfg["temp_alarm_cold_c"]) if not self.temp_cold else (temp < cfg["temp_alarm_cold_c"] + h)
        if hot != self.temp_hot:
            self.temp_hot = hot
            events.append("TEMP hot alarm %s" % ("on" if hot else "off"))
        if cold != self.temp_cold:
            self.temp_cold = cold
            events.append("TEMP cold alarm %s" % ("on" if cold else "off"))
        # ban dem (anh sang loi -> coi la ban ngay de canh bao van keu)
        if light is None:
            night = False
        elif not self.night:
            night = light < cfg["night_on"]
        else:
            night = light < cfg["night_off"]
        if night != self.night:
            self.night = night
            events.append("NIGHT on" if night else "NIGHT off")
        # nang gat (thieu 1 trong 2 so do -> khong hoan)
        if temp is None or light is None:
            harsh = False
        elif not self.harsh:
            harsh = temp >= cfg["harsh_temp_on"] and light >= cfg["harsh_light_on"]
        else:
            harsh = not (temp < cfg["harsh_temp_off"] or light < cfg["harsh_light_off"])
        if harsh != self.harsh:
            self.harsh = harsh
            events.append("HARSH %s" % ("on" if harsh else "off"))

    # ---- vong cap nhat ----
    def update(self, now, soil, water, temp=None, light=None):
        cfg = self.cfg
        events = []
        self._update_env(temp, light, events)

        # 1. Muc nuoc co tao tre
        water_bad = water is None
        if water_bad:
            self.water_low = True  # khong doc duoc -> coi nhu thap (an toan)
        elif self.water_low and water >= cfg["water_ok_at"]:
            self.water_low = False
            events.append("WATER ok %.1f" % water)
        elif (not self.water_low) and water < cfg["water_low_below"]:
            self.water_low = True
            events.append("WATER low %.1f" % water)

        # 2. Nhu cau tung vung (tao tre 40/60); cam bien loi -> khong co nhu cau
        fault = [False] * ZONES
        for z in range(ZONES):
            v = soil[z] if z < len(soil) else None
            if v is None:
                fault[z] = True
                self.need[z] = False
                continue
            if v < self.eff_start:
                self.need[z] = True
            elif v >= self.eff_stop:
                self.need[z] = False

        # 2b. Che do thu cong: nhu cau do nguoi dung quyet dinh (cam bien loi van chan)
        if self.mode == "manual":
            for z in range(ZONES):
                self.need[z] = bool(self.manual[z]) and not fault[z]

        # 3a. Gioi han cua BOM (dung chung 3 vung): chay lien tuc du max_run_s thi cat het, nghi cooldown_s
        if self.pump_since is not None and now - self.pump_since >= cfg["max_run_s"]:
            for z in range(ZONES):
                if self.zst[z] in (OPENING, RUNNING):
                    self._begin_closing(z, now, events, "max_run")
            # bom tat ngay tick nay (muc 5); mo van lai truoc valve_lead_s de bom bat lai dung sau cooldown_s
            self.pump_rest_until = now + max(0.0, cfg["cooldown_s"] - cfg["valve_lead_s"])
            events.append("PUMP rest %.0f s" % cfg["cooldown_s"])

        # 3. May trang thai tung vung
        for z in range(ZONES):
            st = self.zst[z]
            if st == OPENING:
                if self.water_low:
                    self._begin_closing(z, now, events, "water_low")
                elif fault[z] or not self.need[z]:
                    self._begin_closing(z, now, events, "need_gone")
                elif now - self.t_state[z] >= cfg["valve_lead_s"]:
                    self.t_run_start[z] = now
                    self._enter(z, RUNNING, now, events)
            elif st == RUNNING:
                if self.water_low:
                    self._begin_closing(z, now, events, "water_low")
                elif fault[z]:
                    self._begin_closing(z, now, events, "sensor_fault")
                elif not self.need[z]:
                    self._begin_closing(z, now, events, "target_reached")
                elif now - self.t_run_start[z] >= cfg["max_run_s"]:
                    self._begin_closing(z, now, events, "max_run")
            elif st == CLOSING:
                if now - self.t_state[z] >= cfg["valve_lag_s"]:
                    self.valves[z] = False
                    self.last_stop[z] = now
                    self._enter(z, IDLE, now, events, self.stop_reason[z])

        # 4. Vung nao dang kho (va het cooldown) thi mo van ngay, vung kho nhat truoc
        newdef = [False] * ZONES
        if (not self.water_low) and now >= self.pump_rest_until:
            active = sum(1 for z in range(ZONES) if self.zst[z] != IDLE)
            cands = []
            for z in range(ZONES):
                if self.zst[z] != IDLE or not self.need[z]:
                    continue
                ls = self.last_stop[z]
                if self.mode == "auto" and ls is not None and (now - ls) < cfg["cooldown_s"]:
                    continue
                if self.mode == "auto" and self.harsh and soil[z] >= cfg["soil_critical"]:
                    newdef[z] = True       # nang gat: hoan, tru khi dat kho nguy cap
                    continue
                cands.append(z)
            cands.sort(key=lambda zz: soil[zz])
            for z in cands:
                if active >= cfg["max_parallel"]:
                    break
                self.valves[z] = True
                self._enter(z, OPENING, now, events, "need soil=%.1f" % soil[z])
                active += 1

        for z in range(ZONES):
            if newdef[z] != self.deferred[z]:
                self.deferred[z] = newdef[z]
                events.append("DEFER zone=%d %s" % (z, "on harsh" if newdef[z] else "off"))

        # 5. Bom chay khi co it nhat 1 vung RUNNING (van cua vung do chac chan dang mo)
        self.pump = any(s == RUNNING for s in self.zst)
        if self.pump:
            if self.pump_since is None:
                self.pump_since = now
        else:
            self.pump_since = None

        self._summary()
        return self._outputs(), events

    # ---- lenh tu dashboard ----
    def set_mode(self, mode):
        if mode not in ("auto", "manual"):
            return "CMD rejected: mode"
        if mode != self.mode:
            self.mode = mode
            self.manual = [False] * ZONES
        return "MODE " + mode

    def set_zone(self, z, on):
        if self.mode != "manual" or z < 0 or z >= ZONES:
            return "CMD rejected: can che do thu cong"
        if on and self.water_low:
            return "CMD rejected: water_low"
        self.manual[z] = bool(on)
        return "MANUAL zone=%d %s" % (z, "on" if on else "off")

    def set_thresholds(self, start, stop):
        if not (0.0 <= start < stop <= 100.0 and stop - start >= 10.0):
            return "CMD rejected: nguong khong hop le"
        self.cfg["start_below"] = start
        self.cfg["stop_at"] = stop
        return "THR %d %d" % (round(start), round(stop))

    def emergency_stop(self, now):
        self.mode = "manual"
        self.manual = [False] * ZONES
        self.force_all_off(now)
        return "STOP all"

    def force_all_off(self, now=0.0):
        """Dung khan cap: tat bom va moi van ngay lap tuc."""
        self.pump = False
        self.pump_since = None
        self.valves = [False] * ZONES
        for z in range(ZONES):
            if self.zst[z] != IDLE:
                self.last_stop[z] = now
            self.zst[z] = IDLE
        self.state = IDLE
        self.zone = None
        return self._outputs()


# =====================================================================
# PHAN 4B: LOP PHAN CUNG + VONG DIEU KHIEN
# =====================================================================
ENABLE_OUTPUTS = True    # False = chay kho (chi log). Chi doi True sau khi xem log chay kho.
RELAY_ACTIVE_HIGH = True  # theo so do: GPIO HIGH -> BC547 dan -> cuon K1 hut -> NO dong

TICK = 0.05
SENSE_EVERY = 5          # doc ADC moi 10 tick (0.5 s mo phong)
STATUS_EVERY = 3         # ghi dong trang thai moi 20 tick (1 s mo phong)

CH_SOIL = [0, 1, 2]       # RV1, RV2, RV3 -> vung 1, 2, 3
CH_SOIL4 = 3              # RV4: chi ghi log, khong tham gia dieu khien
CH_LIGHT = 4              # ALS-PT19 (xac nhan tu log 3b: CH4 khong doi khi chinh RV)
CH_WATER = 5              # RV5 muc nuoc (xac nhan tu log 3b: CH5 doi theo RV5)
CH_TEMP = 6               # LM35 (VOUT -> CH6, chan 7 cua MCP3008)
TEMP_ENABLE = True        # False = chua noi LM35: bo qua nhiet do, khong bao loi
TEMP_VREF = 3.3           # dien ap VREF cua MCP3008 (5.0 neu VREF noi +5V, 3.3 neu noi 3V3)
TEMP_MEDIAN_N = 5         # loc trung vi 5 mau (moi mau cach nhau 0.5 s)

PUMP_PIN = pio.GPIO17
VALVE_PINS = [pio.GPIO27, pio.GPIO22, pio.GPIO23]   # K2, K3, K4
ALL_PINS = [("K1 bom", PUMP_PIN), ("K2 van1", VALVE_PINS[0]),
            ("K3 van2", VALVE_PINS[1]), ("K4 van3", VALVE_PINS[2])]

LOG_FILE = None
_applied = {}             # pin -> True/False (trang thai logic da ghi)


def init_log():
    global LOG_FILE
    try:
        path = os.path.join(os.getcwd(), "irrigation4b_log.txt")
        LOG_FILE = open(path, "w")
        print("LOG FILE:", path)
    except Exception as e:
        LOG_FILE = None
        print("Khong mo duoc log file:", repr(e))


def out(msg):
    print(msg)
    if LOG_FILE is not None:
        try:
            LOG_FILE.write(str(msg) + "\n")
            LOG_FILE.flush()
        except Exception:
            pass


# =====================================================================
# PHAN 4C: GHI DU LIEU SQLITE (khong bao gio duoc lam dung dieu khien)
# =====================================================================
DB_DIR = r"E:\SU PHAM KY THUAT\TLCN\Protus\irrigation_data"
DB_FILE = "irrigation.db"
DB_EVERY = 20            # ghi 1 dong readings moi 100 tick (5 s mo phong)

DB = None                 # ket noi sqlite, None neu mo that bai
DB_RUN = 0                # so thu tu lan chay


def init_db():
    """Mo DB, tao bang, tao 1 dong runs. Loi bat ky -> DB = None, dieu khien van chay."""
    global DB, DB_RUN
    try:
        if not os.path.isdir(DB_DIR):
            os.makedirs(DB_DIR)
        path = os.path.join(DB_DIR, DB_FILE)
        DB = sqlite3.connect(path)
        DB.execute("CREATE TABLE IF NOT EXISTS runs ("
                   "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                   "enable_outputs INTEGER)")
        DB.execute("CREATE TABLE IF NOT EXISTS readings ("
                   "id INTEGER PRIMARY KEY AUTOINCREMENT, run INTEGER, sim_t REAL, "
                   "state TEXT, zone INTEGER, "
                   "soil1 REAL, soil2 REAL, soil3 REAL, soil4 REAL, "
                   "water REAL, light REAL, "
                   "pump INTEGER, valve1 INTEGER, valve2 INTEGER, valve3 INTEGER, "
                   "temp REAL, night INTEGER, harsh INTEGER)")
        have = [r[1] for r in DB.execute("PRAGMA table_info(readings)")]
        for col, typ in (("temp", "REAL"), ("night", "INTEGER"), ("harsh", "INTEGER")):
            if col not in have:      # DB cu chua co cot: them vao, du lieu cu giu nguyen
                DB.execute("ALTER TABLE readings ADD COLUMN %s %s" % (col, typ))
        DB.execute("CREATE TABLE IF NOT EXISTS events ("
                   "id INTEGER PRIMARY KEY AUTOINCREMENT, run INTEGER, sim_t REAL, "
                   "text TEXT)")
        cur = DB.execute("INSERT INTO runs (enable_outputs) VALUES (?)",
                         (1 if ENABLE_OUTPUTS else 0,))
        DB_RUN = cur.lastrowid
        DB.commit()
        out("DB SAN SANG: " + path + " run=" + str(DB_RUN))
    except Exception as e:
        DB = None
        out("Mo DB LOI (van chay, khong ghi DB): " + repr(e))


def db_reading(now, ctrl, soil, soil4, water, light, outputs):
    if DB is None:
        return
    try:
        v = outputs["valves"]
        DB.execute(
            "INSERT INTO readings (run, sim_t, state, zone, soil1, soil2, soil3, "
            "soil4, water, light, pump, valve1, valve2, valve3, temp, night, harsh) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (DB_RUN, now, ctrl.state, ctrl.zone,
             soil[0], soil[1], soil[2], soil4, water, light,
             1 if outputs["pump"] else 0,
             1 if v[0] else 0, 1 if v[1] else 0, 1 if v[2] else 0,
             ctrl.temp, 1 if ctrl.night else 0, 1 if ctrl.harsh else 0))
        DB.commit()
    except Exception as e:
        out("Ghi readings LOI: " + repr(e))


def db_event(now, text):
    if DB is None:
        return
    try:
        DB.execute("INSERT INTO events (run, sim_t, text) VALUES (?,?,?)",
                   (DB_RUN, now, str(text)))
        DB.commit()
    except Exception as e:
        out("Ghi events LOI: " + repr(e))


def close_db():
    global DB
    if DB is not None:
        try:
            DB.close()
        except Exception:
            pass
        DB = None


# =====================================================================
# PHAN 4D: MQTT KHONG CHAN (client toi gian, tu viet, khong dung paho)
# Nguyen tac: moi lenh mang deu o che do non-blocking, select voi timeout 0.
# Broker tat / mat mang -> chi mat du lieu gui di, dieu khien tuoi KHONG bi anh huong.
# Dung IP (khong dung ten may) de khong bi chan boi DNS.
# =====================================================================
MQTT_ENABLE = True
MQTT_HOST = "127.0.0.1"   # broker (vi du Mosquitto) chay tren cung may tinh voi Proteus
MQTT_PORT = 1883
MQTT_BASE = "irrigation"  # cac topic: irrigation/status, irrigation/readings, irrigation/events
MQTT_CLIENT_ID = "smart_irrigation_rpi"
MQTT_RETRY_S = 10.0       # sau khi that bai, doi 10 s mo phong roi thu lai
MQTT_PUB_EVERY = 20      # gui 1 ban tin readings moi 100 tick (5 s mo phong)
MANUAL_FAILSAFE_S = 60.0   # thu cong ma mat MQTT qua so giay mo phong nay thi tu ve che do tu dong

try:
    import socket
    import select
    import errno
    MQTT_AVAILABLE = True
except Exception:
    MQTT_AVAILABLE = False

# ---- MQTT_LITE_BEGIN ----
MQ_OFF, MQ_CONNECTING, MQ_WAIT_ACK, MQ_ONLINE = "OFF", "CONNECTING", "WAIT_CONNACK", "ONLINE"


def _mq_str(s):
    b = s.encode("utf-8")
    return bytes([len(b) >> 8, len(b) & 255]) + b


def _mq_len(n):
    res = bytearray()
    while True:
        d = n % 128
        n //= 128
        if n > 0:
            d |= 128
        res.append(d)
        if n == 0:
            return bytes(res)


class MqttLite:
    """MQTT 3.1.1, QoS 0, chi publish. poll(now) goi moi tick, khong bao gio chan."""

    def __init__(self, host, port, client_id, base, retry_s=10.0, log=None):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.base = base
        self.retry_s = retry_s
        self.timeout_s = 5.0
        self._log = log if log is not None else print
        self.sock = None
        self.state = MQ_OFF
        self.next_try = 0.0
        self.t_state = 0.0
        self.t_check = 0.0
        self.now = 0.0
        self.rbuf = b""
        self.sent = 0
        self.dropped = 0
        self.cmds = []          # (topic, payload) nhan tu broker

    # ---- noi bo ----
    def _close_sock(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def _fail(self, now, reason):
        self._close_sock()
        self.state = MQ_OFF
        self.rbuf = b""
        self.next_try = now + self.retry_s
        self._log("[%.2f] MQTT OFFLINE: %s. Thu lai sau %.0f s" % (now, reason, self.retry_s))

    def _connect_packet(self):
        # co: clean session 0x02 + will 0x04 + will retain 0x20; keepalive = 0 (khong can ping)
        vh = _mq_str("MQTT") + bytes([4, 0x26, 0, 0])
        pl = (_mq_str(self.client_id) + _mq_str(self.base + "/status")
              + _mq_str("offline"))
        body = vh + pl
        return bytes([0x10]) + _mq_len(len(body)) + body

    def _start_connect(self, now):
        self._close_sock()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setblocking(False)
        code = s.connect_ex((self.host, self.port))
        if code in (0, errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EAGAIN, 10035, 10036):
            self.sock = s
            self.state = MQ_CONNECTING
            self.t_state = now
        else:
            try:
                s.close()
            except Exception:
                pass
            self._fail(now, "connect_ex ma " + str(code))

    def _poll(self, now):
        st = self.state
        if st == MQ_OFF:
            if now >= self.next_try:
                self._start_connect(now)
        elif st == MQ_CONNECTING:
            r, w, x = select.select([], [self.sock], [self.sock], 0)
            if x:
                self._fail(now, "ket noi bi tu choi")
            elif w:
                err = self.sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err != 0:
                    self._fail(now, "ket noi bi tu choi, ma " + str(err))
                else:
                    self.sock.send(self._connect_packet())
                    self.state = MQ_WAIT_ACK
                    self.t_state = now
            elif now - self.t_state > self.timeout_s:
                self._fail(now, "het gio cho ket noi")
        elif st == MQ_WAIT_ACK:
            r, w, x = select.select([self.sock], [], [], 0)
            if r:
                data = self.sock.recv(4 - len(self.rbuf))
                if not data:
                    self._fail(now, "broker dong ket noi")
                    return
                self.rbuf += data
                if len(self.rbuf) >= 4:
                    if self.rbuf[0] == 0x20 and self.rbuf[3] == 0:
                        self.rbuf = b""
                        self.state = MQ_ONLINE
                        self.t_check = now
                        self._log("[%.2f] MQTT ONLINE" % now)
                        self.publish("status", "online", True)
                        self._subscribe()
                    else:
                        self._fail(now, "broker tu choi CONNECT")
            elif now - self.t_state > self.timeout_s:
                self._fail(now, "het gio cho CONNACK")
        elif st == MQ_ONLINE:
            if now - self.t_check >= 0.5:
                self.t_check = now
                r, w, x = select.select([self.sock], [], [], 0)
                if r:
                    data = self.sock.recv(1024)
                    if not data:
                        self._fail(now, "broker ngat ket noi")
                    else:
                        self.rbuf += data
                        self._parse()

    def _subscribe(self):
        body = bytes([0, 1]) + _mq_str(self.base + "/cmd") + bytes([0])
        self.sock.send(bytes([0x82]) + _mq_len(len(body)) + body)

    def _parse(self):
        """Tach cac goi PUBLISH (QoS 0) nhan duoc, bo qua SUBACK va goi khac."""
        b = self.rbuf
        while len(b) >= 2:
            i, mult, ln = 1, 1, 0
            done = False
            while i < len(b):
                d = b[i]
                i += 1
                ln += (d & 127) * mult
                if not (d & 128):
                    done = True
                    break
                mult *= 128
            if not done or len(b) - i < ln:
                break
            if (b[0] >> 4) == 3 and ln >= 2:
                tl = (b[i] << 8) | b[i + 1]
                topic = b[i + 2:i + 2 + tl].decode("utf-8", "ignore")
                self.cmds.append((topic, b[i + 2 + tl:i + ln].decode("utf-8", "ignore")))
            b = b[i + ln:]
        self.rbuf = b[-4096:]

    def take_cmds(self):
        c = self.cmds
        self.cmds = []
        return c

    # ---- giao dien ----
    def poll(self, now):
        """Goi moi tick. Khong bao gio nem loi ra ngoai."""
        self.now = now
        w0 = time.time()
        try:
            self._poll(now)
        except Exception as e:
            self._fail(now, "loi " + repr(e))
        dt = time.time() - w0
        if dt > 0.3:
            self._log("[%.2f] MQTT CANH BAO: poll mat %.2f s" % (now, dt))

    def publish(self, sub, payload, retain=False):
        """Gui 1 ban tin. Tra False (va bo qua) neu chua online."""
        if self.state != MQ_ONLINE:
            self.dropped += 1
            return False
        try:
            body = _mq_str(self.base + "/" + sub) + payload.encode("utf-8")
            pkt = bytes([0x30 | (1 if retain else 0)]) + _mq_len(len(body)) + body
            n = self.sock.send(pkt)
            if n != len(pkt):
                self._fail(self.now, "gui thieu du lieu")
                return False
            self.sent += 1
            return True
        except Exception as e:
            self._fail(self.now, "loi gui " + repr(e))
            return False

    def close(self, now):
        """Tat sach se: bao offline roi ngat. Best effort."""
        try:
            if self.state == MQ_ONLINE:
                self.publish("status", "offline", True)
                self.sock.send(bytes([0xE0, 0x00]))
        except Exception:
            pass
        self._close_sock()
        self.state = MQ_OFF
# ---- MQTT_LITE_END ----


def jnum(v):
    return "null" if v is None else ("%.1f" % v)


def reading_json(now, ctrl, soil, soil4, water, light, outputs):
    v = outputs["valves"]
    return ('{"run":%d,"t":%.1f,"state":"%s","zone":%s,'
            '"soil":[%s,%s,%s],"soil4":%s,"water":%s,"light":%s,'
            '"temp":%s,"band":"%s","night":%d,"harsh":%d,"defer":[%d,%d,%d],"thr":[%s,%s],'
            '"pump":%d,"valves":[%d,%d,%d],"mode":"%s"}' % (
                DB_RUN, now, ctrl.state,
                "null" if ctrl.zone is None else str(ctrl.zone),
                jnum(soil[0]), jnum(soil[1]), jnum(soil[2]),
                jnum(soil4), jnum(water), jnum(light),
                jnum(ctrl.temp), ctrl.temp_band, 1 if ctrl.night else 0, 1 if ctrl.harsh else 0,
                1 if ctrl.deferred[0] else 0, 1 if ctrl.deferred[1] else 0, 1 if ctrl.deferred[2] else 0,
                jnum(ctrl.eff_start), jnum(ctrl.eff_stop),
                1 if outputs["pump"] else 0,
                1 if v[0] else 0, 1 if v[1] else 0, 1 if v[2] else 0, ctrl.mode))


def event_json(now, text):
    t = str(text).replace("\\", "/").replace('"', "'")
    return '{"run":%d,"t":%.2f,"text":"%s"}' % (DB_RUN, now, t)


def init_mqtt():
    if not MQTT_ENABLE or not MQTT_AVAILABLE:
        out("MQTT TAT (MQTT_ENABLE=False hoac khong co thu vien socket)")
        return None
    try:
        mq = MqttLite(MQTT_HOST, MQTT_PORT, MQTT_CLIENT_ID, MQTT_BASE, MQTT_RETRY_S, out)
        out("MQTT khoi tao xong (khong chan), dich " + MQTT_HOST + ":" + str(MQTT_PORT))
        return mq
    except Exception as e:
        out("MQTT khoi tao LOI (van chay, khong gui MQTT): " + repr(e))
        return None


def handle_cmd(now, ctrl, payload):
    """Thuc thi 1 lenh JSON tu dashboard. Tra chuoi su kien (hoac None). Khong bao gio nem loi."""
    if json is None:
        return None
    try:
        c = json.loads(payload)
        k = c.get("cmd")
        if k == "mode":
            return ctrl.set_mode(c.get("value"))
        if k == "zone":
            return ctrl.set_zone(int(c.get("z")), bool(c.get("on")))
        if k == "thr":
            return ctrl.set_thresholds(float(c.get("start")), float(c.get("stop")))
        if k == "stop":
            msg = ctrl.emergency_stop(now)
            if ENABLE_OUTPUTS:
                apply_outputs(ctrl._outputs())    # tat relay ngay, khong doi vong sau
            return msg
        return "CMD rejected: lenh la"
    except Exception as e:
        return "CMD rejected: " + repr(e)


def tick():
    peripheral_loop()
    time.sleep(TICK)


def fmt(v):
    return "NA" if v is None else ("%.1f" % v)


def write_pin(pin, on):
    """on = trang thai logic (True = relay hoat dong). Chi ghi khi co thay doi."""
    if _applied.get(pin) is on:
        return
    level_on = cpu.GPIO.HIGH if RELAY_ACTIVE_HIGH else cpu.GPIO.LOW
    level_off = cpu.GPIO.LOW if RELAY_ACTIVE_HIGH else cpu.GPIO.HIGH
    cpu.GPIO.output(pin, level_on if on else level_off)
    _applied[pin] = on


def apply_outputs(outputs):
    write_pin(PUMP_PIN, outputs["pump"])
    for i in range(3):
        write_pin(VALVE_PINS[i], outputs["valves"][i])


def all_off():
    for name, pin in ALL_PINS:
        try:
            write_pin(pin, False)
        except Exception as e:
            out("tat relay LOI " + name + " " + repr(e))


def open_spi():
    try:
        import spidev
        spi = spidev.SpiDev()
        spi.open(0, 0)
        spi.max_speed_hz = 1000000
        spi.mode = 0
        return spi
    except Exception as e:
        out("Mo SPI LOI: " + repr(e))
        return None


def read_raw(spi, ch):
    """Doc 1 kenh MCP3008 bang xfer2. Tra raw 0..1023 hoac None neu loi."""
    if spi is None:
        return None
    try:
        r = spi.xfer2([1, (8 + ch) << 4, 0])
        return ((r[1] & 3) << 8) | r[2]
    except Exception:
        return None


def read_pct(spi, ch):
    """Doc 1 kenh MCP3008, doi sang thang 0..100. Tra None neu loi."""
    return raw_to_pct(read_raw(spi, ch))


# =====================================================================
# PHAN 4E: LCD 16x2 + 8 LED CANH BAO + COI (khong bao gio duoc lam dung dieu khien)
# Moi loi o phan nay chi lam TAT giao dien, bo dieu khien tuoi van chay.
# =====================================================================
ENABLE_UI = True          # False = khong dung LCD/LED/coi
UI_ACTIVE_HIGH = True     # LED va coi: GPIO HIGH -> sang / keu
BUZZER_ENABLE = True      # False = tat coi (LED va LCD van chay)
LCD_BYTES_PER_TICK = 4    # so byte gui LCD moi tick (nho = it chiem thoi gian, chu cham hon)
LCD_PAGE_S = 2.0          # doi trang LCD moi 2 s mo phong
WIFI_GRACE_S = 15.0       # sau khi khoi dong, cho 15 s moi keu coi bao mat ket noi

LCD_RS = pio.GPIO5
LCD_E = pio.GPIO6
LCD_DATA = [pio.GPIO12, pio.GPIO13, pio.GPIO16, pio.GPIO19]     # D4, D5, D6, D7
LED_PINS = [(pio.GPIO20, pio.GPIO21),     # bom / he thong: (do, xanh)
            (pio.GPIO26, pio.GPIO24),     # vung 1
            (pio.GPIO25, pio.GPIO4),      # vung 2
            (pio.GPIO18, pio.GPIO7)]      # vung 3
BUZZER_PIN = pio.GPIO2
UI_PINS = [LCD_RS, LCD_E] + LCD_DATA + [p for pair in LED_PINS for p in pair] + [BUZZER_PIN]

# ---- UI_BEGIN ----
# Bao dong: ten -> (uu tien, nho = quan trong hon, chu ky s, [(bat dau, ket thuc) trong chu ky], keu toi da s)
ALARMS = {
    "water": (0, 1.0, [(0.0, 0.2)], 30.0),                    # het nuoc: bip bip lien tuc toi da 30 s
    "sensor": (1, 3.0, [(0.0, 0.1), (0.25, 0.35)], 15.0),     # cam bien loi: 2 bip ngan moi 3 s
    "tsensor": (1.5, 3.0, [(0.0, 0.1), (0.25, 0.35), (0.5, 0.6)], 15.0),  # LM35 loi: 3 bip ngan moi 3 s
    "hot": (1.8, 4.0, [(0.0, 0.1), (0.2, 0.3), (0.4, 0.5)], 12.0),        # qua nong: 3 bip nhanh moi 4 s
    "cold": (1.9, 4.0, [(0.0, 0.5)], 8.0),                    # qua lanh: 1 bip dai moi 4 s
    "wifi": (2, 2.0, [(0.0, 0.1)], 6.0),                      # mat ket noi: bip trong 6 s
    "dry": (3, 1.0, [(0.0, 0.1)], 1.0),                       # co vung moi can tuoi: 1 bip
}


def line16(s):
    s = "".join(ch if 32 <= ord(ch) < 127 else "?" for ch in str(s))
    return (s + " " * 16)[:16]


class PinOut:
    """Ghi chan GPIO, chi ghi khi gia tri doi (do GPIO trong Proteus ton thoi gian)."""

    def __init__(self, gpio, active_high=True):
        self.g = gpio
        self.active_high = active_high
        self.cache = {}

    def set(self, pin, on):
        on = bool(on)
        if self.cache.get(pin) is on:
            return
        hi = on if self.active_high else (not on)
        self.g.output(pin, self.g.HIGH if hi else self.g.LOW)
        self.cache[pin] = on


class Lcd16x2:
    """HD44780 16x2, che do 4 bit, RW noi GND. Khong chan: chi gui vai byte moi tick."""

    def __init__(self, gpio, rs, e, data, sleep=time.sleep):
        self.g = gpio
        self.rs = rs
        self.e = e
        self.d = list(data)
        self.sleep = sleep
        self.pins = PinOut(gpio, True)
        self.queue = []
        self.shadow = [" " * 16, " " * 16]

    def _nib(self, v, rs):
        p = self.pins
        p.set(self.rs, rs)
        for i in range(4):
            p.set(self.d[i], (v >> i) & 1)
        self.g.output(self.e, self.g.HIGH)
        self.g.output(self.e, self.g.LOW)

    def _byte(self, v, rs):
        self._nib(v >> 4, rs)
        self._nib(v & 15, rs)

    def init(self):
        s = self.sleep
        self.g.output(self.e, self.g.LOW)
        s(0.05)
        for w in (0.005, 0.002, 0.002):
            self._nib(3, 0)
            s(w)
        self._nib(2, 0)             # chuyen sang 4 bit
        s(0.002)
        for c in (0x28, 0x08, 0x01):   # 2 dong, tat hien thi, xoa man hinh
            self._byte(c, 0)
            s(0.003)
        self._byte(0x06, 0)         # con tro tu tang
        s(0.001)
        self._byte(0x0C, 0)         # bat hien thi, an con tro
        s(0.001)
        self.queue = []
        self.shadow = [" " * 16, " " * 16]

    def set_text(self, l1, l2):
        """Xep hang chi cac ky tu thay doi (khong gui lai ca man hinh)."""
        new = [line16(l1), line16(l2)]
        for r in (0, 1):
            old, cur = self.shadow[r], new[r]
            c = 0
            while c < 16:
                if cur[c] == old[c]:
                    c += 1
                    continue
                start = c
                while c < 16 and cur[c] != old[c]:
                    c += 1
                self.queue.append((0, 0x80 | (0x40 * r + start)))
                for k in range(start, c):
                    self.queue.append((1, ord(cur[k])))
            self.shadow[r] = cur

    def service(self, max_bytes):
        n = 0
        while self.queue and n < max_bytes:
            rs, v = self.queue.pop(0)
            self._byte(v, rs)
            n += 1
        return n

    def flush(self):
        return self.service(10 ** 6)


def _num(v):
    return "   NA" if v is None else ("%5.1f" % v)


def zone_label(ctrl, soil, z):
    if soil[z] is None:
        return "LOI CB"
    st = ctrl.zst[z]
    if st == "RUNNING":
        return "TUOI"
    if st == "OPENING":
        return "MO VAN"
    if st == "CLOSING":
        return "DONG VAN"
    return "CHO" if ctrl.need[z] else "OK"


def wifi_label(mq_state):
    if mq_state == "ONLINE":
        return "BAT"
    if mq_state in ("CONNECTING", "WAIT_CONNACK"):
        return "NOI.."
    return "TAT"


def temp_note(ctrl):
    """Dong 2 trang nhiet do: loi / canh bao / hoan tuoi / nguong dang dung."""
    if ctrl.temp_fault:
        return "LOI CB NHIET"
    if ctrl.temp_hot:
        return "QUA NONG"
    if ctrl.temp_cold:
        return "QUA LANH"
    if any(ctrl.deferred):
        return "NANG GAT:HOAN"
    return "NGUONG %d/%d" % (round(ctrl.eff_start), round(ctrl.eff_stop))


def build_pages(ctrl, soil, soil4, water, light, outputs, mq_state):
    """5 trang, moi trang 2 dong 16 ky tu."""
    def zl(z):
        return "V%d:%-8s%s" % (z + 1, zone_label(ctrl, soil, z), _num(soil[z]))
    v = outputs["valves"]
    pump = "BAT" if outputs["pump"] else "TAT"
    if water is None:
        wl = "LOI"
    else:
        wl = "THAP" if ctrl.water_low else "OK"
    pages = [
        (zl(0), zl(1)),
        (zl(2), "BOM:%-4s V:%d%d%d" % (pump, int(v[0]), int(v[1]), int(v[2]))),
        ("NUOC:%-5s%s" % (wl, _num(water)), "WIFI:%s" % wifi_label(mq_state)),
        ("SANG:%s %-5s" % (_num(light), "DEM" if ctrl.night else "NGAY"), "DAT4:%s" % _num(soil4)),
        ("NHIET:%sC" % _num(ctrl.temp), temp_note(ctrl)),
    ]
    return [(line16(a), line16(b)) for a, b in pages]


def led_states(now, ctrl, soil, water, online):
    """4 cap LED (do, xanh): bom/he thong, vung 1, vung 2, vung 3."""
    blink = int(now * 2) % 2 == 0      # nhap nhay 1 Hz
    cfg = ctrl.cfg
    leds = []
    if ctrl.water_low:
        leds.append((True, False))             # het nuoc: do dung yen
    elif not online:
        leds.append((blink, False))            # mat ket noi: do nhap nhay
    elif water is not None and water >= cfg["water_ok_at"]:
        leds.append((False, True))             # nuoc du va co ket noi: xanh
    else:
        leds.append((False, False))
    for z in range(3):
        v = soil[z]
        if v is None:
            leds.append((blink, False))        # cam bien loi: do nhap nhay
        elif v < ctrl.eff_start:
            leds.append((True, False))         # do am < nguong bat dau (40, doi theo nhiet do): do
        elif v >= ctrl.eff_stop:
            leds.append((False, True))         # do am >= nguong dung (60, doi theo nhiet do): xanh
        else:
            leds.append((False, False))        # 40-60: tat ca hai (ke ca khi dang tuoi tiep den 60)
    if ctrl.night:                              # ban dem: tat den xanh, chi con den do canh bao
        leds = [(r, False) for r, g in leds]
    return leds


def active_alarms(now, ctrl, soil, online, wifi_grace):
    keys = set()
    if ctrl.water_low:
        keys.add(("water", 0))
    if any(v is None for v in soil):
        keys.add(("sensor", 0))
    if ctrl.temp_fault:
        keys.add(("tsensor", 0))
    if ctrl.temp_hot:
        keys.add(("hot", 0))
    if ctrl.temp_cold:
        keys.add(("cold", 0))
    if not ctrl.night:                          # ban dem: im bip mat ket noi va bip vung can tuoi
        if (not online) and now >= wifi_grace:
            keys.add(("wifi", 0))
        for z in range(3):
            if ctrl.need[z]:
                keys.add(("dry", z))
    return keys


class Buzzer:
    def __init__(self, pins, pin, enable=True):
        self.pins = pins
        self.pin = pin
        self.enable = enable
        self.t0 = {}

    def update(self, now, keys):
        for k in list(self.t0):
            if k not in keys:
                del self.t0[k]
        for k in keys:
            if k not in self.t0:
                self.t0[k] = now
        best = None
        for k, t in self.t0.items():
            pri, period, wins, mx = ALARMS[k[0]]
            if now - t >= mx:
                continue
            if best is None or pri < best[0]:
                best = (pri, period, wins, now - t)
        on = False
        if best is not None and self.enable:
            ph = best[3] % best[1]
            on = any(a <= ph < b for a, b in best[2])
        self.pins.set(self.pin, on)
        return on


class Ui:
    def __init__(self, gpio, rs, e, data, led_pins, buzzer_pin, active_high=True,
                 lcd_bytes=4, page_s=2.0, buzzer_enable=True, wifi_grace=15.0,
                 sleep=time.sleep):
        self.pins = PinOut(gpio, active_high)
        self.lcd = Lcd16x2(gpio, rs, e, data, sleep)
        self.led_pins = led_pins
        self.buzzer = Buzzer(self.pins, buzzer_pin, buzzer_enable)
        self.buzzer_pin = buzzer_pin
        self.lcd_bytes = lcd_bytes
        self.page_s = page_s
        self.wifi_grace = wifi_grace

    def init(self):
        self._all_off()
        self.lcd.init()
        self.lcd.set_text("TUOI TU DONG", "Dang khoi dong..")
        self.lcd.flush()

    def _all_off(self):
        for r, g in self.led_pins:
            self.pins.set(r, False)
            self.pins.set(g, False)
        self.pins.set(self.buzzer_pin, False)

    def update(self, now, ctrl, soil, soil4, water, light, outputs, mq_state):
        online = (mq_state == "ONLINE")
        for (r, g), (pr, pg) in zip(led_states(now, ctrl, soil, water, online), self.led_pins):
            self.pins.set(pr, r)
            self.pins.set(pg, g)
        self.buzzer.update(now, active_alarms(now, ctrl, soil, online, self.wifi_grace))
        pages = build_pages(ctrl, soil, soil4, water, light, outputs, mq_state)
        l1, l2 = pages[int(now / self.page_s) % len(pages)]
        self.lcd.set_text(l1, l2)
        self.lcd.service(self.lcd_bytes)

    def shutdown(self):
        self._all_off()
        self.lcd.set_text("HE THONG DUNG", "Relay da tat")
        self.lcd.flush()
# ---- UI_END ----


def init_ui():
    if not ENABLE_UI:
        out("UI TAT (ENABLE_UI=False)")
        return None
    try:
        for p in UI_PINS:
            cpu.GPIO.setup(p, cpu.GPIO.OUT)
        ui = Ui(cpu.GPIO, LCD_RS, LCD_E, LCD_DATA, LED_PINS, BUZZER_PIN,
                UI_ACTIVE_HIGH, LCD_BYTES_PER_TICK, LCD_PAGE_S, BUZZER_ENABLE, WIFI_GRACE_S)
        ui.init()
        out("UI san sang: LCD 16x2, 8 LED, coi")
        return ui
    except Exception as e:
        out("UI khoi tao LOI (van chay, khong co LCD/LED/coi): " + repr(e))
        return None


def run(max_ticks=None):
    """Vong dieu khien chinh. max_ticks chi dung de kiem thu ngoai Proteus."""
    ctrl = IrrigationController({"temp_enabled": TEMP_ENABLE})
    tfilt = TempFilter(TEMP_MEDIAN_N)
    temp = None
    spi = open_spi()
    mq = init_mqtt()
    ui = init_ui()
    soil = [None, None, None]
    water = None
    light = None
    soil4 = None
    last_dry = None
    off_since = None   # thoi diem mat MQTT (giay mo phong), None neu dang online
    n = 0
    try:
        while max_ticks is None or n < max_ticks:
            now = n * TICK
            if n % SENSE_EVERY == 0:
                soil = [read_pct(spi, c) for c in CH_SOIL]
                soil4 = read_pct(spi, CH_SOIL4)
                light = read_pct(spi, CH_LIGHT)
                water = read_pct(spi, CH_WATER)
                if TEMP_ENABLE:
                    temp = tfilt.push(raw_to_temp(read_raw(spi, CH_TEMP), TEMP_VREF))

            outputs, events = ctrl.update(now, soil, water, temp, light)
            for e in events:
                out("[%.2f] %s" % (now, e))
                db_event(now, e)
                if mq is not None:
                    mq.publish("events", event_json(now, e))

            if ENABLE_OUTPUTS:
                apply_outputs(outputs)
            else:
                snap = (outputs["pump"], tuple(outputs["valves"]))
                if snap != last_dry:
                    out("[%.2f] DRY (khong xuat): pump=%s valves=%s" % (
                        now, outputs["pump"], outputs["valves"]))
                    last_dry = snap

            if n % DB_EVERY == 0:
                db_reading(now, ctrl, soil, soil4, water, light, outputs)

            if mq is not None:
                mq.poll(now)
                # failsafe: che do thu cong + mat MQTT qua MANUAL_FAILSAFE_S -> ve tu dong
                if mq.state == "ONLINE":
                    off_since = None
                else:
                    if off_since is None:
                        off_since = now
                    if ctrl.mode == "manual" and (now - off_since) >= MANUAL_FAILSAFE_S:
                        _fs = "FAILSAFE mat MQTT %.0f s, thu cong -> " % (now - off_since) + ctrl.set_mode("auto")
                        out("[%.2f] %s" % (now, _fs))
                        db_event(now, _fs)
                        mq.publish("events", event_json(now, _fs))
                for _topic, _payload in mq.take_cmds():
                    _msg = handle_cmd(now, ctrl, _payload)
                    if _msg:
                        out("[%.2f] %s" % (now, _msg))
                        db_event(now, _msg)
                        mq.publish("events", event_json(now, _msg))
                if n % MQTT_PUB_EVERY == 0:
                    mq.publish("readings", reading_json(
                        now, ctrl, soil, soil4, water, light, outputs), True)

            if ui is not None:
                try:
                    ui.update(now, ctrl, soil, soil4, water, light, outputs,
                              "OFF" if mq is None else mq.state)
                except Exception as e:
                    out("UI LOI, tat giao dien (tuoi van chay): " + repr(e))
                    ui = None

            if n % STATUS_EVERY == 0:
                out("[%.1f] state=%s zone=%s soil=%s ch3=%s water=%s light=%s temp=%s band=%s night=%d harsh=%d mqtt=%s" % (
                    now, ctrl.state, ctrl.zone,
                    [fmt(v) for v in soil], fmt(soil4), fmt(water), fmt(light),
                    fmt(temp), ctrl.temp_band, 1 if ctrl.night else 0, 1 if ctrl.harsh else 0,
                    "TAT" if mq is None else mq.state))
            tick()
            n += 1
    finally:
        ctrl.force_all_off(n * TICK)
        all_off()
        if ui is not None:
            try:
                ui.shutdown()
            except Exception:
                pass
        out("Tat ca relay ve trang thai tat")
        if mq is not None:
            try:
                mq.close(n * TICK)
            except Exception:
                pass
        close_db()
        if spi is not None:
            try:
                spi.close()
            except Exception:
                pass


def main():
    print("STEP 0: truoc peripheral_setup")
    peripheral_setup()
    print("STEP 1: peripheral_setup xong")
    init_log()
    init_db()
    out("=== 4D BAT DAU === ENABLE_OUTPUTS=%s RELAY_ACTIVE_HIGH=%s MQTT_ENABLE=%s" % (
        ENABLE_OUTPUTS, RELAY_ACTIVE_HIGH, MQTT_ENABLE))
    try:
        cpu.GPIO.setwarnings(False)
        cpu.GPIO.setmode(cpu.GPIO.BCM)
        for name, pin in ALL_PINS:
            cpu.GPIO.setup(pin, cpu.GPIO.OUT)
        all_off()
        out("GPIO san sang, tat ca relay o trang thai tat")
        run()
    except BaseException as e:
        out("LOI KHONG DOI TRUOC: " + repr(e))
        out(traceback.format_exc())
    out("=== 4D KET THUC (giu mo phong song, relay tat) ===")
    while True:
        tick()


if __name__ == "__main__":
    main()