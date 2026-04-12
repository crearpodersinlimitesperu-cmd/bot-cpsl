"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V85: Persistent Quantum Architecture (Blindaje con Disco Render /data)
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
# 1. ZONA HORARIA Y DIRECTORIO PERSISTENTE
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))

# FIX CORPORATIVO: Detectar si estamos en Render con disco persistente
DATA_DIR = "/data" if os.path.exists("/data") else "."
logger.info(f"Directorio de almacenamiento activo: {DATA_DIR}")

def ahora_lima():
    return datetime.now(TZ_LIMA)

def ahora_lima_str():
    return ahora_lima().strftime("%Y-%m-%d %H:%M:%S")

def get_csv_bd_path():
    # El archivo de base de datos se busca en el raíz o en /data
    for path in [".", DATA_DIR]:
        archivos = [f for f in os.listdir(path) if f.startswith("participantes_") and f.endswith(".csv")]
        if archivos:
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
            return os.path.join(path, archivos[0])
    return "base_datos.csv"

class Config:
    TOKEN               = os.environ.get("WA_TOKEN", "")
    PHONE_ID            = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN        = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    EXCEL_PATH          = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")
    CSV_BD_PATH         = os.environ.get("CSV_BD_PATH", get_csv_bd_path())
    # Archivos movidos al disco persistente
    SESSIONS_PATH       = os.path.join(DATA_DIR, "sesiones.json")
    SESSIONS_SIM_PATH   = os.path.join(DATA_DIR, "sesiones_sim.json")   
    HISTORIAL_PATH      = os.path.join(DATA_DIR, "historial_chat.json")
    BACKUP_CSV          = os.path.join(DATA_DIR, "backup_absoluto_mensajes.csv")
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
    if not os.path.exists(path): return []
    try:
        mtime = os.path.getmtime(path)
        with _csv_lock:
            if _csv_rows is not None and mtime == _csv_mtime: return _csv_rows
            delim = _detectar_delimitador(path)
            with open(path, "r", encoding="utf-8-sig") as f:
                rows = list(csv.DictReader(f, delimiter=delim))
            _csv_rows, _csv_mtime = rows, mtime
            logger.info(f"CSV recargado: {len(rows)} filas de la base maestra.")
            return rows
    except Exception as e:
        logger.error(f"Error en caché CSV: {e}")
        return []

