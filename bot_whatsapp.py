"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V84: The Shielded Architecture (V83 + Prevención Amnesia, Smart CSV, TimeCompat, Clean Format)
"""

import os, re, json, time, csv, io, random, logging, threading, queue
from flask import Flask, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
# 1. ZONA HORARIA Y CONFIG (FIX: SMART CSV SELECTOR)
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))

def ahora_lima():
    return datetime.now(TZ_LIMA)

def ahora_lima_str():
    return ahora_lima().strftime("%Y-%m-%d %H:%M:%S")

def get_csv_bd_path():
    if os.path.exists("base_datos.csv"):
        return "base_datos.csv"
    archivos = [f for f in os.listdir(".") if f.startswith("participantes_") and f.endswith(".csv")]
    if archivos:
        # Toma siempre el archivo modificado más recientemente
        archivos.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        return archivos[0]
    return "base_datos.csv"

class Config:
    TOKEN               = os.environ.get("WA_TOKEN", "")
    PHONE_ID            = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN        = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    EXCEL_PATH          = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")
    CSV_BD_PATH         = os.environ.get("CSV_BD_PATH", get_csv_bd_path())
    SESSIONS_PATH       = "sesiones.json"
    SESSIONS_SIM_PATH   = "sesiones_sim.json"   
    HISTORIAL_PATH      = "historial_chat.json"
    BACKUP_CSV          = "backup_absoluto_mensajes.csv"
    SHEET_ID            = os.environ.get("SHEET_ID", "")
    CREDS_JSON          = os.environ.get("GOOGLE_CREDENTIALS", "")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# 2. CACHÉ CSV EN MEMORIA
# ══════════════════════════════════════════════════════════════
_csv_rows        = None
_csv_mtime       = 0.0
_csv_lock        = threading.Lock()

def _detectar_delimitador(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            primera = f.readline()
        return ";" if primera.count(";") > primera.count(",") else ","
    except Exception:
        return ","

def get_csv_rows():
    global _csv_rows, _csv_mtime
    path = Config.CSV_BD_PATH
    if not os.path.exists(path):
        return []
    try:
        mtime = os.path.getmtime(path)
        with _csv_lock:
            if _csv_rows is not None and mtime == _csv_mtime:
                return _csv_rows
            delim = _detectar_delimitador(path)
            with open(path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f, delimiter=delim))
            _csv_rows  = rows
            _csv_mtime = mtime
            logger.info(f"CSV recargado: {len(rows)} filas, delim='{delim}'")
            return rows
    except Exception as e:
        logger.error(f"CSV cache error: {e}")
        return []

# ══════════════════════════════════════════════════════════════
# 3. SESSION MANAGER (FIX: PREVENCIÓN DE AMNESIA)
# ══════════════════════════════════════════════════════════════
class SessionManager:
    @staticmethod
    def _path(telefono):
        return Config.SESSIONS_SIM_PATH if str(telefono).startswith("SIM_") else Config.SESSIONS_PATH

    @classmethod
    def _load(cls, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception: pass
        return {}

    @classmethod
    def _save(cls, path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def get_sesion(cls, telefono):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                return cls._load(path).get(str(telefono), {})
        except FileLockTimeout:
            logger.warning(f"Lock timeout get_sesion {telefono}. Retornando None para proteger datos.")
            return None # FIX: Evita sobreescribir la memoria si el servidor está saturado
        except Exception as e:
            logger.error(f"get_sesion error: {e}")
            return None

    @classmethod
    def set_sesion(cls, telefono, data_dict):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data[str(telefono)] = data_dict
                cls._save(path, data)
        except FileLockTimeout:
            logger.warning(f"Lock timeout set_sesion {telefono}")
        except Exception as e:
            logger.error(f"set_sesion error: {e}")

    @classmethod
    def borrar_sesion(cls, telefono):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data.pop(str(telefono), None)
                cls._save(path, data)
        except FileLockTimeout: pass
        except Exception: pass

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        path = Config.HISTORIAL_PATH
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                h = []
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f: h = json.load(f)
                    except Exception: h = []
                h.append({
                    "telefono": str(telefono),
                    "nombre":   nombre or "Desconocido",
                    "texto":    texto,
                    "tipo":     tipo,
                    "hora":     ahora_lima().strftime("%d/%m %H:%M"),
                })
                if len(h) > 10000: h = h[-10000:]
                with open(path, "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, indent=2)
        except Exception: pass

    @staticmethod
    def guardar_backup_absoluto(telefono, nombre, mensaje, direccion, estado_sistema):
        path = Config.BACKUP_CSV
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                nuevo = not os.path.exists(path)
                with open(path, "a", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    if nuevo: w.writerow(["Fecha y Hora","Telefono","Nombre","Direccion (In/Out)","Mensaje","Estado Sistema"])
                    w.writerow([ahora_lima().strftime("%Y-%m-%d %H:%M:%S"), telefono, nombre, direccion, mensaje, estado_sistema])
        except Exception: pass

def get_sesion(tel):              return SessionManager.get_sesion(tel)
def set_sesion(tel, d):           SessionManager.set_sesion(tel, d)
def borrar_sesion(tel):           SessionManager.borrar_sesion(tel)
def append_historial(t, n, x, p): SessionManager.append_historial(t, n, x, p)

def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return []

# ══════════════════════════════════════════════════════════════
# 4. GOOGLE SHEETS (COLA NON-DAEMON)
# ══════════════════════════════════════════════════════════════
_sheets_token     = None
_sheets_token_exp = 0
_sheets_tok_lock  = threading.Lock()

def _get_sheets_token():
    global _sheets_token, _sheets_token_exp
    with _sheets_tok_lock:
        if _sheets_token and time.time() < _sheets_token_exp - 60: return _sheets_token
        if not Config.CREDS_JSON: return None
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now   = int(time.time())
            creds = json.loads(Config.CREDS_JSON)
            pk_pem = creds["private_key"].replace("\\n", "\n")
            hdr = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            pld = base64.urlsafe_b64encode(json.dumps({
                "iss":   creds["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
                "aud":   "https://oauth2.googleapis.com/token", "iat":   now, "exp": now + 3600,
            }).encode()).rstrip(b"=")
            msg = hdr + b"." + pld
            pk  = serialization.load_pem_private_key(pk_pem.encode(), password=None)
            sig = pk.sign(msg, cp.PKCS1v15(), hashes.SHA256())
            jwt = (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion":   jwt}, timeout=10)
            if r.status_code == 200:
                d = r.json()
                _sheets_token     = d["access_token"]
                _sheets_token_exp = now + d.get("expires_in", 3600)
                return _sheets_token
        except Exception: pass
        return None

_cola_sheets = queue.Queue()

def _worker_sheets():
    while True:
        try:
            t = _cola_sheets.get()
            if not Config.SHEET_ID:
                _cola_sheets.task_done()
                continue
            tok = _get_sheets_token()
            if tok:
                url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H:append"
                req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                    json={"values": [[ahora_lima().strftime("%d/%m/%Y %H:%M"), str(t["tel"]), t["nom"], t["msg"], t["resp"], t["est"], t.get("resp_man",""), t.get("env_stat","")]]},
                    headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}, timeout=10)
            time.sleep(1.0)
        except Exception: pass
        finally: _cola_sheets.task_done()

threading.Thread(target=_worker_sheets, daemon=False, name="worker-sheets").start()

def registrar_en_sheets(tel, nom, msg, resp, est="", resp_man="", env_stat=""):
    if str(tel).startswith("SIM_"): return
    _cola_sheets.put({"tel": tel, "nom": nom, "msg": msg, "resp": resp, "est": est, "resp_man": resp_man, "env_stat": env_stat})

# ══════════════════════════════════════════════════════════════
# 5. WHATSAPP API
# ══════════════════════════════════════════════════════════════
def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=True, estado_menu="INTERACTIVO"):
    if str(telefono).startswith("SIM_"):
        append_historial(telefono, nombre_imo, texto, "out")
        registrar_en_sheets(telefono, nombre_imo, "", texto[:500], estado_menu or "SIMULADOR")
        SessionManager.guardar_backup_absoluto(telefono, nombre_imo, texto, "OUT", estado_menu or "SIMULADOR")
        return True

    url     = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type":  "application/json"}
    payload = {"messaging_product": "whatsapp", "to":   str(telefono), "type": "text", "text": {"body": texto, "preview_url": False}}
    try:
        r = req_lib.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            append_historial(telefono, nombre_imo, texto, "out")
            SessionManager.guardar_backup_absoluto(telefono, nombre_imo, texto, "OUT", estado_menu or "INTERACTIVO")
            if registrar_sheets: registrar_en_sheets(telefono, nombre_imo, "", texto[:500], estado_menu or "INTERACTIVO")
            return True
    except Exception: pass
    return False

# ══════════════════════════════════════════════════════════════
# 6. UTILIDADES Y CRM
# ══════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0")  and len(t) == 10: return t[1:]
    if len(t) > 10 and not t.startswith("9"): return t[-9:]
    return t

def son_mismo_numero(t1, t2):
    a, b = norm_tel(t1), norm_tel(t2)
    if not a or not b: return False
    if a == b: return True
    return min(len(a), len(b)) >= 8 and (a.endswith(b) or b.endswith(a))

def nombre_pila(s):
    partes = [p for p in re.split(r'\s+', s.strip()) if len(p) > 2]
    return partes[0].title() if partes else s.strip().title()

_perfil_cache      = {}
_perfil_cache_lock = threading.Lock()

def cargar_px_del_imo(telefono):
    if not os.path.exists(Config.EXCEL_PATH): return "", []
    try:
        with FileLock(Config.EXCEL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            wb      = load_workbook(Config.EXCEL_PATH, data_only=True, read_only=True)
            ws      = wb["DATA"]
            px_list, imo_nombre = [], ""
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 7: continue
                if son_mismo_numero(str(row[3] or ""), telefono):
                    if not imo_nombre: imo_nombre = str(row[0] or "").strip()
                    est = str(row[6] or "").strip().upper()
                    px  = str(row[4] or "").strip()
                    if est in ("PENDIENTE", "ENVIADO", "") and px: px_list.append(px)
            wb.close()
            return imo_nombre, px_list
    except Exception: return "", []

def obtener_perfil_crm(telefono):
    tel_norm = norm_tel(telefono)
    with _perfil_cache_lock:
        if tel_norm in _perfil_cache: return _perfil_cache[tel_norm]

    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    imo_nom, px_list = cargar_px_del_imo(telefono)
    if imo_nom and px_list:
        perfil["rol"]    = "IMO"
        perfil["nombre"] = imo_nom

    rows = get_csv_rows()
    if rows:
        keys        = {k.strip().lower(): k for k in rows[0].keys() if k}
        tel_key     = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None)
        nom_key     = next((k for k in keys.values() if "nombre" in k.lower()), None)
        ape_key     = next((k for k in keys.values() if "apellido" in k.lower()), None)
        c1_key      = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
        c2_key      = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
        mj_key      = next((k for k in keys.values() if "maestr" in k.lower()), None)
        imo_nom_key = next((k for k in keys.values() if "imo" in k.lower() and "tel" not in k.lower()), None)
        imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)

        for row in rows:
            if imo_tel_key and son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
                perfil["rol"] = "IMO"
                if not perfil["nombre"] and imo_nom_key: perfil["nombre"] = nombre_pila(str(row.get(imo_nom_key, "")))

            if tel_key and son_mismo_numero(str(row.get(tel_key, "")), telefono):
                n = str(row.get(nom_key, "")).strip()
                a = str(row.get(ape_key, "")).strip() if ape_key else ""
                nx = (n.split()[0] + " " + a.split()[0]).title().strip() if (n and a) else nombre_pila(n)
                perfil["px_nombre"] = nx

                c1  = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                c2  = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
                mj  = str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                s1  = c1 in ("SI", "S")
                s2  = c2 in ("SI", "S")
                sm  = mj in ("SI", "S")

                if sm:
                    perfil["px_pendiente"] = "Ninguno (Maestría iniciada)"
                    perfil["rol_base"]     = "MJ"
                elif s1 and s2:
                    perfil["px_pendiente"] = "Maestría (MJ)"
                    perfil["rol_base"]     = "PX_UPSELL_MJ"
                elif s1:
                    perfil["px_pendiente"] = "Capítulo 2 (C2)"
                    perfil["rol_base"]     = "PX_UPSELL_C2"
                else:
                    perfil["px_pendiente"] = "Capítulo 1 (C1)"
                    perfil["rol_base"]     = "PX_REZAGADO_C1"

                perfil["imo_nombre"] = nombre_pila(str(row.get(imo_nom_key, "Tu líder"))) if imo_nom_key else "Tu líder"
                perfil["imo_tel"]    = str(row.get(imo_tel_key, "")) if imo_tel_key else ""

    if perfil["rol"] != "IMO" and perfil.get("px_nombre"):
        perfil["nombre"]   = perfil["px_nombre"]
        perfil["pendiente"] = perfil.get("px_pendiente")
        perfil["rol"]       = perfil.get("rol_base", "PX_REZAGADO_C1")

    with _perfil_cache_lock: _perfil_cache[tel_norm] = perfil
    return perfil

def buscar_pendientes_imo_csv(telefono):
    rows = get_csv_rows()
    if not rows: return []
    keys        = {k.strip().lower(): k for k in rows[0].keys() if k}
    imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)
    nom_key     = next((k for k in keys.values() if "nombre" in k.lower()), None)
    c1_key      = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
    c2_key      = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
    if not imo_tel_key: return []

    resultado = []
    for row in rows:
        if not son_mismo_numero(str(row.get(imo_tel_key, "")), telefono): continue
        c1 = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
        c2 = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
        falta_c1 = c1 not in ("SI", "S")
        falta_c2 = not falta_c1 and c2 not in ("SI", "S")
        if falta_c1 or falta_c2:
            n = nombre_pila(str(row.get(nom_key, "")))
            resultado.append(f"• {n} (Falta {'C1' if falta_c1 else 'C2'})")
    return resultado

def reporte_sentados_imo(telefono):
    rows = get_csv_rows()
    if not rows: return [], []
    keys        = {k.strip().lower(): k for k in rows[0].keys() if k}
    imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)
    nom_key     = next((k for k in keys.values() if "nombre" in k.lower()), None)
    c1_key      = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
    c2_key      = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
    mj_key      = next((k for k in keys.values() if "maestr" in k.lower()), None)
    if not imo_tel_key: return [], []

    sentados, rezagados = [], []
    for row in rows:
        if not son_mismo_numero(str(row.get(imo_tel_key, "")), telefono): continue
        n   = nombre_pila(str(row.get(nom_key, "")))
        c1  = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
        c2  = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
        mj  = str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
        if mj in ("SI","S"):       st = "MJ Iniciado/Graduado"
        elif c2 in ("SI","S"):     st = "En Proceso C2"
        elif c1 in ("SI","S"):     st = "Inició C1"
        else:                      st = None
        if st: sentados.append(f"• {n} — {st}")
        else: rezagados.append(f"• {n} — Rezagado (Falta C1)")
    return sentados, rezagados

def marcar_stop(telefono):
    if str(telefono).startswith("SIM_") or not os.path.exists(Config.EXCEL_PATH): return
    hoy = ahora_lima().strftime("%d/%m/%Y %H:%M")
    try:
        with FileLock(Config.EXCEL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            wb = load_workbook(Config.EXCEL_PATH)
            for row in wb["DATA"].iter_rows(min_row=2):
                if row and len(row) >= 7 and son_mismo_numero(str(row[3].value or ""), telefono):
                    row[6].value = "STOP"; row[7].value = hoy
            wb.save(Config.EXCEL_PATH); wb.close()
    except Exception: pass

# ══════════════════════════════════════════════════════════════
# 7. RELOJ DINÁMICO LIMA 2026
# ══════════════════════════════════════════════════════════════
def get_fecha_activa(tipo_evento):
    ahora = ahora_lima()
    eventos_c1 = [
        {"co": datetime(2026,5,1,11,30,tzinfo=TZ_LIMA),  "txt": "Viernes 01 de Mayo a las 9:00 AM (Equipo 27)"},
        {"co": datetime(2026,6,5,11,30,tzinfo=TZ_LIMA),  "txt": "Viernes 05 de Junio a las 9:00 AM (Equipo 28)"},
        {"co": datetime(2026,7,10,11,30,tzinfo=TZ_LIMA), "txt": "Viernes 10 de Julio a las 9:00 AM (Equipo 29)"},
        {"co": datetime(2026,8,14,11,30,tzinfo=TZ_LIMA), "txt": "Viernes 14 de Agosto a las 9:00 AM (Equipo 30)"},
    ]
    eventos_c2 = [
        {"co": datetime(2026,4,9,15,30,tzinfo=TZ_LIMA),  "txt": "Jueves 09 de Abril a las 1:00 PM (Equipo 26)"},
        {"co": datetime(2026,5,14,15,30,tzinfo=TZ_LIMA), "txt": "Jueves 14 de Mayo a las 1:00 PM (Equipo 27)"},
        {"co": datetime(2026,6,18,15,30,tzinfo=TZ_LIMA), "txt": "Jueves 18 de Junio a las 1:00 PM (Equipo 28)"},
        {"co": datetime(2026,7,23,15,30,tzinfo=TZ_LIMA), "txt": "Jueves 23 de Julio a las 1:00 PM (Equipo 29)"},
    ]
    eventos_mj = [
        {"co": datetime(2026,4,17,19,0,tzinfo=TZ_LIMA),  "txt": "Viernes 17 de Abril a las 5:00 PM (Inicia Equipo 26)"},
        {"co": datetime(2026,5,22,19,0,tzinfo=TZ_LIMA),  "txt": "Viernes 22 de Mayo a las 5:00 PM (Inicia Equipo 27)"},
        {"co": datetime(2026,6,26,19,0,tzinfo=TZ_LIMA),  "txt": "Viernes 26 de Junio a las 5:00 PM (Inicia Equipo 28)"},
        {"co": datetime(2026,7,31,19,0,tzinfo=TZ_LIMA),  "txt": "Viernes 31 de Julio a las 5:00 PM (Inicia Equipo 29)"},
    ]
    eventos = eventos_c1 if tipo_evento == "C1" else eventos_c2 if tipo_evento == "C2" else eventos_mj
    for ev in eventos:
        if ahora <= ev["co"]: return ev["txt"]
    return "Nuevas fechas por confirmar. Escríbenos para más información."

# ══════════════════════════════════════════════════════════════
# 8. SMART ROUTING
# ══════════════════════════════════════════════════════════════
def notificar_coordinadora_interna(prospecto_tel, prospecto_nombre, motivo, contexto="GENERAL"):
    ahora = ahora_lima()
    targets = {"Diana": "51912379744", "Joyce": "51933599903", "Zuley": "51933599864"}
    is_mj = any(x in contexto for x in ("MAESTRÍA","MJ","RETOMAR","SOPORTE MJ"))
    
    if is_mj:
        targets = {"Linid": "51912379686"}
        if ahora >= datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385"
    else:
        if ahora < datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385"

    coord_n, coord_t = random.choice(list(targets.items()))
    msg = f"🚨 *NUEVO TICKET CORPORATIVO* 🚀\n*Nombre:* {prospecto_nombre or 'No especificado'}\n*Teléfono:* wa.me/{prospecto_tel}\n*Contexto:* {contexto}\n*Requerimiento:* {motivo}"
    enviar_mensaje(coord_t, msg, f"COORDINACIÓN: {coord_n}", True, "ALERTA TICKET")
    return coord_n

# ══════════════════════════════════════════════════════════════
# 9. MENÚS
# ══════════════════════════════════════════════════════════════
MENU_STRUCTURE = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial. Responde con el número de tu elección:\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Inversión y Métodos de Pago\n3️⃣ Soy Participante / Líder (Cambié de número)\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1":"info_entrenamientos","2":"pagos","3":"pre_action_humano_actualizar_numero","4":"pre_action_humano_coordinacion","0":"action_salir"},
    },
    "main_imo": {
        "text": "🌟 *Bienvenido Líder IMO {nombre}*\nCanal Corporativo Oficial. Selecciona una opción:\n\n1️⃣ Ver mis rezagados (Pendientes C1/C2)\n2️⃣ Ver estado de TODOS mis enrolados\n3️⃣ Hablar con Coordinación IMO\n0️⃣ Finalizar",
        "options": {"1":"ver_pendientes_imo","2":"ver_todos_imo","3":"pre_action_humano_soporte_imo","0":"action_salir"},
    },
    "main_px_rezagado_c1": {
        "text": "🌟 *Hola {nombre}.*\nTienes pendiente vivir tu *Capítulo 1 (Fase de Descubrimiento)*. ¡Tu transformación te espera!\n\n1️⃣ Confirmar mi asistencia para la próxima fecha\n2️⃣ Ver fechas y horarios del C1\n3️⃣ Solicitar reprogramación a Coordinación\n4️⃣ Ver a mis invitados enrolados\n0️⃣ Finalizar",
        "options": {"1":"pre_action_humano_confirma_c1","2":"info_fechas","3":"pre_action_humano_reprogramacion_c1","4":"ver_todos_imo","0":"action_salir"},
    },
    "main_px_upsell_c2": {
        "text": "🌟 *¡Hola {nombre}! Diste el primer paso en C1.*\nTu siguiente nivel de transformación profunda te espera. Tienes pendiente tu *Capítulo 2 (C2)*.\n\n1️⃣ Información y fechas del Capítulo 2 (C2)\n2️⃣ Confirmar asistencia / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1":"info_fechas","2":"pagos","3":"ver_todos_imo","4":"pre_action_humano_asesoria_c2","0":"action_salir"},
    },
    "main_px_upsell_mj": {
        "text": "🌟 *¡Felicidades por completar tu C2, {nombre}!*\nEl último paso para llevar tu liderazgo a tu familia y finanzas es la *Maestría (MJ)*.\n\n1️⃣ Información y fechas de Maestría (MJ)\n2️⃣ Confirmar inscripción / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con Coordinación de Maestría\n0️⃣ Finalizar",
        "options": {"1":"info_fechas","2":"pagos","3":"ver_todos_imo","4":"pre_action_humano_asesoria_mj","0":"action_salir"},
    },
    "main_mj": {
        "text": "🌟 *Portal de Graduados*\n¡Un honor saludarte, Líder {nombre}! Tu transformación inspira a otros.\n\n¿Desde qué espacio requieres apoyo o eliges servir hoy?\n1️⃣ Enrolar a un nuevo participante\n2️⃣ Ver TODOS mis enrolados y su estatus\n3️⃣ Hablar con Coordinación de Maestría\n4️⃣ Postularme al programa de Aliados\n0️⃣ Menú principal",
        "options": {"1":"pre_action_humano_enrolar","2":"ver_todos_imo","3":"pre_action_humano_soporte_mj","4":"pre_action_humano_aliados","0":"main"},
    },
    "info_entrenamientos": {
        "text": "📘 *Crear Poder Sin Límites*\nSomos un centro de entrenamiento de liderazgo y transformación cuántica de alto rendimiento. Nuestra misión es impulsarte a salir del \"modo automático\" y aplicar los principios de la física cuántica para que elijas vivir una vida extraordinaria.\n\nSelecciona el nivel que estás listo para explorar:\n1️⃣ C1 (Capítulo Uno) - El Descubrimiento\n2️⃣ C2 (Capítulo Dos) - La Experiencia\n3️⃣ MJ (Maestría del Juego) - La Práctica\n4️⃣ Fechas y lugares\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1":"info_c1","2":"info_c2","3":"info_mj","4":"info_fechas","9":"volver","0":"main"},
    },
    "info_c1": {
        "text": "🚀 *C1 (Capítulo Uno) - El Descubrimiento*\nUn entrenamiento vivencial de 3 días diseñado para romper paradigmas, observar tus mecanismos de defensa automáticos y confrontar los límites que te has puesto a ti mismo.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1":"pre_action_humano_info_c1","9":"volver","0":"main"},
    },
    "info_c2": {
        "text": "🔥 *C2 (Capítulo Dos) - La Experiencia*\n4 días inmersivos de alto riesgo emocional para atravesar de frente las barreras descubiertas en el C1. Diseñado para dar un salto cuántico y elegir rediseñar por completo tu realidad.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1":"pre_action_humano_info_c2","9":"volver","0":"main"},
    },
    "info_mj": {
        "text": "👑 *MJ (Maestría del Juego) - La Práctica*\nUn programa continuo de 100 días donde el liderazgo se lleva a la cancha real. Integrarás lo aprendido en C1 y C2, forjando disciplina para crear resultados sostenibles.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1":"pre_action_humano_info_mj","9":"volver","0":"main"},
    },
    "info_fechas": {
        "text": "dinamico",
        "options": {"1":"pre_action_humano_coordinacion","9":"volver","0":"main"},
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher / Factura a Coordinación\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1":"pre_action_humano_pagos","9":"volver","0":"main"},
    },
}

# ══════════════════════════════════════════════════════════════
# 10. FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════
def flujo_principal(telefono, texto):
    try:
        sesion = get_sesion(telefono)
        # FIX: Prevención de Amnesia y Sobreescritura
        if sesion is None:
            logger.warning(f"Ignorando mensaje de {telefono} por saturación de sistema (No se pudo bloquear sesión).")
            return 

        txt_up = str(texto).strip().upper()

        if txt_up in {"STOP","BAJA","DETENER","ALTO","NO MAS MENSAJES"}:
            marcar_stop(telefono)
            borrar_sesion(telefono)
            with _perfil_cache_lock: _perfil_cache.pop(norm_tel(telefono), None)
            enviar_mensaje(telefono, "Has sido dado de baja. No recibirás más mensajes.", "SISTEMA", True, "STOP")
            return

        if "perfil" not in sesion or txt_up in {"0","MENU","MENÚ","INICIO"}:
            perfil = obtener_perfil_crm(telefono)
            if perfil["rol"] == "PROSPECTO" and len(texto.split()) <= 3 and len(texto) > 2 and not txt_up.isnumeric():
                perfil["nombre"] = nombre_pila(texto)
            sesion["perfil"] = perfil
            set_sesion(telefono, sesion)
        else:
            perfil = sesion.get("perfil", {})

        nombre_show = f"({perfil.get('rol','PROSPECTO')}) {perfil.get('nombre','Nuevo')}" if perfil.get("nombre") else "NUEVO CONTACTO"

        if sesion.get("menu_state") == "esperando_humano":
            if txt_up not in {"0","MENU","MENÚ","INICIO"}: return

        if sesion.get("menu_state") == "esperando_encuesta":
            if txt_up in {"1","2","3","4","5"}:
                enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟\n_Escribe MENU para reiniciar._", nombre_show, True, "ENCUESTA CSAT")
                borrar_sesion(telefono)
            else:
                enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_show, True, "ERROR CSAT")
            return

        if sesion.get("menu_state") == "capturando_motivo":
            if txt_up in {"0","MENU","MENÚ","INICIO"}:
                sesion.pop("menu_state", None); sesion.pop("contexto_derivacion", None)
                set_sesion(telefono, sesion)
            else:
                sesion["motivo_temp"] = texto
                sesion["menu_state"]  = "confirmando_derivacion"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, f"⚡ Entendido. Te vamos a derivar con Coordinación para tratar:\n\n💬 _{texto}_\n\n*¿Es correcto?*\n1️⃣ Sí, derivar a Coordinación ahora\n2️⃣ No, cancelar y volver al menú", nombre_show, True, "DOBLE OPT-IN")
                return

        if sesion.get("menu_state") == "confirmando_derivacion":
            if txt_up == "1":
                motivo   = sesion.get("motivo_temp", "Sin detalle")
                contexto = sesion.get("contexto_derivacion", "GENERAL")
                notificar_coordinadora_interna(telefono, perfil.get("nombre"), motivo, contexto)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "¡Excelente! Tu consulta ha sido derivada a Coordinación. Te responderemos pronto.\n\n_Escribe *0* para volver al menú._", nombre_show, True, "DERIVADO EXITOSO")
            elif txt_up == "2":
                hist = sesion.get("menu_history", [])
                prev = hist[-1] if hist else _get_main_key(perfil)
                sesion["menu_state"] = prev
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Operación cancelada. No se ha notificado a Coordinación.\nVolviendo al menú...", nombre_show, True, "DERIVACIÓN CANCELADA")
            else:
                enviar_mensaje(telefono, "⚠️ Opción no válida. Responde *1* para derivar o *2* para cancelar.", nombre_show, True, "ERROR OPT-IN")
            return

        # FIX: Universal Time Compat con strptime
        try:
            last_str = sesion.get("last_interaction", "2000-01-01 00:00:00")
            if len(last_str) == 19:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ_LIMA)
            else:
                last_dt = datetime.fromisoformat(last_str)
            inact = (ahora_lima() - last_dt).total_seconds() / 60.0
        except Exception:
            inact = 9999

        sesion["last_interaction"] = ahora_lima_str()
        main_key = _get_main_key(perfil)

        def render_menu(m_key):
            if m_key == "info_fechas":
                return f"📅 *Fechas Disponibles*\n\n🚀 *C1:* {get_fecha_activa('C1')}\n🔥 *C2:* {get_fecha_activa('C2')}\n👑 *MJ (Creación):* {get_fecha_activa('MJ')}\n\n1️⃣ Hablar con Coordinación\n9️⃣ Regresar\n0️⃣ Menú principal"
            txt = MENU_STRUCTURE.get(m_key, MENU_STRUCTURE["main_prospecto"])["text"]
            if "{" in txt:
                txt = txt.format(nombre=perfil.get("nombre", "Líder"), imo=perfil.get("imo_nombre", "tu líder"), pendiente=perfil.get("pendiente", "tu nivel"))
            return txt

        def ir_main():
            sesion["menu_state"]   = main_key
            sesion["menu_history"] = []
            sesion["menu_errors"]  = 0
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(main_key), nombre_show, True, main_key)

        if (inact > 30 or "menu_state" not in sesion or txt_up in {"0","MENU","MENÚ","INICIO"}):
            ir_main()
            return

        if txt_up in {"9","VOLVER","ATRAS","ATRÁS"}:
            hist = sesion.get("menu_history", [])
            if hist:
                prev = hist.pop()
                sesion["menu_state"]   = prev
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, render_menu(prev), nombre_show, True, prev)
            else:
                ir_main()
            return

        estado = sesion.get("menu_state", main_key)
        if estado not in MENU_STRUCTURE:
            ir_main()
            return

        siguiente = MENU_STRUCTURE[estado].get("options", {}).get(txt_up)

        if siguiente:
            sesion["menu_errors"] = 0
            if siguiente.startswith("pre_action_humano"):
                contexto = siguiente.replace("pre_action_humano_", "").upper().replace("_", " ")
                if siguiente == "pre_action_humano_actualizar_numero":
                    msg = "Para actualizar tu registro corporativo, por favor indícame en un solo mensaje:\n*¿Cuál es tu Nombre Completo y tu DNI?*"
                else:
                    msg = "Para asignar tu caso de forma correcta, por favor descríbeme en un solo mensaje:\n*¿Cuál es exactamente tu requerimiento?*"
                sesion["contexto_derivacion"] = contexto
                hist = sesion.get("menu_history", [])
                if not hist or hist[-1] != estado: hist.append(estado)
                sesion["menu_state"]   = "capturando_motivo"
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, msg, nombre_show, True, "PIDIENDO MOTIVO")
                return

            if siguiente == "ver_pendientes_imo":
                lista = buscar_pendientes_imo_csv(telefono)
                msg   = "📊 *Reporte de Equipo (Rezagados)*\n\n" + "\n".join(lista) + "\n\n_Escribe *0* para volver._" if lista else "¡Todos tus participantes se han sentado! 🎉\n\n_Escribe *0* para volver._"
                enviar_mensaje(telefono, msg, nombre_show, True, "REPORTE PENDIENTES")
                hist = sesion.get("menu_history", [])
                if not hist or hist[-1] != estado: hist.append(estado)
                sesion["menu_state"]   = "ver_pendientes_imo"
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                return

            if siguiente == "ver_todos_imo":
                sentados, reza = reporte_sentados_imo(telefono)
                msg = "📊 *Reporte Especial de Comunidad*\n\n✅ *Sentados / Activos:*\n" + ("\n".join(sentados) if sentados else "Ninguno") + "\n\n⏳ *No Sentados / Rezagados:*\n" + ("\n".join(reza) if reza else "Ninguno") + "\n\n_Escribe *0* para volver al menú._"
                enviar_mensaje(telefono, msg, nombre_show, True, "REPORTE TODOS")
                hist = sesion.get("menu_history", [])
                if not hist or hist[-1] != estado: hist.append(estado)
                sesion["menu_state"]   = "ver_todos_imo"
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                return

            if siguiente == "action_salir":
                sesion["menu_state"] = "esperando_encuesta"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Antes de irte, ¿cómo calificarías tu experiencia?\n\nResponde del *1 al 5*:\n1️⃣ = Mala   5️⃣ = ¡Excelente!", nombre_show, True, "ENCUESTA SALIDA")
                return

            dest = main_key if siguiente == "main" else siguiente
            hist = sesion.get("menu_history", [])
            if estado != main_key and (not hist or hist[-1] != estado): hist.append(estado)
            sesion["menu_state"]   = dest
            sesion["menu_history"] = hist
            set_sesion(telefono, sesion)
            if dest in MENU_STRUCTURE: enviar_mensaje(telefono, render_menu(dest), nombre_show, True, dest)

        else:
            if not txt_up.isnumeric():
                sesion["contexto_derivacion"] = "TEXTO LIBRE"
                hist = sesion.get("menu_history", [])
                if not hist or hist[-1] != estado: hist.append(estado)
                sesion["menu_state"]   = "capturando_motivo"
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Para brindarte atención corporativa, por favor dime en un solo mensaje: *¿Qué necesitas consultar o resolver?*", nombre_show, True, "TEXTO LIBRE")
                return

            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            if errores >= 3:
                sesion["menu_errors"] = 0
                notificar_coordinadora_interna(telefono, perfil.get("nombre"), "Usuario atascado en el menú.", "SISTEMA ERROR")
                enviar_mensaje(telefono, "He notificado a Coordinación para que te asista.\n\n_Escribe *0* para menú principal._", nombre_show, True, "ERROR_DERIVADO")
                sesion["menu_state"] = "esperando_humano"
            else:
                enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado)}", nombre_show, True, "ERROR_MENU")
            set_sesion(telefono, sesion)

    except Exception as e:
        logger.error(f"flujo_principal error {telefono}: {e}", exc_info=True)

def _get_main_key(perfil):
    rol = perfil.get("rol", "PROSPECTO")
    return {"IMO":"main_imo", "MJ":"main_mj", "PX_REZAGADO_C1":"main_px_rezagado_c1", "PX_UPSELL_C2":"main_px_upsell_c2", "PX_UPSELL_MJ":"main_px_upsell_mj", "PX":"main_px_rezagado_c1", "REGISTRADO":"main_px_rezagado_c1"}.get(rol, "main_prospecto")

# ══════════════════════════════════════════════════════════════
# 11. ENDPOINTS FLASK
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode, token, challenge = (request.args.get(k) for k in ["hub.mode","hub.verify_token","hub.challenge"])
    if mode == "subscribe" and token == Config.VERIFY_TOKEN: return challenge, 200
    return "Token inválido", 403

@app.route("/webhook", methods=["POST"])
def recv_webhook():
    data = request.get_json(silent=True)
    if not data: return jsonify({"status":"ok"}), 200
    try:
        changes  = data.get("entry",[{}])[0].get("changes",[{}])[0].get("value",{})
        if "messages" not in changes: return jsonify({"status":"ok"}), 200

        msg      = changes["messages"][0]
        telefono = msg.get("from","")
        tipo     = msg.get("type","")

        sesion      = get_sesion(telefono) or {}
        perfil      = sesion.get("perfil") or obtener_perfil_crm(telefono)
        nombre_cach = f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}" if perfil.get("nombre") else "NUEVO CONTACTO"

        if tipo == "text":
            texto = str(msg["text"]["body"])
            append_historial(telefono, nombre_cach, texto, "in")
            estado_sesion = sesion.get("menu_state","")
            if estado_sesion not in ("capturando_motivo","confirmando_derivacion"):
                SessionManager.guardar_backup_absoluto(telefono, nombre_cach, texto, "IN", "RECIBIDO")
                registrar_en_sheets(telefono, nombre_cach, texto, "", "RECIBIDO")
            threading.Thread(target=flujo_principal, args=(telefono, texto), daemon=False, name=f"flujo-{telefono[-4:]}").start()

        elif tipo in ("audio","image","document","video","sticker"):
            append_historial(telefono, nombre_cach, "[MULTIMEDIA]", "in")
            SessionManager.guardar_backup_absoluto(telefono, nombre_cach, "[MULTIMEDIA]", "IN", "MULTIMEDIA")
            registrar_en_sheets(telefono, nombre_cach, "[MULTIMEDIA]", "", "RECIBIDO")
            estado_sesion = sesion.get("menu_state","")
            if estado_sesion in ("capturando_motivo","confirmando_derivacion"):
                enviar_mensaje(telefono, "Por políticas de registro, por favor escríbeme tu consulta *únicamente en texto*. No procesamos audios ni imágenes en esta etapa.", nombre_cach, True, "ERROR_MULTIMEDIA")
            elif estado_sesion != "esperando_humano":
                enviar_mensaje(telefono, "Por favor responde con texto o el número de tu opción.", nombre_cach, True, "ERROR_MULTIMEDIA")

    except Exception as e: logger.error(f"webhook error: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial", methods=["GET"])
def api_historial(): return jsonify(get_historial()), 200

@app.route("/api/descargar_respaldo", methods=["GET"])
def api_respaldo():
    if os.path.exists(Config.BACKUP_CSV):
        with open(Config.BACKUP_CSV, "r", encoding="utf-8-sig") as f: data = f.read()
    else: data = "Fecha,Telefono,Nombre,Direccion,Mensaje,Estado\nSin datos"
    return Response(data, mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=Backup_V84.csv"})

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    d   = request.json or {}
    tel = d.get("telefono","")
    msg = d.get("mensaje","")
    if not tel or not msg: return jsonify({"error":"Faltan datos"}), 400
    sesion = get_sesion(tel) or {}
    perfil = sesion.get("perfil") or obtener_perfil_crm(tel)
    nombre = f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}" if perfil.get("nombre") else "PANEL"
    enviar_mensaje(tel, msg, nombre, True, "MANUAL_PANEL")
    return jsonify({"status":"ok"}), 200

@app.route("/api/mensaje_simulador", methods=["POST"])
def api_simulador():
    d   = request.json or {}
    tel = d.get("telefono","")
    txt = d.get("texto","")
    if not tel or not txt: return jsonify({"error":"Faltan datos"}), 400
    sesion  = get_sesion(tel) or {}
    perfil  = sesion.get("perfil", {})
    nombre  = f"({perfil.get('rol','PROSPECTO')}) {perfil.get('nombre','Simulado')}" if perfil.get("nombre") else "SIMULACIÓN"
    append_historial(tel, nombre, txt, "in")
    SessionManager.guardar_backup_absoluto(tel, nombre, txt, "IN", "SIMULADOR")
    threading.Thread(target=flujo_principal, args=(tel, txt), daemon=True, name=f"sim-{tel[-4:]}").start()
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status":       "activo",
        "version":      "v84",
        "cola_sheets":  _cola_sheets.qsize(),
        "csv_filas":    len(get_csv_rows()),
        "hora_lima":    ahora_lima().strftime("%d/%m/%Y %H:%M:%S"),
    }), 200

@app.route("/chat", methods=["GET"])
def panel_chat():
    if os.path.exists("panel_chat.html"):
        with open("panel_chat.html", encoding="utf-8") as f: return f.read()
    return "<h2>Panel no disponible</h2><p>Sube panel_chat.html al servidor.</p>", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Bot CPSL v84 — puerto {port}")
    logger.info(f"Excel : {Config.EXCEL_PATH}")
    logger.info(f"CSV   : {Config.CSV_BD_PATH}")
    logger.info(f"Sheet : {Config.SHEET_ID or 'NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=port, debug=False)
