"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
✅ Versión V44: CRM Omnicanal Perfecto (Detección PX, IMO y Auto-Update de Sheets)
"""

import os, re, json, time, csv, io, random, logging
from flask import Flask, request, jsonify, Response
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock
from http import HTTPStatus
import threading

# ── IMPORTS DE LAS IAs ──
GEMINI_DISPONIBLE = False
QWEN_DISPONIBLE = False
genai = None
Generation = None

try:
    import google.generativeai as genai_module
    genai = genai_module
    GEMINI_DISPONIBLE = True
except ImportError:
    pass

try:
    from dashscope import Generation as DashGeneration
    Generation = DashGeneration
    QWEN_DISPONIBLE = True
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN Y CONSTANTES
# ══════════════════════════════════════════════════════════════════════════
class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    
    EXCEL_PATH = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")
    CSV_BD_PATH = os.environ.get("CSV_BD_PATH", "participantes_2026-04-04.csv" if os.path.exists("participantes_2026-04-04.csv") else "base_datos.csv") 
    SESSIONS_PATH = os.environ.get("SESSIONS_PATH", "sesiones.json")
    HISTORIAL_PATH = "historial_chat.json"
    
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
    MODO_IA = os.environ.get("MODO_IA", "fallback").lower() 
    IA_PRIMARIA = os.environ.get("IA_PRIMARIA", "qwen").lower() 
    IA_FALLBACK = os.environ.get("IA_FALLBACK", "gemini").lower()
    
    SHEET_ID = os.environ.get("SHEET_ID", "")
    CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

# ══════════════════════════════════════════════════════════════════════════
# 2. GESTOR DE ESTADO CONCURRENTE (GUNICORN SAFE)
# ══════════════════════════════════════════════════════════════════════════
class SessionManager:
    @staticmethod
    def get_sesion(telefono):
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get(str(telefono), {})
            except Exception as e: pass
            return {}

    @staticmethod
    def set_sesion(telefono, data_dict):
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                data = {}
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                data[str(telefono)] = data_dict
                with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e: pass

    @staticmethod
    def borrar_sesion(telefono):
        tel_str = str(telefono)
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if tel_str in data:
                        del data[tel_str]
                        with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e: pass

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        with FileLock(Config.HISTORIAL_PATH + ".lock"):
            try:
                h = []
                if os.path.exists(Config.HISTORIAL_PATH):
                    with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                        h = json.load(f)
                h.append({
                    "telefono": str(telefono), 
                    "nombre": nombre or "Desconocido", 
                    "texto": texto, 
                    "tipo": tipo, 
                    "hora": datetime.now().strftime("%d/%m %H:%M")
                })
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f:
                    json.dump(h[-10000:], f, ensure_ascii=False, indent=2)
            except Exception as e: pass

    @staticmethod
    def forzar_sincronizacion(leer_sheet_func, norm_tel_func):
        rows = leer_sheet_func()
        if not rows: return
        with FileLock(Config.HISTORIAL_PATH + ".lock"):
            try:
                local_hist = []
                if os.path.exists(Config.HISTORIAL_PATH):
                    with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                        local_hist = json.load(f)
                existing = set(f"{m.get('telefono','')}_{m.get('texto','')}" for m in local_hist)
                for row in rows[1:]:
                    if len(row) < 4: continue
                    hora = str(row[0]).strip(); tel = norm_tel_func(str(row[1]).strip())
                    imo_n = str(row[2]).strip() if len(row) > 2 else ""
                    msg_in = str(row[3]).strip() if len(row) > 3 else ""
                    msg_out = str(row[4]).strip() if len(row) > 4 else ""
                    if tel:
                        if msg_in and f"{tel}_{msg_in}" not in existing:
                            local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_in, "tipo": "in", "hora": hora})
                            existing.add(f"{tel}_{msg_in}")
                        if msg_out and f"{tel}_{msg_out}" not in existing:
                            local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_out, "tipo": "out", "hora": hora})
                            existing.add(f"{tel}_{msg_out}")
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: 
                    json.dump(local_hist[-10000:], f, ensure_ascii=False, indent=2) 
            except Exception as e: pass

def get_sesion(tel): return SessionManager.get_sesion(tel)
def set_sesion(tel, d): SessionManager.set_sesion(tel, d)
def borrar_sesion(tel): SessionManager.borrar_sesion(tel)
def append_historial(tel, nom, txt, tipo): SessionManager.append_historial(tel, nom, txt, tipo)
def forzar_sincronizacion_sheets(): SessionManager.forzar_sincronizacion(leer_sheet, norm_tel)
def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return []

# ══════════════════════════════════════════════════════════════════════════
# 3. WATCHDOG PARÁSITO (Cierre de Inactividad)
# ══════════════════════════════════════════════════════════════════════════
def ejecutar_watchdog_inactividad():
    sesiones_vencidas = []
    with FileLock(Config.SESSIONS_PATH + ".lock"):
        if not os.path.exists(Config.SESSIONS_PATH): return
        try:
            with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                sesiones = json.load(f)
            for telefono, data in list(sesiones.items()):
                if data.get("menu_state") == "esperando_humano": continue
                last_interaction = data.get("last_interaction")
                if last_interaction:
                    try:
                        last_time = datetime.strptime(last_interaction, "%Y-%m-%d %H:%M:%S")
                        if (datetime.now() - last_time).total_seconds() / 60.0 > 30:
                            sesiones_vencidas.append(telefono)
                            del sesiones[telefono]
                    except: pass
            if sesiones_vencidas:
                with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(sesiones, f, ensure_ascii=False, indent=2)
        except: pass
    for tel in sesiones_vencidas:
        msg = "⏳ Hola. Por inactividad hemos finalizado esta sesión para proteger tus datos.\n\n_Si necesitas realizar otra consulta, simplemente escribe la palabra *MENU* para volver a empezar. ¡Que tengas un día extraordinario! ✨_"
        WhatsAppAPI.enviar_mensaje(tel, msg, "SISTEMA", registrar_sheets=True, mensaje_usuario="[CIERRE AUTOMÁTICO DE SESIÓN]")

# ══════════════════════════════════════════════════════════════════════════
# 4. CONECTORES DE API (WhatsApp y Google Sheets)
# ══════════════════════════════════════════════════════════════════════════
class WhatsAppAPI:
    @staticmethod
    def enviar_mensaje(telefono, texto, nombre_mostrar="", registrar_sheets=False, mensaje_usuario=""):
        url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto, "preview_url": False}}
        try:
            r = req_lib.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                SessionManager.append_historial(telefono, nombre_mostrar, texto, "out")
                if registrar_sheets:
                    estado_actual = "SISTEMA" if nombre_mostrar == "SISTEMA" else "INTERACTIVO"
                    threading.Thread(target=registrar_en_sheets, args=(telefono, nombre_mostrar, mensaje_usuario or "[Bot]", texto[:500], estado_actual), daemon=True).start()
                return True
        except Exception as e: pass
        return False

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=False, msg_user=""):
    sesion = get_sesion(telefono)
    if sesion.get("primera_vez", True) and not str(nombre_imo).startswith("COORDINADORA") and nombre_imo != "SISTEMA":
        aclaracion = "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*. Mis respuestas pueden ser limitadas. Para más información, comunícate con nuestras coordinadoras:_\n\n" + COORDINADORAS
        texto += aclaracion if "Coordinadoras C1 y C2" not in texto else "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*._"
        sesion["primera_vez"] = False
        set_sesion(telefono, sesion)
    return WhatsAppAPI.enviar_mensaje(telefono, texto, nombre_imo, registrar_sheets, msg_user)

class GoogleSheetsAPI:
    _token_cache = {"token": None, "exp": 0}
    _token_lock = threading.Lock()

    @classmethod
    def get_token(cls):
        import base64
        now = int(time.time())
        with cls._token_lock:
            if cls._token_cache["token"] and now < cls._token_cache["exp"] - 60: return cls._token_cache["token"]
            if not Config.CREDS_JSON: return None
            try:
                creds = json.loads(Config.CREDS_JSON)
                header = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
                payload = base64.urlsafe_b64encode(json.dumps({
                    "iss": creds["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
                    "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600
                }).encode()).rstrip(b"=")
                msg = header + b"." + payload
                from cryptography.hazmat.primitives import hashes, serialization
                from cryptography.hazmat.primitives.asymmetric import padding
                pk = serialization.load_pem_private_key(creds["private_key"].encode(), password=None)
                sig = pk.sign(msg, padding.PKCS1v15(), hashes.SHA256())
                jwt = (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
                r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    cls._token_cache = {"token": d["access_token"], "exp": now + d.get("expires_in", 3600)}
                    return d["access_token"]
            except: pass
            return None

    @classmethod
    def registrar_accion(cls, telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
        if not Config.SHEET_ID or not Config.CREDS_JSON: return
        token = cls.get_token()
        if not token: return
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H:append"
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        try:
            req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, 
                         json={"values": [[ahora, str(telefono), imo_nombre, mensaje, respuesta_bot, estado, "", ""]]}, 
                         headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        except: pass
            
    @classmethod
    def leer_sheet(cls):
        if not Config.SHEET_ID or not Config.CREDS_JSON: return []
        token = cls.get_token()
        if not token: return []
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H"
        try:
            r = req_lib.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
            if r.status_code == 200: return r.json().get("values", [])
        except: pass
        return []

def registrar_en_sheets(tel, nom, msg, resp, est=""): GoogleSheetsAPI.registrar_accion(tel, nom, msg, resp, est)
def leer_sheet(): return GoogleSheetsAPI.leer_sheet()

# ══════════════════════════════════════════════════════════════════════════
# 5. DATOS MAESTROS Y MENÚS DINÁMICOS CRM
# ══════════════════════════════════════════════════════════════════════════
COORDINADORAS_CONTACTOS = {
    "Diana Moscoso": "51912379744", "Joyce Marín": "51933599903", 
    "Leyla Pasquel": "51919502385", "Zuley Urteaga": "51933599864"
}
COORDINADORAS_LISTA = "\n• Diana Moscoso: +51 912 379 744\n• Joyce Marin: +51 933 599 903\n• Leyla Pasquel: +51 919 502 385\n• Zuley Urteaga: +51 933 599 864"
COORDINADORAS = f"Coordinadoras C1 y C2:{COORDINADORAS_LISTA}"

BROCHURE_INFO_MAESTRA = """
INFORMACIÓN OFICIAL CREAR PODER SIN LÍMITES PERÚ:
- Misión: Impactar a la máxima cantidad de seres humanos a vivir una vida extraordinaria.
- Los 3 Niveles del Proceso (100 Días):
  1. Capítulo 1 (C1): Descubrimiento. 3 días para romper paradigmas y darte cuenta de tus barreras.
  2. Capítulo 2 (C2): Experiencia y Transformación profunda (Usualmente 4 días).
  3. Maestría (MJ - Master Journey): Programa de liderazgo y resultados sostenibles de 100 días para integrar lo aprendido.
