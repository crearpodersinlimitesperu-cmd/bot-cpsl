"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V87: The Ultimate Architecture (Persistencia + Graduados + Menús Completos + Simulador)
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
# ZONA HORARIA Y DIRECTORIO PERSISTENTE
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."

def ahora_lima(): return datetime.now(TZ_LIMA)
def ahora_lima_str(): return ahora_lima().strftime("%Y-%m-%d %H:%M:%S")

def get_csv_bd_path():
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
    SESSIONS_PATH       = os.path.join(DATA_DIR, "sesiones.json")
    SESSIONS_SIM_PATH   = os.path.join(DATA_DIR, "sesiones_sim.json")   
    HISTORIAL_PATH      = os.path.join(DATA_DIR, "historial_chat.json")
    BACKUP_CSV          = os.path.join(DATA_DIR, "backup_absoluto_mensajes.csv")
    SHEET_ID            = os.environ.get("SHEET_ID", "")
    CREDS_JSON          = os.environ.get("GOOGLE_CREDENTIALS", "")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# CACHÉ CSV Y RECONOCIMIENTO DE GRADUADOS
# ══════════════════════════════════════════════════════════════
_csv_rows, _csv_mtime, _csv_lock = None, 0.0, threading.Lock()
_graduados_phones = set()

def _detectar_delimitador(path):
    try:
        with open(path, "r", encoding="utf-8-sig") as f: return ";" if f.readline().count(";") > 0 else ","
    except: return ","

def cargar_memoria_graduados(rows):
    global _graduados_phones
    _graduados_phones.clear()
    try:
        archivos_grad = [f for f in os.listdir(DATA_DIR) if "GRADUADO" in f.upper() and f.endswith(".csv")]
        if not archivos_grad: archivos_grad = [f for f in os.listdir(".") if "GRADUADO" in f.upper() and f.endswith(".csv")]
        if not archivos_grad: return

        with open(os.path.join(DATA_DIR if os.path.exists(os.path.join(DATA_DIR, archivos_grad[0])) else ".", archivos_grad[0]), 'r', encoding='utf-8-sig') as f:
            nombres_grad = [line.split(',')[0].strip().upper() for line in f.readlines()[1:] if line.split(',')[0].strip()]

        keys = {k.strip().lower(): k for k in rows[0].keys() if k}
        tel_k = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None)
        nom_k = next((k for k in keys.values() if "nombre" in k.lower()), None)
        ape_k = next((k for k in keys.values() if "apellido" in k.lower()), None)

        for row in rows:
            n, a = str(row.get(nom_k, "")).strip().upper(), str(row.get(ape_k, "")).strip().upper() if ape_k else ""
            full_name = f"{n} {a}".strip()
            tel = norm_tel(row.get(tel_k, ""))
            if tel and full_name:
                if any(g in full_name or full_name in g for g in nombres_grad if len(g)>3):
                    _graduados_phones.add(tel)
    except Exception as e: logger.error(f"Error cruzando graduados: {e}")

def get_csv_rows():
    global _csv_rows, _csv_mtime
    path = Config.CSV_BD_PATH
    if not os.path.exists(path): return []
    try:
        mtime = os.path.getmtime(path)
        with _csv_lock:
            if _csv_rows is not None and mtime == _csv_mtime: return _csv_rows
            delim = _detectar_delimitador(path)
            with open(path, "r", encoding="utf-8-sig") as f: rows = list(csv.DictReader(f, delimiter=delim))
            _csv_rows, _csv_mtime = rows, mtime
            cargar_memoria_graduados(rows)
            return rows
    except: return []