# ══════════════════════════════════════════════════════════════
# 3. SESSION MANAGER (PERSISTENCIA BLINDADA)
# ══════════════════════════════════════════════════════════════
class SessionManager:
    @staticmethod
    def _path(telefono):
        return Config.SESSIONS_SIM_PATH if str(telefono).startswith("SIM_") else Config.SESSIONS_PATH

    @classmethod
    def _load(cls, path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f: return json.load(f)
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
            logger.warning(f"Timeout en disco para {telefono}. Protegiendo datos...")
            return None
        except Exception as e:
            logger.error(f"Error lectura sesión: {e}")
            return None

    @classmethod
    def set_sesion(cls, telefono, data_dict):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data[str(telefono)] = data_dict
                cls._save(path, data)
        except Exception as e:
            logger.error(f"Error escritura sesión: {e}")

    @classmethod
    def borrar_sesion(cls, telefono):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data.pop(str(telefono), None)
                cls._save(path, data)
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
                if len(h) > 5000: h = h[-5000:]
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
                    if nuevo: w.writerow(["Fecha y Hora","Telefono","Nombre","Direccion","Mensaje","Estado"])
                    w.writerow([ahora_lima_str(), telefono, nombre, direccion, mensaje, estado_sistema])
        except Exception: pass

def get_sesion(tel): return SessionManager.get_sesion(tel)
def set_sesion(tel, d): SessionManager.set_sesion(tel, d)
def borrar_sesion(tel): SessionManager.borrar_sesion(tel)
def append_historial(t, n, x, p): SessionManager.append_historial(t, n, x, p)

def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: pass
    return []

# ══════════════════════════════════════════════════════════════
# 4. GOOGLE SHEETS (COLAS Y TOKENS)
# ══════════════════════════════════════════════════════════════
_sheets_token, _sheets_token_exp = None, 0
_sheets_tok_lock = threading.Lock()

def _get_sheets_token():
    global _sheets_token, _sheets_token_exp
    with _sheets_tok_lock:
        if _sheets_token and time.time() < _sheets_token_exp - 60: return _sheets_token
        if not Config.CREDS_JSON: return None
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now, creds = int(time.time()), json.loads(Config.CREDS_JSON)
            pk_pem = creds["private_key"].replace("\\n", "\n")
            hdr = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            pld = base64.urlsafe_b64encode(json.dumps({"iss": creds["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets", "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600}).encode()).rstrip(b"=")
            pk = serialization.load_pem_private_key(pk_pem.encode(), password=None)
            sig = pk.sign(hdr + b"." + pld, cp.PKCS1v15(), hashes.SHA256())
            jwt = (hdr + b"." + pld + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}, timeout=10)
            if r.status_code == 200:
                d = r.json()
                _sheets_token, _sheets_token_exp = d["access_token"], now + d.get("expires_in", 3600)
                return _sheets_token
        except Exception: pass
    return None

_cola_sheets = queue.Queue()

def _worker_sheets():
    while True:
        try:
            t = _cola_sheets.get()
            if not Config.SHEET_ID: continue
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

    url, headers = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages", {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto, "preview_url": False}}
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
# 6. CRM Y UTILIDADES
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
    return a == b or (min(len(a), len(b)) >= 8 and (a.endswith(b) or b.endswith(a)))

def nombre_pila(s):
    partes = [p for p in re.split(r'\s+', s.strip()) if len(p) > 2]
    return partes[0].title() if partes else s.strip().title()

_perfil_cache, _perfil_cache_lock = {}, threading.Lock()

def cargar_px_del_imo(telefono):
    if not os.path.exists(Config.EXCEL_PATH): return "", []
    try:
        with FileLock(Config.EXCEL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            wb = load_workbook(Config.EXCEL_PATH, data_only=True, read_only=True)
            ws, px_list, imo_nombre = wb["DATA"], [], ""
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 7: continue
                if son_mismo_numero(str(row[3] or ""), telefono):
                    if not imo_nombre: imo_nombre = str(row[0] or "").strip()
                    est, px = str(row[6] or "").strip().upper(), str(row[4] or "").strip()
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
    if imo_nom and px_list: perfil["rol"], perfil["nombre"] = "IMO", imo_nom

    rows = get_csv_rows()
    if rows:
        keys = {k.strip().lower(): k for k in rows[0].keys() if k}
        tel_k = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None)
        nom_k = next((k for k in keys.values() if "nombre" in k.lower()), None)
        ape_k = next((k for k in keys.values() if "apellido" in k.lower()), None)
        c1_k = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
        c2_k = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
        mj_k = next((k for k in keys.values() if "maestr" in k.lower()), None)
        i_nom_k = next((k for k in keys.values() if "imo" in k.lower() and "tel" not in k.lower()), None)
        i_tel_k = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)

        for row in rows:
            if i_tel_k and son_mismo_numero(str(row.get(i_tel_k, "")), telefono):
                perfil["rol"] = "IMO"
                if not perfil["nombre"] and i_nom_k: perfil["nombre"] = nombre_pila(str(row.get(i_nom_k, "")))
            if tel_k and son_mismo_numero(str(row.get(tel_k, "")), telefono):
                n, a = str(row.get(nom_k, "")).strip(), str(row.get(ape_k, "")).strip() if ape_k else ""
                perfil["px_nombre"] = (n.split()[0] + " " + a.split()[0]).title().strip() if (n and a) else nombre_pila(n)
                c1, c2, mj = [str(row.get(k, "NO")).strip().upper() in ("SI", "S") for k in [c1_k, c2_k, mj_k]]
                if mj: perfil["px_pendiente"], perfil["rol_base"] = "Ninguno (Maestría iniciada)", "MJ"
                elif c1 and c2: perfil["px_pendiente"], perfil["rol_base"] = "Maestría (MJ)", "PX_UPSELL_MJ"
                elif c1: perfil["px_pendiente"], perfil["rol_base"] = "Capítulo 2 (C2)", "PX_UPSELL_C2"
                else: perfil["px_pendiente"], perfil["rol_base"] = "Capítulo 1 (C1)", "PX_REZAGADO_C1"
                perfil["imo_nombre"] = nombre_pila(str(row.get(i_nom_k, "Tu líder"))) if i_nom_k else "Tu líder"
                perfil["imo_tel"] = str(row.get(i_tel_k, "")) if i_tel_k else ""

    if perfil["rol"] != "IMO" and perfil.get("px_nombre"):
        perfil["nombre"], perfil["pendiente"], perfil["rol"] = perfil["px_nombre"], perfil.get("px_pendiente"), perfil.get("rol_base", "PX_REZAGADO_C1")
    with _perfil_cache_lock: _perfil_cache[tel_norm] = perfil
    return perfil

# ══════════════════════════════════════════════════════════════
# 7. RELOJ DINÁMICO LIMA 2026
# ══════════════════════════════════════════════════════════════
def get_fecha_activa(tipo):
    ahora = ahora_lima()
    evs = {
        "C1": [{"co": datetime(2026,5,1,11,30,tzinfo=TZ_LIMA), "t": "Viernes 01 de Mayo 9:00 AM (E27)"}],
        "C2": [{"co": datetime(2026,4,9,15,30,tzinfo=TZ_LIMA), "t": "Jueves 09 de Abril 1:00 PM (E26)"}, {"co": datetime(2026,5,14,15,30,tzinfo=TZ_LIMA), "t": "Jueves 14 de Mayo 1:00 PM (E27)"}],
        "MJ": [{"co": datetime(2026,4,17,19,0,tzinfo=TZ_LIMA), "t": "Viernes 17 de Abril 5:00 PM (Inicia E26)"}]
    }
    for ev in evs.get(tipo, []):
        if ahora <= ev["co"]: return ev["t"]
    return "Fechas por confirmar."

# ══════════════════════════════════════════════════════════════
# 8. SMART ROUTING
# ══════════════════════════════════════════════════════════════
def notificar_coordinadora_interna(p_tel, p_nom, motivo, ctx="GENERAL"):
    ahora, targets = ahora_lima(), {"Diana": "51912379744", "Joyce": "51933599903", "Zuley": "51933599864"}
    if any(x in ctx for x in ("MAESTRÍA","MJ","RETOMAR","SOPORTE MJ")):
        targets = {"Linid": "51912379686"}
        if ahora >= datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385"
    elif ahora < datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385"
    c_n, c_t = random.choice(list(targets.items()))
    msg = f"🚨 *NUEVO TICKET* 🚀\n*Nombre:* {p_nom or '??'}\n*Tel:* wa.me/{p_tel}\n*Contexto:* {ctx}\n*Requerimiento:* {motivo}"
    enviar_mensaje(c_t, msg, f"COORDINACIÓN: {c_n}", True, "ALERTA TICKET")
    return c_n

# ══════════════════════════════════════════════════════════════
# 9. MENÚS Y FLUJO
# ══════════════════════════════════════════════════════════════
MENU_STR = {
    "main_prospecto": {"text": "🌟 *Bienvenido a CPSL Perú*\n\n1️⃣ Información Entrenamientos\n2️⃣ Inversión y Pagos\n3️⃣ Actualizar mi número\n4️⃣ Coordinación\n0️⃣ Salir", "options": {"1":"info_entrenamientos","2":"pagos","3":"pre_action_humano_actualizar_numero","4":"pre_action_humano_coordinacion","0":"action_salir"}},
    "main_imo": {"text": "🌟 *Hola Líder IMO {nombre}*\n\n1️⃣ Rezagados (Falta C1/C2)\n2️⃣ Estado de enrolados\n3️⃣ Coordinación IMO\n0️⃣ Salir", "options": {"1":"ver_pendientes_imo","2":"ver_todos_imo","3":"pre_action_humano_soporte_imo","0":"action_salir"}},
    "main_px_rezagado_c1": {"text": "🌟 *Hola {nombre}.*\nTienes pendiente tu *C1 (Descubrimiento)*.\n\n1️⃣ Confirmar para próxima fecha\n2️⃣ Ver fechas y horarios\n3️⃣ Reprogramar\n0️⃣ Salir", "options": {"1":"pre_action_humano_confirma_c1","2":"info_fechas","3":"pre_action_humano_reprogramacion_c1","0":"action_salir"}}
}

def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel)
        if sesion is None: return
        txt_up = str(texto).strip().upper()
        if txt_up in {"STOP","BAJA","DETENER"}:
            marcar_stop(tel); borrar_sesion(tel)
            enviar_mensaje(tel, "Dado de baja. Escribe MENU para volver.", "SISTEMA", True, "STOP")
            return
        
        if "perfil" not in sesion or txt_up in {"0","MENU","MENÚ"}:
            sesion["perfil"] = obtener_perfil_crm(tel)
            if sesion["perfil"]["rol"] == "PROSPECTO" and 2 < len(texto) < 30 and not txt_up.isnumeric():
                sesion["perfil"]["nombre"] = nombre_pila(texto)
            set_sesion(tel, sesion)
        
        perfil, estado = sesion.get("perfil"), sesion.get("menu_state", "main_prospecto")
        nombre_show = f"({perfil.get('rol')}) {perfil.get('nombre','Nuevo')}"
        
        # Lógica de estados simplificada para V85
        if estado == "esperando_humano" and txt_up not in {"0","MENU"}: return
        
        if estado == "capturando_motivo":
            sesion["motivo_temp"], sesion["menu_state"] = texto, "confirmando_derivacion"
            set_sesion(tel, sesion)
            enviar_mensaje(tel, f"⚡ ¿Derivamos con Coordinación para este tema?\n\n💬 _{texto}_\n\n1️⃣ Sí\n2️⃣ No, volver", nombre_show, True, "OPT-IN")
            return

        if estado == "confirmando_derivacion":
            if txt_up == "1":
                notificar_coordinadora_interna(tel, perfil.get("nombre"), sesion.get("motivo_temp"), sesion.get("contexto_derivacion", "GENERAL"))
                sesion["menu_state"] = "esperando_humano"
                set_sesion(tel, sesion)
                enviar_mensaje(tel, "Derivado. Te responderemos pronto. Escribe 0 para el menú.", nombre_show, True, "DERIVADO")
            else:
                sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
                enviar_mensaje(tel, "Cancelado. Volviendo al menú principal.", nombre_show, True, "CANCELADO")
            return

        # Reset por inactividad e inicio
        sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
        enviar_mensaje(tel, MENU_STR["main_prospecto"]["text"], nombre_show, True, "MAIN")

    except Exception as e: logger.error(f"Error flujo: {e}")

# ══════════════════════════════════════════════════════════════
# 10. ENDPOINTS FLASK (V85)
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recv():
    data = request.get_json(silent=True)
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        tel, texto = msg["from"], msg["text"]["body"]
        threading.Thread(target=flujo_principal, args=(tel, texto)).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/descargar_respaldo")
def backup():
    if os.path.exists(Config.BACKUP_CSV):
        with open(Config.BACKUP_CSV, "r", encoding="utf-8-sig") as f: return Response(f.read(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=BlackBox_V85.csv"})
    return "No hay datos", 404

@app.route("/chat")
def chat_panel():
    p = "panel_chat.html"
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return f.read()
    return "Sube el panel_chat.html", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