- Reglas Importantes: Exclusivo para MAYORES DE 18 AÑOS. Este entrenamiento NO ES PARA SANAR O ARREGLAR. NO sustituye ninguna terapia o proceso de salud mental.
- Opciones de Pago e Inversión: BCP Soles a nombre de CREACIÓN CUÁNTICA E.I.R.L (Cuenta: 1934218307060).
"""

MENU_STRUCTURE = {
    "main_prospecto": {
        "text": (
            "🌟 *Bienvenido a Crear Poder Sin Límites Perú* 🌟\n\n"
            "Soy *IA Cuántica*, tu asistente virtual.\n"
            "Para brindarte una experiencia ágil, responde con el *número* de la opción que buscas:\n\n"
            "1️⃣ *Explorar Entrenamientos* (C1, C2 y Maestría)\n"
            "2️⃣ *Inversión y Pagos* (Modalidades y cuentas)\n"
            "3️⃣ *Hablar con IA Cuántica* (Chat libre, resolvemos dudas)\n"
            "4️⃣ *Atención Personalizada* (Contactar a una coordinadora)\n"
            "0️⃣ *Finalizar sesión*"
        ),
        "options": {"1": "info_entrenamientos", "2": "pagos", "3": "chat_libre_ia", "4": "action_humano", "0": "action_salir"}
    },
    "main_imo": {
        "text": (
            "🌟 *Bienvenido Líder IMO {nombre}* 🌟\n\n"
            "Es un honor apoyarte en tu liderazgo. Selecciona una opción:\n\n"
            "1️⃣ *Reportar Asistencia* de mis participantes\n"
            "2️⃣ *Explorar Entrenamientos* e información oficial\n"
            "3️⃣ *Hablar con una Coordinadora* para apoyo especial\n"
            "0️⃣ *Finalizar sesión*"
        ),
        "options": {"1": "action_imo", "2": "info_entrenamientos", "3": "action_humano", "0": "action_salir"}
    },
    "main_px": {
        "text": (
            "🌟 *Bienvenido de vuelta, {nombre}* 🌟\n\n"
            "Vemos en nuestro sistema que estás acompañado por tu líder *{imo}*.\n"
            "Notamos que tienes pendiente tu: *{pendiente}*.\n\n"
            "¿En qué podemos apoyarte hoy? Responde con el *número*:\n\n"
            "1️⃣ *¡CONFIRMAR MI ASISTENCIA!* (Avisa a tu líder)\n"
            "2️⃣ *Ver fechas y horarios* de mi entrenamiento\n"
            "3️⃣ *Solicitar reprogramación / Cambio*\n"
            "4️⃣ *Hablar con una coordinadora humana*\n"
            "5️⃣ *Chat Libre con IA* (Resolver dudas generales)\n"
            "0️⃣ *Finalizar sesión*"
        ),
        "options": {"1": "px_confirma", "2": "info_fechas", "3": "action_humano", "4": "action_humano", "5": "chat_libre_ia", "0": "action_salir"}
    },
    "info_entrenamientos": {
        "text": "📘 *Explorar Entrenamientos*\n\n1️⃣ Capítulo 1 (C1)\n2️⃣ Capítulo 2 (C2)\n3️⃣ Maestría (MJ)\n4️⃣ Fechas y lugares\n\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "info_c1", "2": "info_c2", "3": "info_mj", "4": "info_fechas", "9": "volver", "0": "main"}
    },
    "info_c1": {
        "text": "🚀 *Capítulo 1 (C1)*: Fase de Descubrimiento. 3 días diseñados para romper paradigmas.\n\n1️⃣ Contactar a un asesor\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": "🔥 *Capítulo 2 (C2)*: Transformación profunda. 4 días inmersivos.\n\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": "👑 *Maestría (MJ)*: Liderazgo y acción. 100 días para crear hábitos inquebrantables.\n\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": "📅 *Fechas y Lugares*\nHotel José Antonio Deluxe (Miraflores, Lima). Para la fecha exacta de tu equipo:\n\n1️⃣ Solicitar calendario a coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher a Coordinadora\n2️⃣ Ayuda con factura/boleta\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "2": "action_humano", "9": "volver", "0": "main"}
    }
}

def notificar_coordinadora_aleatoria(prospecto_tel, prospecto_nombre, necesidad_detectada):
    coord_nombre, coord_tel = random.choice(list(COORDINADORAS_CONTACTOS.items()))
    nombre_txt = prospecto_nombre if prospecto_nombre else "No especificado"
    msg_coord = (
        f"🚨 *NUEVO CONTACTO PARA CREAR* 🚀\n\n"
        f"*Nombre:* {nombre_txt}\n"
        f"*Teléfono:* wa.me/{prospecto_tel}\n"
        f"*Necesidad / Motivo:* {necesidad_detectada}\n\n"
        f"¡Es tu turno de apoyarlo a dar su salto cuántico!"
    )
    sesion_coord = get_sesion(coord_tel)
    sesion_coord["primera_vez"] = False 
    set_sesion(coord_tel, sesion_coord)
    enviar_mensaje(coord_tel, msg_coord, f"COORDINADORA: {coord_nombre}")
    return coord_nombre

# ══════════════════════════════════════════════════════════════════════════
# 6. UTILIDADES, RECONOCIMIENTO CRM Y EXCEL
# ══════════════════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = str(tel).strip().replace("+","").replace(" ","").replace("-","")
    if t.startswith("51") and len(t) == 11: t = t[2:]
    elif t.startswith("0") and len(t) == 10: t = t[1:]
    elif len(t) > 10 and not t.startswith("9"): t = t[-9:]
    return t

def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]: t = t.replace(a, b)
    return t

def nombre_pila(s):
    partes = [p.strip() for p in re.split(r'\s+', s.strip()) if len(p.strip()) > 2]
    return partes[0].title() if partes else s.strip().title()

def cargar_px_del_imo(telefono):
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH, data_only=True, read_only=True)
            ws = wb["DATA"]
            px_list, imo_nombre = [], ""
            tel_n = norm_tel(telefono)
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 7: continue
                imo_n  = str(row[0] or "").strip()
                imo_t  = norm_tel(str(row[3] or ""))
                px_n   = str(row[4] or "").strip()
                estado = str(row[6] or "").strip().upper()
                if imo_t == tel_n:
                    if not imo_nombre: imo_nombre = imo_n
                    if estado in ("PENDIENTE","ENVIADO","") and px_n:
                        px_list.append(px_n)
            wb.close()
            return imo_nombre, px_list
        except: return "", []

def obtener_perfil_crm(telefono):
    """Cerebro del CRM Omnicanal: Detecta si es IMO, PX o Prospecto"""
    tel_n = norm_tel(telefono)
    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    
    # 1. Es IMO?
    imo_nom, px_list = cargar_px_del_imo(tel_n)
    if imo_nom:
        perfil["rol"] = "IMO"
        perfil["nombre"] = imo_nom
        perfil["pendientes"] = px_list
        return perfil
        
    # 2. Buscar en CSV para ver si es PX
    try:
        if os.path.exists(Config.CSV_BD_PATH):
            with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
                primera_linea = f.readline()
                delimitador = ';' if ';' in primera_linea else ','
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimitador)
                
                if reader.fieldnames:
                    tel_key = next((c for c in reader.fieldnames if c and ("tel" in c.lower() or "cel" in c.lower()) and "imo" not in c.lower()), None)
                    nom_key = next((c for c in reader.fieldnames if c and ("nombre" in c.lower())), None)
                    ape_key = next((c for c in reader.fieldnames if c and ("apellido" in c.lower())), None)
                    c1_key = next((c for c in reader.fieldnames if c and ("c1" == c.strip().lower())), None)
                    c2_key = next((c for c in reader.fieldnames if c and ("c2" == c.strip().lower())), None)
                    mj_key = next((c for c in reader.fieldnames if c and ("maestr" in c.lower())), None)
                    imo_nom_key = next((c for c in reader.fieldnames if c and ("imo" in c.lower() and "tel" not in c.lower())), None)
                    imo_tel_key = next((c for c in reader.fieldnames if c and ("tel" in c.lower() and "imo" in c.lower())), None)

                    if tel_key:
                        for row in reader:
                            if not row or not row.get(tel_key): continue
                            if norm_tel(str(row.get(tel_key, ""))) == tel_n:
                                nombre_base = str(row.get(nom_key, "")).strip()
                                apellido_base = str(row.get(ape_key, "")).strip() if ape_key else ""
                                nombre_completo = f"{nombre_base.split()[0]} {apellido_base.split()[0]}".title() if nombre_base and apellido_base else nombre_pila(nombre_base)
                                
                                c1_stat = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                                c2_stat = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
                                mj_stat = str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                                
                                pendiente = "Capítulo 1 (C1)"
                                if c1_stat == "SI": pendiente = "Capítulo 2 (C2)"
                                if c1_stat == "SI" and c2_stat == "SI": pendiente = "Maestría (MJ)"
                                if c1_stat == "SI" and c2_stat == "SI" and mj_stat == "SI": pendiente = "Siguiente Nivel"

                                perfil["rol"] = "PX"
                                perfil["nombre"] = nombre_completo
                                perfil["pendiente"] = pendiente
                                perfil["imo_nombre"] = nombre_pila(str(row.get(imo_nom_key, "Tu líder")).strip()) if imo_nom_key else "Tu líder"
                                perfil["imo_tel"] = norm_tel(str(row.get(imo_tel_key, ""))) if imo_tel_key else ""
                                return perfil
    except Exception as e: logger.error(f"Error en CRM CSV: {e}")
    return perfil

def actualizar_excel(resultados, telefono_imo):
    """Actualiza el excel del IMO cuando el PX confirma directamente"""
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    tel_n = norm_tel(telefono_imo)
    if not tel_n: return
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                imo_t = norm_tel(str(row[3].value or ""))
                px_c = str(row[4].value or "").strip()
                if imo_t != tel_n: continue
                for r in resultados:
                    # Coincidencia flexible de nombres
                    if r["px"].split()[0].lower() in px_c.lower():
                        row[6].value = r["estatus"]; row[7].value = hoy; break
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

def marcar_stop(telefono):
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            for row in wb["DATA"].iter_rows(min_row=2):
                if row and len(row) >= 7 and norm_tel(str(row[3].value or "")) == norm_tel(telefono): 
                    row[6].value = "STOP"; row[7].value = datetime.now().strftime("%d/%m/%Y %H:%M")
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

# ══════════════════════════════════════════════════════════════════════════
# 7. ESTRATEGIA DE IA DUAL (GEMINI + QWEN)
# ══════════════════════════════════════════════════════════════════════════
def embudo_ventas_ia(mensaje_usuario, nombre_conocido=None, nombre_ya_saludado=False):
    if len(mensaje_usuario.split()) <= 3 and nombre_conocido and not nombre_ya_saludado:
        return f"¡Hola, {nombre_conocido}! Creemos firmemente que tienes un potencial ilimitado esperando ser despertado.\n\nA través de metodologías vivenciales, te acompañamos a romper las barreras que te frenan. Todo esto lo vives en el *Capítulo 1*, un entrenamiento intensivo de 3 días para transformar tu realidad. ¿Te gustaría conocer la fecha de nuestro próximo entrenamiento?"
    
    if not Config.GEMINI_KEY or not GEMINI_DISPONIBLE: 
        return "En Crear Poder Sin Límites creemos en acompañarte hacia tu mejor versión. Para apoyarte de forma humana y precisa, responde con el número *4* o *6* para enlazarte con una coordinadora."
    
    try:
        genai.configure(api_key=Config.GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash') 
        prompt = f"""Eres Asesor de 'Crear Poder Sin Límites Perú'. Contacto: {nombre_conocido}. Mensaje: "{mensaje_usuario}"
        Responde cortés, directo. Máximo 3 oraciones. Ofrece info sobre el C1, C2 o Maestría de 100 días.
        No mandes a coordinadoras si puedes ayudar. Cero IA."""
        r = model.generate_content(prompt)
        if r.text: return r.text.strip()
    except: pass
    return "Para apoyarte de forma humana y precisa, responde con el número de la opción para enlazarte con una coordinadora."

# ══════════════════════════════════════════════════════════════════════════
# 8. MÁQUINA DE ESTADOS CRM (NÚCLEO OMNICANAL)
# ══════════════════════════════════════════════════════════════════════════
def procesar_mensaje(telefono, texto):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    
    # -- 1. RECONOCIMIENTO CRM --
    perfil = sesion.get("perfil")
    if not perfil:
        perfil = obtener_perfil_crm(telefono)
        # Solo pedir nombre a los desconocidos
        if perfil["rol"] == "PROSPECTO" and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric():
            perfil["nombre"] = nombre_pila(texto)
        sesion["perfil"] = perfil
        set_sesion(telefono, sesion)
        
    nombre_mostrar = f"({perfil['rol']}) {perfil['nombre']}" if perfil['nombre'] else "NUEVO CONTACTO"

    # -- 2. CSAT ENCUESTA --
    if sesion.get("menu_state") == "esperando_encuesta":
        if texto_limpio in ["1", "2", "3", "4", "5"]:
            threading.Thread(target=registrar_en_sheets, args=(telefono, nombre_mostrar, "Calificación", f"{texto_limpio} Estrellas", "CSAT"), daemon=True).start()
            enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟 Valoramos mucho tu opinión para seguir mejorando.\n\n_Escribe MENU para reiniciar._", nombre_mostrar)
            borrar_sesion(telefono)
        else: enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_mostrar)
        return

    # -- 3. CONTROL Y TIMEOUT --
    try:
        last_time = datetime.strptime(sesion.get("last_interaction", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        minutos_inactividad = (datetime.now() - last_time).total_seconds() / 60.0
    except: minutos_inactividad = 9999

    sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if texto_limpio == "STOP":
        marcar_stop(telefono); borrar_sesion(telefono)
        enviar_mensaje(telefono, "Listo. Has sido dado de baja. No recibirás más mensajes.\n\n*Crear Poder Sin Límites*", nombre_mostrar)
        return

    # Determinar qué menú principal usar según el ROL
    def get_main_key(rol):
        if rol == "IMO": return "main_imo"
        if rol == "PX": return "main_px"
        return "main_prospecto"
        
    main_key = get_main_key(perfil["rol"])

    # Función para renderizar menús con variables
    def render_menu(m_key):
        txt = MENU_STRUCTURE[m_key]["text"]
        if "{" in txt:
            txt = txt.format(
                nombre=perfil.get("nombre", "Participante"), 
                imo=perfil.get("imo_nombre", "tu líder"), 
                pendiente=perfil.get("pendiente", "tu entrenamiento")
            )
        return txt

    # Si se venció la sesión o es "MENU"
    if minutos_inactividad > 30 or "menu_state" not in sesion or texto_limpio in ["0", "MENU", "MENÚ", "INICIO"]:
        sesion["menu_state"] = main_key
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar)
        return

    if texto_limpio in ["9", "VOLVER", "ATRAS", "ATRÁS"]:
        hist = sesion.get("menu_history", [])
        if hist:
            prev = hist.pop()
            sesion["menu_state"] = prev
            sesion["menu_history"] = hist
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(prev), nombre_mostrar)
        else:
            sesion["menu_state"] = main_key
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar)
        return

    estado_actual = sesion.get("menu_state", main_key)

    # -- NAVEGACIÓN EN ÁRBOL --
    if estado_actual in MENU_STRUCTURE:
        nodo_actual = MENU_STRUCTURE[estado_actual]
        siguiente_estado = nodo_actual.get("options", {}).get(texto_limpio)
        
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            # --- ACCIONES CRM ESPECIALES ---
            if siguiente_estado == "px_confirma":
                # AUTO-UPDATE AL EXCEL DEL IMO!!!
                px_nombre = perfil["nombre"]
                imo_tel = perfil["imo_tel"]
                if imo_tel:
                    threading.Thread(target=actualizar_excel, args=([{"px": px_nombre, "estatus": "CONFIRMADO"}], imo_tel), daemon=True).start()
                
                msg_exito = f"¡Extraordinario, {px_nombre}! 🎉\n\nHemos registrado tu asistencia para tu próximo {perfil['pendiente']}. Le avisaremos automáticamente a tu líder {perfil['imo_nombre']} para que esté al tanto.\n\n_Escribe 0 para volver al menú._"
                enviar_mensaje(telefono, msg_exito, nombre_mostrar)
                sesion["menu_state"] = "esperando_fecha" # Estado neutro
                set_sesion(telefono, sesion)
                return

            elif siguiente_estado == "action_humano":
                coord_asignada = notificar_coordinadora_aleatoria(telefono, perfil["nombre"], f"Necesita asistencia desde la opción: {estado_actual}")
                enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{coord_asignada}*. Ella te escribirá por aquí en breve para apoyarte personalmente. 🚀\n\n_Escribe *0* si deseas cancelar y volver al menú._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return
                
            elif siguiente_estado == "action_salir":
                sesion["menu_state"] = "esperando_encuesta"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Antes de irte, ¿Cómo calificarías tu experiencia de hoy con nuestra *IA Cuántica*?\n\nResponde con un número del *1 al 5*:\n1️⃣ = Mala experiencia\n5️⃣ = ¡Excelente!", nombre_mostrar)
                return
                
            elif siguiente_estado == "main":
                # Redirige a su main correcto
                siguiente_estado = main_key
                
            # Transición normal
            hist = sesion.get("menu_history", [])
            if estado_actual != main_key and (not hist or hist[-1] != estado_actual):
                hist.append(estado_actual)
            
            sesion["menu_state"] = siguiente_estado
            sesion["menu_history"] = hist
            set_sesion(telefono, sesion)
            
            if siguiente_estado in MENU_STRUCTURE:
                enviar_mensaje(telefono, render_menu(siguiente_estado), nombre_mostrar)
            
            elif siguiente_estado == "chat_libre_ia":
                enviar_mensaje(telefono, "Has ingresado a nuestro *Chat Inteligente*. 🧠\nPuedes preguntarme lo que desees sobre nuestros entrenamientos, precios o metodologías.\n\n_Escribe *0* para salir del chat._", nombre_mostrar)
            
            elif siguiente_estado == "action_imo":
                enviar_mensaje(telefono, f"¡Hola líder! 👋\n\nHas ingresado al *Portal IMO*. Por favor, envíame un mensaje con el estatus de tus participantes pendientes para registrarlos en el Excel.\n\n_Escribe *0* para volver al menú._", nombre_mostrar)

        else:
            if not texto_limpio.isnumeric() and len(texto.split()) > 1:
                sesion["menu_state"] = "chat_libre_ia"
                set_sesion(telefono, sesion)
                resp_ia = embudo_ventas_ia(texto, perfil["nombre"])
                enviar_mensaje(telefono, resp_ia + "\n\n_(Escribe *0* en cualquier momento para volver al menú principal)_", nombre_mostrar)
                return

            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            if errores >= 3:
                sesion["menu_errors"] = 0
                c_nom = notificar_coordinadora_aleatoria(telefono, perfil["nombre"], "El usuario se atascó en el menú.")
                enviar_mensaje(telefono, f"Noto que estamos teniendo problemas. 🤖\nHe notificado a la coordinadora *{c_nom}* para que te asista de manera humana.\n\n_Escribe *0* para menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado_actual)}", nombre_mostrar)
            set_sesion(telefono, sesion)

    elif estado_actual == "action_imo":
        enviar_mensaje(telefono, f"Excelente líder. Has enviado tu estatus. Estamos procesándolo.\n\n_Escribe *0* para volver al menú._", nombre_mostrar)
        return
        
    elif estado_actual == "esperando_humano" or estado_actual == "esperando_fecha":
        set_sesion(telefono, sesion)
        return

    elif estado_actual == "chat_libre_ia":
        resp_ia = embudo_ventas_ia(texto, perfil["nombre"])
        enviar_mensaje(telefono, resp_ia, nombre_mostrar)
        return

# ══════════════════════════════════════════════════════════════════════════
# 9. PANEL WEB Y ENDPOINTS FLASK
# ══════════════════════════════════════════════════════════════════════════
HTML_CHAT = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel WhatsApp - Creación Cuántica</title>
    <style>
        :root { --primary: #008069; --bg-body: #d1d7db; --bg-chat: #efeae2; --chat-bubble-out: #d9fdd3; --text-dark: #111b21; --text-muted: #667781; --border: #e9edef; --panel-bg: #ffffff; }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; }
        body { background-color: var(--bg-body); color: var(--text-dark); height: 100vh; display: flex; justify-content: center; align-items: center; overflow: hidden; }
        .app-container { display: flex; width: 100%; max-width: 1400px; height: 95vh; background: var(--panel-bg); box-shadow: 0 6px 18px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
        .sidebar { width: 30%; min-width: 320px; border-right: 1px solid var(--border); display: flex; flex-direction: column; background: #ffffff; }
        .sidebar-header { background: #f0f2f5; padding: 15px 20px; font-weight: 600; font-size: 18px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 10px; }
        .header-top { display: flex; justify-content: space-between; align-items: center; width: 100%; }
        .header-actions { font-size:12px; font-weight:normal; display:flex; align-items:center; gap:8px; }
        .search-box { width: 100%; padding: 8px 12px; border-radius: 5px; border: 1px solid #ccc; outline: none; font-size: 14px; }
        .contacts-list { flex: 1; overflow-y: auto; }
        .contact-item { padding: 15px 20px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.2s; display: flex; align-items: center; }
        .contact-item:hover, .contact-item.active { background: #f0f2f5; }
        .avatar { width: 45px; height: 45px; background: #dfe5e7; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-size: 20px; flex-shrink: 0;}
        .contact-info { flex: 1; min-width: 0; }
        .contact-info h4 { margin-bottom: 4px; font-weight: 500; font-size:15px; color: #111b21;}
        .contact-info p { font-size: 13px; color: var(--text-muted); text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: var(--bg-chat); position: relative; }
        .chat-header { background: #f0f2f5; padding: 15px 25px; font-weight: 500; border-bottom: 1px solid var(--border); z-index: 1; display: flex; align-items: center; }
        .messages-container { flex: 1; padding: 30px; overflow-y: auto; z-index: 1; display: flex; flex-direction: column; scroll-behavior: smooth; }
        .message { max-width: 65%; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px; position: relative; font-size: 14.5px; line-height: 1.4; box-shadow: 0 1px 1px rgba(0,0,0,0.1); word-wrap: break-word; }
        .message.sent { align-self: flex-end; background: var(--chat-bubble-out); border-top-right-radius: 0; }
        .message.received { align-self: flex-start; background: #ffffff; border-top-left-radius: 0; }
        .message .time { font-size: 11px; color: var(--text-muted); float: right; margin-top: 5px; margin-left: 15px; }
        .chat-input-area { background: #f0f2f5; padding: 15px 25px; display: flex; align-items: center; z-index: 1; gap: 15px; }
        .chat-input-area textarea { flex: 1; border: none; padding: 12px 15px; border-radius: 8px; resize: none; outline: none; font-size: 15px; }
        .send-btn { background: var(--primary); color: white; border: none; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; flex-shrink:0; }
        .hidden { display: none !important; }
        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; z-index: 1; color: var(--text-muted); text-align: center; padding: 20px;}
        .sync-btn { background: #e9edef; border: 1px solid #ccc; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; }
        .download-btn { background: #00a884; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; text-decoration: none;}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <div class="header-top">
                    <div>💬 Panel V44 (CRM Master)</div>
                    <div class="header-actions">
                        <a href="/api/descargar_respaldo" class="download-btn">📥 Backup</a>
                        <button class="sync-btn" id="syncBtn" onclick="forceSync()">🔄 Excel</button>
                    </div>
                </div>
                <input type="text" id="searchBox" class="search-box" placeholder="🔍 Buscar nombre, número o mensaje..." onkeyup="filtrarChats()">
            </div>
            <div class="contacts-list" id="contactsList"></div>
        </div>
        <div class="chat-area" id="chatArea">
            <div class="empty-state" id="emptyState">
                <div style="font-size: 50px; margin-bottom: 20px;">🚀</div>
                <h2 style="color: #41525d; font-weight: 300;">Creación Cuántica Web</h2>
                <p style="margin-top: 10px; font-size:14px;">Selecciona un chat de la columna izquierda.</p>
            </div>
            <div class="chat-header hidden" id="chatHeader">
                <div class="avatar">👤</div>
                <h3 id="chatHeaderName" style="color: #111b21;"></h3>
            </div>
            <div class="messages-container hidden" id="messagesContainer"></div>
            <div class="chat-input-area hidden" id="chatInputArea">
                <textarea id="messageInput" rows="1" placeholder="Escribe tu respuesta aquí..."></textarea>
                <button class="send-btn" onclick="sendMessage()">Enviar</button>
            </div>
        </div>
    </div>
    <script>
        let chatHistory = {}; let activeContact = null;
        async function cargarDatos() {
            try {
                let res = await fetch('/api/historial'); let data = await res.json();
                let newHistory = {};
                for(let m of data) {
                    if (!newHistory[m.telefono]) newHistory[m.telefono] = { nombre: "", messages: [] };
                    if (m.nombre) newHistory[m.telefono].nombre = m.nombre;
                    newHistory[m.telefono].messages.push({ text: m.texto, time: m.hora, sent: m.tipo === 'out' });
                }
                chatHistory = newHistory; renderContacts(); if (activeContact) renderMessages();
            } catch (e) { }
        }
        
        function filtrarChats() {
            const query = document.getElementById("searchBox").value.toLowerCase();
            const items = document.querySelectorAll(".contact-item");
            items.forEach(item => {
                const searchData = item.getAttribute("data-search") || "";
                if (searchData.includes(query)) {
                    item.style.display = "flex";
                } else {
                    item.style.display = "none";
                }
            });
        }

        async function forceSync() {
            const btn = document.getElementById('syncBtn'); btn.classList.add('loading'); btn.innerText = "⏳...";
            try {
                await fetch('/api/force_sync', {method: 'POST'});
                setTimeout(async () => { await cargarDatos(); btn.classList.remove('loading'); btn.innerText = "🔄 Excel"; }, 4000);
            } catch(e) { btn.classList.remove('loading'); btn.innerText = "🔄 Excel"; }
        }

        function renderContacts() {
            const list = document.getElementById('contactsList'); list.innerHTML = '';
            const phones = Object.keys(chatHistory).reverse();
            if(phones.length === 0) { list.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">Cargando chats...</div>'; return; }
            phones.forEach(phone => {
                const contactData = chatHistory[phone]; 
                const lastMessage = contactData.messages[contactData.messages.length - 1].text;
                const displayName = contactData.nombre ? contactData.nombre : `+${phone}`;
                
                const allMessages = contactData.messages.map(m => m.text.toLowerCase()).join(" ");
                const searchStr = `${displayName.toLowerCase()} ${phone} ${allMessages}`.replace(/"/g, '');

                const div = document.createElement('div');
                div.className = `contact-item ${activeContact === phone ? 'active' : ''}`;
                div.onclick = () => openChat(phone, displayName);
                div.setAttribute("data-search", searchStr);
                
                div.innerHTML = `<div class="avatar">👤</div><div class="contact-info"><h4>${displayName}</h4><p>${lastMessage}</p></div>`;
                list.appendChild(div);
            });
            filtrarChats(); 
        }

        function openChat(phone, displayName) {
            activeContact = phone;
            document.getElementById('emptyState').classList.add('hidden'); 
            document.getElementById('chatHeader').classList.remove('hidden');
            document.getElementById('messagesContainer').classList.remove('hidden'); 
            document.getElementById('chatInputArea').classList.remove('hidden');
            document.getElementById('chatHeaderName').innerHTML = `${displayName} <span style="font-size:12px; color:#888; margin-left:10px;">(+${phone})</span>`;
            renderContacts(); renderMessages();
        }

        function renderMessages() {
            const container = document.getElementById('messagesContainer'); container.innerHTML = '';
            if (!activeContact || !chatHistory[activeContact]) return;
            chatHistory[activeContact].messages.forEach(msg => {
                const div = document.createElement('div'); div.className = `message ${msg.sent ? 'sent' : 'received'}`;
                div.innerHTML = `${msg.text.replace(/\\n/g, '<br>')}<span class="time">${msg.time}</span>`;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const textarea = document.getElementById('messageInput'); const mensaje = textarea.value.trim(); const destino = activeContact;
            if (!mensaje || !destino) return;
            textarea.value = '';
            chatHistory[destino].messages.push({ text: mensaje, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}), sent: true });
            renderMessages(); renderContacts();
            try {
                await fetch('/api/enviar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ telefono: destino, mensaje: mensaje }) });
                cargarDatos();
            } catch (error) { alert("Error de conexión"); }
        }
        setInterval(cargarDatos, 3000); cargarDatos();
    </script>
</body>
</html>
"""