# ══════════════════════════════════════════════════════════════
# SESSION MANAGER (PERSISTENCIA)
# ══════════════════════════════════════════════════════════════
class SessionManager:
    @staticmethod
    def _path(telefono): return Config.SESSIONS_SIM_PATH if str(telefono).startswith("SIM_") else Config.SESSIONS_PATH

    @classmethod
    def get_sesion(cls, telefono):
        try:
            with FileLock(cls._path(telefono) + ".lock", timeout=Config.LOCK_TIMEOUT):
                with open(cls._path(telefono), "r", encoding="utf-8") as f: return json.load(f).get(str(telefono), {})
        except: return {}

    @classmethod
    def set_sesion(cls, telefono, data_dict):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = {}
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                data[str(telefono)] = data_dict
                with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        except: pass

    @classmethod
    def borrar_sesion(cls, telefono):
        path = cls._path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f: data = json.load(f)
                    data.pop(str(telefono), None)
                    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        except: pass

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        try:
            with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
                h = []
                if os.path.exists(Config.HISTORIAL_PATH):
                    with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: h = json.load(f)
                h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": ahora_lima().strftime("%d/%m %H:%M")})
                if len(h) > 5000: h = h[-5000:]
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, indent=2)
        except: pass

    @staticmethod
    def guardar_backup_absoluto(telefono, nombre, mensaje, direccion, estado_sistema):
        try:
            with FileLock(Config.BACKUP_CSV + ".lock", timeout=Config.LOCK_TIMEOUT):
                nuevo = not os.path.exists(Config.BACKUP_CSV)
                with open(Config.BACKUP_CSV, "a", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    if nuevo: w.writerow(["Fecha y Hora","Telefono","Nombre","Direccion","Mensaje","Estado"])
                    w.writerow([ahora_lima_str(), telefono, nombre, direccion, mensaje, estado_sistema])
        except: pass

def get_sesion(tel): return SessionManager.get_sesion(tel)
def set_sesion(tel, d): SessionManager.set_sesion(tel, d)
def borrar_sesion(tel): SessionManager.borrar_sesion(tel)
def append_historial(t, n, x, p): SessionManager.append_historial(t, n, x, p)
def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return []

# ══════════════════════════════════════════════════════════════
# WHATSAPP API & SHEETS QUEUE
# ══════════════════════════════════════════════════════════════
_cola_sheets = queue.Queue()
def registrar_en_sheets(tel, nom, msg, resp, est=""):
    if not str(tel).startswith("SIM_"): _cola_sheets.put({"tel": tel, "nom": nom, "msg": msg, "resp": resp, "est": est})

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=True, estado_menu="INTERACTIVO"):
    if str(telefono).startswith("SIM_"):
        append_historial(telefono, nombre_imo, texto, "out")
        SessionManager.guardar_backup_absoluto(telefono, nombre_imo, texto, "OUT", estado_menu or "SIMULADOR")
        return True
    try:
        r = req_lib.post(f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages", 
                         json={"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto}}, 
                         headers={"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}, timeout=10)
        if r.status_code == 200:
            append_historial(telefono, nombre_imo, texto, "out")
            SessionManager.guardar_backup_absoluto(telefono, nombre_imo, texto, "OUT", estado_menu)
            if registrar_sheets: registrar_en_sheets(telefono, nombre_imo, "", texto[:500], estado_menu)
            return True
    except: pass
    return False

# ══════════════════════════════════════════════════════════════
# CRM Y ETIQUETADO DE GRADUADOS
# ══════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0")  and len(t) == 10: return t[1:]
    return t[-9:] if len(t) > 10 else t

def son_mismo_numero(t1, t2):
    a, b = norm_tel(t1), norm_tel(t2)
    if not a or not b: return False
    return a == b or (min(len(a), len(b)) >= 8 and (a.endswith(b) or b.endswith(a)))

def nombre_pila(s): return s.strip().split()[0].title() if s.strip() else ""

_perfil_cache, _perfil_cache_lock = {}, threading.Lock()

def obtener_perfil_crm(telefono):
    tel_norm = norm_tel(telefono)
    with _perfil_cache_lock:
        if tel_norm in _perfil_cache: return _perfil_cache[tel_norm]

    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": "Capítulo 1 (C1)"}
    rows = get_csv_rows()
    if rows:
        keys = {k.strip().lower(): k for k in rows[0].keys() if k}
        tel_k = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None)
        nom_k = next((k for k in keys.values() if "nombre" in k.lower()), None)
        c1_k = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
        c2_k = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
        
        for row in rows:
            if tel_k and son_mismo_numero(str(row.get(tel_k, "")), telefono):
                perfil["nombre"] = nombre_pila(str(row.get(nom_k, "")))
                c1 = str(row.get(c1_k, "NO")).strip().upper() in ("SI", "S")
                c2 = str(row.get(c2_k, "NO")).strip().upper() in ("SI", "S")
                if c1 and c2: perfil["pendiente"], perfil["rol"] = "Maestría (MJ)", "PX_UPSELL_MJ"
                elif c1: perfil["pendiente"], perfil["rol"] = "Capítulo 2 (C2)", "PX_UPSELL_C2"
                else: perfil["pendiente"], perfil["rol"] = "Capítulo 1 (C1)", "PX_REZAGADO_C1"
                break
                
    if tel_norm in _graduados_phones:
        perfil["rol"] = "GRADUADO"
        perfil["pendiente"] = "Líder Egresado"

    with _perfil_cache_lock: _perfil_cache[tel_norm] = perfil
    return perfil

# ══════════════════════════════════════════════════════════════
# MENÚS Y FLUJO COMPLETO (RESTAURADO DE V84)
# ══════════════════════════════════════════════════════════════
def get_fecha_activa(tipo): return "Próximas fechas por confirmar por Coordinación."

MENU_STR = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial. Responde con el número de tu elección:\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Inversión y Métodos de Pago\n3️⃣ Actualizar mi número\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1":"info_entrenamientos","2":"pagos","3":"pre_action_humano_actualizar","4":"pre_action_humano_coordinacion","0":"action_salir"},
    },
    "main_px_rezagado_c1": {
        "text": "🌟 *Hola {nombre}.*\nTienes pendiente vivir tu *Capítulo 1 (Fase de Descubrimiento)*.\n\n1️⃣ Confirmar mi asistencia\n2️⃣ Ver fechas y horarios\n3️⃣ Solicitar reprogramación\n0️⃣ Finalizar",
        "options": {"1":"pre_action_humano_confirma_c1","2":"info_fechas","3":"pre_action_humano_reprogramacion","0":"action_salir"},
    },
    "main_px_upsell_c2": {
        "text": "🌟 *¡Hola {nombre}! Diste el primer paso en C1.*\nTienes pendiente tu *Capítulo 2 (C2)*.\n\n1️⃣ Información y fechas C2\n2️⃣ Confirmar asistencia / Pago\n3️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1":"info_fechas","2":"pagos","3":"pre_action_humano_asesoria_c2","0":"action_salir"},
    },
    "main_graduado": {
        "text": "👑 *Portal de Líderes Graduados*\n¡Un honor saludarte, Líder {nombre}!\n\n¿Desde qué espacio eliges servir hoy?\n1️⃣ Enrolar a un nuevo participante\n2️⃣ Hablar con Coordinación / Staff\n0️⃣ Finalizar",
        "options": {"1":"pre_action_humano_enrolar","2":"pre_action_humano_coordinacion","0":"action_salir"},
    },
    "info_entrenamientos": {
        "text": "📘 *Crear Poder Sin Límites*\nSelecciona el nivel que estás listo para explorar:\n1️⃣ C1 (Capítulo Uno) - Descubrimiento\n2️⃣ C2 (Capítulo Dos) - La Experiencia\n3️⃣ MJ (Maestría del Juego) - La Práctica\n9️⃣ Regresar",
        "options": {"1":"pre_action_humano_info","2":"pre_action_humano_info","3":"pre_action_humano_info","9":"volver"},
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher a Coordinación\n9️⃣ Regresar",
        "options": {"1":"pre_action_humano_pagos","9":"volver"},
    },
}