@app.route("/chat", methods=["GET"])
def panel_chat(): return HTML_CHAT

@app.route("/api/historial", methods=["GET"])
def api_historial(): return jsonify(get_historial()), 200

@app.route("/api/force_sync", methods=["POST"])
def force_sync():
    threading.Thread(target=forzar_sincronizacion_sheets, daemon=True).start()
    return jsonify({"status": "syncing"}), 200

@app.route("/api/descargar_respaldo", methods=["GET"])
def descargar_respaldo():
    h = get_historial()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Telefono", "Nombre IMO", "Tipo Mensaje", "Texto"])
    for m in h:
        tipo_str = "Bot/Panel envió" if m.get("tipo") == "out" else "Contacto respondió"
        writer.writerow([m.get("hora", ""), m.get("telefono", ""), m.get("nombre", ""), tipo_str, m.get("texto", "")])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=Respaldo_Chats.csv"})

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    data = request.json; tel = data.get("telefono"); msg = data.get("mensaje")
    if tel and msg:
        sesion = get_sesion(tel)
        perfil = sesion.get("perfil")
        if not perfil: perfil = obtener_perfil_crm(tel)
        nombre_mostrar = f"({perfil['rol']}) {perfil['nombre']}" if perfil['nombre'] else "NUEVO CONTACTO"
        
        WhatsAppAPI.enviar_mensaje(tel, msg, nombre_mostrar, registrar_sheets=True, mensaje_usuario="[ENVIADO DESDE PANEL PRIVADO]")
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Faltan datos"}), 400

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode, token, challenge = (request.args.get(k) for k in ["hub.mode","hub.verify_token","hub.challenge"])
    if mode == "subscribe" and token == Config.VERIFY_TOKEN: return challenge, 200
    return "Token invalido", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json(silent=True)
    if not data: return jsonify({"status":"ok"}), 200
    try:
        changes = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        if "messages" not in changes: return jsonify({"status":"ok"}), 200
        
        msg = changes["messages"][0]
        telefono = msg.get("from")
        tipo = msg.get("type", "")
        
        if tipo == "text":
            texto = msg["text"]["body"]
            texto = str(texto).replace("=", "").replace("+", "").replace("@", "")
            
            # Guardado y envío al procesador
            procesar_mensaje(telefono, texto, None)
            
            # Recuperamos el perfil ya procesado para guardarlo en el historial
            sesion = get_sesion(telefono)
            perfil = sesion.get("perfil", {})
            nombre_mostrar = f"({perfil.get('rol', 'PROSPECTO')}) {perfil.get('nombre', 'Nuevo')}" if perfil.get('nombre') else "NUEVO CONTACTO"
            
            append_historial(telefono, nombre_mostrar, texto, "in")

        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.", "")
    except Exception as e: 
        logger.error(f"Error crítico en Webhook: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): 
    return jsonify({
        "status": "activo", "version": "v44_crm_omnicanal",
        "gemini": "disponible" if GEMINI_DISPONIBLE else "no instalado",
        "qwen": "disponible" if QWEN_DISPONIBLE else "no instalado"
    }), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando bot en puerto {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