def notificar_coordinacion(tel, nom, motivo):
    enviar_mensaje("51912379744", f"🚨 *TICKET*\n*Nombre:* {nom}\n*Tel:* wa.me/{tel}\n*Motivo:* {motivo}", "COORDINACION", True)

def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel) or {}
        txt_up = str(texto).strip().upper()
        
        if txt_up in {"STOP","BAJA"}:
            borrar_sesion(tel)
            enviar_mensaje(tel, "Dado de baja. Escribe MENU para volver.", "SISTEMA", True, "STOP")
            return
            
        if "perfil" not in sesion or txt_up in {"0","MENU","MENÚ","INICIO"}:
            sesion["perfil"] = obtener_perfil_crm(tel)
            if sesion["perfil"]["rol"] == "PROSPECTO" and len(texto) > 2 and not txt_up.isnumeric():
                sesion["perfil"]["nombre"] = nombre_pila(texto)
            sesion["menu_state"] = "main_graduado" if sesion["perfil"].get("rol") == "GRADUADO" else ("main_px_rezagado_c1" if sesion["perfil"].get("rol") == "PX_REZAGADO_C1" else ("main_px_upsell_c2" if sesion["perfil"].get("rol") == "PX_UPSELL_C2" else "main_prospecto"))
            set_sesion(tel, sesion)

        perfil, estado = sesion.get("perfil", {}), sesion.get("menu_state", "main_prospecto")
        nombre_show = f"({perfil.get('rol')}) {perfil.get('nombre','Nuevo')}"
        
        if estado == "esperando_humano":
            if txt_up in {"0","MENU"}:
                sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
                enviar_mensaje(tel, MENU_STR["main_prospecto"]["text"], nombre_show, True, "MAIN")
            return

        if estado == "capturando_motivo":
            if txt_up in {"0","MENU"}:
                sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
            else:
                sesion["motivo_temp"], sesion["menu_state"] = texto, "confirmando_derivacion"
                set_sesion(tel, sesion)
                enviar_mensaje(tel, f"⚡ ¿Derivamos a Coordinación este tema?\n\n💬 _{texto}_\n\n1️⃣ Sí, derivar\n2️⃣ No, cancelar", nombre_show, True, "OPT-IN")
            return

        if estado == "confirmando_derivacion":
            if txt_up == "1":
                notificar_coordinacion(tel, perfil.get("nombre"), sesion.get("motivo_temp"))
                sesion["menu_state"] = "esperando_humano"; set_sesion(tel, sesion)
                enviar_mensaje(tel, "Derivado. Te responderemos pronto. Escribe 0 para el menú.", nombre_show, True, "DERIVADO")
            else:
                sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
                enviar_mensaje(tel, "Cancelado. Volviendo al menú...", nombre_show, True, "MAIN")
            return

        if estado in MENU_STR:
            opciones = MENU_STR[estado].get("options", {})
            if txt_up in opciones:
                sig = opciones[txt_up]
                if sig.startswith("pre_action_humano"):
                    sesion["menu_state"] = "capturando_motivo"; set_sesion(tel, sesion)
                    enviar_mensaje(tel, "Por favor descríbeme en un solo mensaje: *¿Cuál es tu consulta exacta?*", nombre_show, True, "MOTIVO")
                    return
                if sig == "volver" or sig == "action_salir":
                    sesion["menu_state"] = "main_prospecto"; set_sesion(tel, sesion)
                    sig = "main_prospecto"
                if sig in MENU_STR:
                    sesion["menu_state"] = sig; set_sesion(tel, sesion)
                    txt_menu = MENU_STR[sig]["text"].replace("{nombre}", perfil.get("nombre","Líder"))
                    enviar_mensaje(tel, txt_menu, nombre_show, True, sig)
                return

        txt_menu = MENU_STR.get(estado, MENU_STR["main_prospecto"])["text"].replace("{nombre}", perfil.get("nombre","Líder"))
        enviar_mensaje(tel, txt_menu, nombre_show, True, estado)

    except Exception as e: logger.error(f"Error flujo: {e}")

# ══════════════════════════════════════════════════════════════
# ENDPOINTS RESTAURADOS (SIMULADOR Y ENVIAR INCLUIDOS)
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recv():
    try:
        msg = request.get_json(silent=True)["entry"][0]["changes"][0]["value"]["messages"][0]
        tel, texto = msg["from"], msg.get("text",{}).get("body","[Media]")
        threading.Thread(target=flujo_principal, args=(tel, texto)).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial(): return jsonify(get_historial()), 200

@app.route("/api/descargar_respaldo")
def backup():
    if os.path.exists(Config.BACKUP_CSV):
        with open(Config.BACKUP_CSV, "r", encoding="utf-8-sig") as f: return Response(f.read(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=BlackBox_V87.csv"})
    return "No hay datos", 404

# RUTA DEL CHAT MANUAL RESTAURADA
@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    d = request.json or {}
    tel, msg = d.get("telefono",""), d.get("mensaje","")
    if not tel or not msg: return jsonify({"error":"Faltan datos"}), 400
    perfil = obtener_perfil_crm(tel)
    nombre = f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}" if perfil.get("nombre") else "PANEL"
    enviar_mensaje(tel, msg, nombre, True, "MANUAL_PANEL")
    return jsonify({"status":"ok"}), 200

# RUTA DEL SIMULADOR RESTAURADA
@app.route("/api/mensaje_simulador", methods=["POST"])
def api_simulador():
    d = request.json or {}
    tel, txt = d.get("telefono",""), d.get("texto","")
    if not tel or not txt: return jsonify({"error":"Faltan datos"}), 400
    perfil = obtener_perfil_crm(tel)
    nombre = f"({perfil.get('rol','PROSPECTO')}) {perfil.get('nombre','Simulado')}" if perfil.get("nombre") else "SIMULACIÓN"
    append_historial(tel, nombre, txt, "in")
    SessionManager.guardar_backup_absoluto(tel, nombre, txt, "IN", "SIMULADOR")
    threading.Thread(target=flujo_principal, args=(tel, txt)).start()
    return jsonify({"status":"ok"}), 200

@app.route("/chat")
def chat_panel():
    p = "panel_chat.html"
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f: return f.read()
    return "Sube el panel_chat.html", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
