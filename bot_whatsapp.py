"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
✅ Versión V37: Buscador Omnisciente en Panel Web, Carga Masiva (10k) y Sync Total
"""

import os, re, json, threading, time, csv, io, random, logging
from flask import Flask, request, jsonify, Response
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock
from http import HTTPStatus

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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
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
# 2. GESTOR DE ESTADO CONCURRENTE (SISTEMA DE BACKUP MASIVO)
# ══════════════════════════════════════════════════════════════════════════
class SessionManager:
    _session_lock = threading.Lock()
    _history_lock = threading.Lock()

    @staticmethod
    def get_sesion(telefono):
        with SessionManager._session_lock:
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        return data.get(str(telefono), {})
            except Exception as e:
                logger.error(f"Error leyendo sesiones: {e}")
            return {}

    @staticmethod
    def set_sesion(telefono, data_dict):
        with SessionManager._session_lock:
            try:
                data = {}
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                data[str(telefono)] = data_dict
                with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error guardando sesión: {e}")

    @staticmethod
    def borrar_sesion(telefono):
        tel_str = str(telefono)
        with SessionManager._session_lock:
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if tel_str in data:
                        del data[tel_str]
                        with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error borrando sesión: {e}")

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        with SessionManager._history_lock:
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
                # Carga Masiva: Guarda hasta 10,000 mensajes
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f:
                    json.dump(h[-10000:], f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error escribiendo en historial: {e}")

    @staticmethod
    def forzar_sincronizacion(leer_sheet_func, norm_tel_func):
        """Restaura el historial completo desde Google Sheets"""
        with SessionManager._history_lock:
            try:
                local_hist = []
                if os.path.exists(Config.HISTORIAL_PATH):
                    with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                        local_hist = json.load(f)
                        
                existing = set(f"{m.get('telefono','')}_{m.get('texto','')}" for m in local_hist)
                rows = leer_sheet_func()
                
                if rows:
                    for row in rows[1:]:
                        if len(row) < 4: continue
                        hora = str(row[0]).strip(); tel = norm_tel_func(str(row[1]).strip())
                        imo_n = str(row[2]).strip() if len(row) > 2 else ""
                        msg_in, msg_out = "", ""
                        if len(row) > 3: msg_in  = str(row[3]).strip()
                        if len(row) > 4: msg_out = str(row[4]).strip()
                        
                        if tel:
                            if msg_in and f"{tel}_{msg_in}" not in existing:
                                local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_in, "tipo": "in", "hora": hora})
                                existing.add(f"{tel}_{msg_in}")
                            if msg_out and f"{tel}_{msg_out}" not in existing:
                                local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_out, "tipo": "out", "hora": hora})
                                existing.add(f"{tel}_{msg_out}")
                    
                    # Ordenar cronológicamente y guardar
                    with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: 
                        json.dump(local_hist[-10000:], f, ensure_ascii=False, indent=2) 
            except Exception as e:
                logger.error(f"Error restaurando Backup de Sheets: {e}")

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
# 3. CONECTORES DE API (WhatsApp y Google Sheets Anti-Pérdida)
# ══════════════════════════════════════════════════════════════════════════
class WhatsAppAPI:
    @staticmethod
    def enviar_mensaje(telefono, texto, nombre_mostrar="", registrar_sheets=False, mensaje_usuario=""):
        url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp", "to": str(telefono), "type": "text",
            "text": {"body": texto, "preview_url": False}
        }
        try:
            r = req_lib.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                SessionManager.append_historial(telefono, nombre_mostrar, texto, "out")
                
                if registrar_sheets:
                    sesion = get_sesion(telefono)
                    ultimo_msg = sesion.get("ultimo_mensaje_usuario", mensaje_usuario or "[Bot Autónomo]")
                    estado_actual = sesion.get("menu_state", "BOT")
                    
                    threading.Thread(
                        target=registrar_en_sheets, 
                        args=(telefono, nombre_mostrar, ultimo_msg, texto[:500], estado_actual),
                        daemon=True
                    ).start()
                return True
        except Exception as e:
            logger.error(f"Fallo al enviar mensaje a {telefono}: {e}")
        return False

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=False, msg_user=""):
    sesion = get_sesion(telefono)
    if sesion.get("primera_vez", True) and not str(nombre_imo).startswith("COORDINADORA"):
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
            if cls._token_cache["token"] and now < cls._token_cache["exp"] - 60:
                return cls._token_cache["token"]
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
            except Exception as e: logger.error(f"Error generando JWT Sheets: {e}")
            return None

    @classmethod
    def registrar_accion(cls, telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
        if not Config.SHEET_ID: return
        token = cls.get_token()
        if not token: return
        url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H:append"
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        try:
            req_lib.post(url, 
                params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, 
                json={"values": [[ahora, str(telefono), imo_nombre, mensaje, respuesta_bot, estado, "", ""]]}, 
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        except Exception as e: logger.error(f"Error guardando en Sheets: {e}")
            
    @classmethod
    def leer_sheet(cls):
        if not Config.SHEET_ID: return []
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
# 4. DATOS MAESTROS Y MENÚS
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
- Opciones de Pago e Inversión: BCP Soles a nombre de CREACIÓN CUÁNTICA E.I.R.L (Cuenta: 1934218307060 / CCI: 00219300421830706018). Se acepta PayPal, Efectivo y tarjetas de crédito.
"""

MENU_STRUCTURE = {
    "main": {
        "text": (
            "🌟 *Bienvenido a Crear Poder Sin Límites Perú* 🌟\n\n"
            "Soy *IA Cuántica*, tu asistente virtual. Es un honor acompañarte hacia tu siguiente nivel de liderazgo y transformación.\n\n"
            "Para brindarte una experiencia ágil y precisa, responde con el *número* de la opción que buscas hoy:\n\n"
            "1️⃣ *Explorar Entrenamientos* (C1, C2 y Maestría)\n"
            "2️⃣ *Acceso para Líderes* (Gestión exclusiva IMO)\n"
            "3️⃣ *Soporte a Participantes* (Acompañamiento)\n"
            "4️⃣ *Estado de mi Matrícula* (Revisar tu proceso)\n"
            "5️⃣ *Inversión y Pagos* (Modalidades y cuentas)\n"
            "6️⃣ *Atención Personalizada* (Contactar a una coordinadora)\n"
            "7️⃣ *Hablar con IA Cuántica* (Chat libre, resolvemos dudas)\n"
            "8️⃣ *Finalizar sesión*"
        ),
        "options": {
            "1": "info_entrenamientos", "2": "action_imo", "3": "soporte_participante", 
            "4": "estado_proceso", "5": "pagos", "6": "action_humano", "7": "chat_libre_ia", "8": "action_salir"
        }
    },
    "info_entrenamientos": {
        "text": (
            "📘 *Explorar Entrenamientos*\n"
            "Selecciona el entrenamiento sobre el que deseas descubrir más:\n\n"
            "1️⃣ Capítulo 1 (C1) - El inicio del viaje\n"
            "2️⃣ Capítulo 2 (C2) - Transformación profunda\n"
            "3️⃣ Maestría (MJ) - Liderazgo de 100 días\n"
            "4️⃣ Fechas y lugares de próximos eventos\n\n"
            "9️⃣ Regresar al paso anterior\n"
            "0️⃣ Volver al menú principal"
        ),
        "options": {"1": "info_c1", "2": "info_c2", "3": "info_mj", "4": "info_fechas", "9": "volver", "0": "main"}
    },
    "info_c1": {
        "text": (
            "🚀 *Capítulo 1 (C1)*: Es la fase de Descubrimiento. Un entrenamiento vivencial de 3 días diseñado para romper paradigmas y empezar a crear resultados excepcionales.\n\n"
            "Escribe *1* si deseas contactar a un asesor para dar tu primer paso.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": (
            "🔥 *Capítulo 2 (C2)*: Experiencia y Transformación profunda. Usualmente son 4 días inmersivos diseñados para rediseñar tu forma de relacionarte con el mundo.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": (
            "👑 *Maestría (MJ)*: El nivel donde el liderazgo se lleva a la acción. 100 días de entrenamiento continuo para crear hábitos inquebrantables.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": (
            "📅 *Fechas y Lugares*\nNuestra sede principal en Perú es el Hotel José Antonio Deluxe (Miraflores, Lima). Para darte la fecha exacta del próximo entrenamiento:\n\n"
            "1️⃣ Solicitar calendario a una coordinadora\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "soporte_participante": {
        "text": (
            "👤 *Soporte y Acompañamiento*\n¿Qué necesitas hoy?\n\n"
            "1️⃣ Tengo dudas sobre mi asistencia o fechas asignadas\n"
            "2️⃣ Requisitos y qué llevar al salón\n"
            "3️⃣ Realizar una consulta a un humano\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "2": "requisitos_salon", "3": "action_humano", "9": "volver", "0": "main"}
    },
    "requisitos_salon": {
        "text": (
            "🎒 *Requisitos para el Salón*\nTe sugerimos llevar ropa muy cómoda y una botella de agua para hidratarte. No necesitas cuadernos ni apuntes. No se permiten alimentos externos y el entrenamiento es exclusivo para mayores de 18 años.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "estado_proceso": {
        "text": (
            "📊 *Estado de mi Matrícula*\nPara revisar el estatus exacto de tu matrícula o reprogramaciones, necesitamos que una coordinadora verifique tu DNI en nuestro sistema seguro.\n\n"
            "1️⃣ Solicitar revisión a coordinadora\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": (
            "💳 *Inversión y Pagos*\nAceptamos pagos por transferencia al BCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060), tarjetas de crédito y PayPal.\n\n"
            "1️⃣ Enviar voucher de pago a Coordinadora\n"
            "2️⃣ Necesito ayuda con mi factura/boleta\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "2": "action_humano", "9": "volver", "0": "main"}
    }
}

def obtener_necesidad(estado_actual, texto_limpio, texto_original):
    if estado_actual == "main" and texto_limpio == "6": return "Atención personalizada general"
    if estado_actual == "info_c1" and texto_limpio == "1": return "Desea inscribirse o contactar a un asesor para el Capítulo 1"
    if estado_actual == "info_fechas" and texto_limpio == "1": return "Solicita calendario de fechas de próximos entrenamientos"
    if estado_actual == "soporte_participante" and texto_limpio == "1": return "Tiene dudas sobre su asistencia o fechas asignadas"
    if estado_actual == "soporte_participante" and texto_limpio == "3": return "Desea realizar una consulta general de soporte"
    if estado_actual == "estado_proceso" and texto_limpio == "1": return "Solicita revisión de su matrícula / Validación de DNI"
    if estado_actual == "pagos" and texto_limpio == "1": return "Desea enviar un voucher de pago"
    if estado_actual == "pagos" and texto_limpio == "2": return "Necesita ayuda con facturación o boletas"
    if estado_actual == "chat_libre_ia" and texto_limpio == "3": return "Solicitó un humano tras conversar con la IA"
    return f"Motivo no especificado. Último mensaje: '{texto_original}'"

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
    nombre_mostrar_coord = f"COORDINADORA: {coord_nombre}"
    enviar_mensaje(coord_tel, msg_coord, nombre_mostrar_coord)
    return coord_nombre

# ══════════════════════════════════════════════════════════════════════════
# 5. UTILIDADES Y CARGA DE EXCEL
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
    lock = FileLock(Config.EXCEL_PATH + ".lock")
    with lock:
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

def marcar_stop(telefono):
    tel_n = norm_tel(telefono)
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                if norm_tel(str(row[3].value or "")) == tel_n: 
                    row[6].value = "STOP"
                    row[7].value = hoy
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

# ══════════════════════════════════════════════════════════════════════════
# 6. ESTRATEGIA DE IA DUAL (GEMINI + QWEN)
# ══════════════════════════════════════════════════════════════════════════
def embudo_ventas_ia(mensaje_usuario, nombre_conocido=None, nombre_ya_saludado=False):
    cfg = {"gemini_key": Config.GEMINI_KEY, "dashscope_key": Config.DASHSCOPE_KEY, "modo_ia": Config.MODO_IA, "ia_primaria": Config.IA_PRIMARIA, "ia_fallback": Config.IA_FALLBACK}
    msg_len = len(mensaje_usuario.split())
    
    def respuesta_del_banco(mensaje):
        msg_norm = normalizar(mensaje)
        if msg_len <= 3 and nombre_conocido and not nombre_ya_saludado:
            return f"¡Hola, {nombre_conocido}! Creemos firmemente que tienes un potencial ilimitado esperando ser despertado.\n\nA través de metodologías vivenciales, te acompañamos a romper las barreras que te frenan. Todo esto lo vives en el *Capítulo 1*, un entrenamiento intensivo de 3 días para transformar tu realidad. ¿Te gustaría conocer la fecha de nuestro próximo entrenamiento?"
            
        banco_preguntas = [
            (["100 dias", "cuanto dura", "duracion", "el proceso"], "Creemos en transformaciones reales. Por eso el proceso completo dura 100 días, donde con el apoyo de tu equipo integrarás lo aprendido a tu vida cotidiana, creando hábitos inquebrantables."),
            (["edad", "niños", "menores", "jovenes", "adolescentes", "18"], "Creemos en el potencial a toda edad, pero este formato está diseñado exclusivamente para mayores de 18 años. Si buscas espacios para menores, por favor escribe el número *3* y te apoyaremos."),
            (["terapia", "psicologo", "depresion", "sanar", "salud mental", "arreglar"], "Es vital aclarar que nuestro enfoque es de alto rendimiento. NO somos un centro de terapia ni sustituimos procesos de salud mental. Nos enfocamos en empoderarte para crear una nueva realidad a partir de hoy."),
            (["precio", "costo", "cuanto cuesta", "pagar", "inversion", "cuenta", "banco", "transferencia", "bcp"], "Aceptamos pagos por transferencia al BCP a nombre de Creación Cuántica E.I.R.L. (Cuenta: 1934218307060), tarjetas de crédito y PayPal. ¿Te gustaría realizar la reserva de tu espacio ahora mismo?"),
            (["que es", "de que trata", "que hacen", "para que sirve", "informacion", "beneficios", "capitulo 1", "crear"], "El Capítulo 1 es un modelo de coaching de alto rendimiento. Es un entrenamiento vivencial de 3 días diseñado para desarrollar nuevas formas de pensamiento, gestión emocional y descubrir las barreras que te limitan en tu vida actual. ¿Estás listo para dar este salto?"),
            (["horario", "hora", "cuando empieza", "cuando termina", "dias", "fechas", "agenda"], f"Tu transformación requiere compromiso total. El proceso inmersivo de 3 días en el Hotel José Antonio Deluxe inicia este viernes a las 9:00 am y cierra el domingo por la noche (9:00 pm aproximadamente)."),
            (["donde", "lugar", "direccion", "ubicacion", "hotel", "distrito", "sede"], f"Nuestra sede principal en Perú se encuentra en el Hotel José Antonio Deluxe, ubicado en Calle Bellavista 133, Miraflores, Lima. También contamos con sedes en Colombia, Ecuador y México."),
            (["ropa", "vestimenta", "que llevar", "llevar", "frio", "calor"], "Te sugerimos llevar ropa muy cómoda y una botella de agua para hidratarte. Todo lo demás lo ponemos nosotros en el salón."),
            (["comida", "almuerzo", "refrigerio", "comer", "desayuno", "cena", "snacks"], "No se permiten alimentos ni bebidas externas al salón. Contaremos con los tiempos adecuados para que puedas salir a almorzar y compartir por la zona."),
            (["coordinadora", "asesor", "humano", "persona", "llamar", "contactar", "hablar", "queja"], "Para brindarte un apoyo 100% personalizado con una coordinadora humana, por favor responde únicamente con el número *3*.")
        ]
        
        for palabras_clave, respuesta in banco_preguntas:
            if any(kw in msg_norm for kw in palabras_clave):
                return respuesta
        
        if nombre_conocido: return f"¡Comprendido, {nombre_conocido}! Para resolver tu consulta a detalle sobre nuestro proceso, por favor responde con el número *3* y una coordinadora se comunicará contigo."
        else: return f"En Crear Poder Sin Límites creemos en acompañarte hacia tu mejor versión. Para apoyarte de forma humana y precisa, responde con el número *3* para enlazarte con una coordinadora."

    def construir_prompt_gemini():
        return f"""
        Eres un Asesor Experto y Resolutivo de 'Crear Poder Sin Límites Perú'.
        Un contacto acaba de escribir: "{mensaje_usuario}"
        Contexto: Su nombre es: "{nombre_conocido if nombre_conocido else 'Desconocido'}".
        INFORMACIÓN OFICIAL:
        {BROCHURE_INFO_MAESTRA}
        Reglas:
        1. Responde basándote en la información oficial. Da precios, cuentas o duración de 100 días si preguntan.
        2. NO derives a la coordinadora a menos que pidan hablar con un humano.
        3. Si YA SABES el nombre, úsalo. Si no, pregúntalo cordialmente.
        4. CERO rastros de IA. Eres humano.
        5. BREVEDAD: Responde en máximo 3 oraciones y termina con una pregunta persuasiva.
        """

    def construir_prompt_qwen():
        return [
            {"role": "system", "content": "Eres un Asesor Experto de 'Crear Poder Sin Límites Perú'. Responde usando SOLO el brochure oficial. Eres humano, directo y empático. Máximo 3 oraciones."},
            {"role": "user", "content": f"Contacto: {nombre_conocido if nombre_conocido else 'No registrado'}\nMensaje: '{mensaje_usuario}'\nBrochure:\n{BROCHURE_INFO_MAESTRA}\nResponde:"}
        ]

    def llamar_gemini():
        if not GEMINI_DISPONIBLE or not cfg.get("gemini_key"): return None, "gemini_no_configurado"
        try:
            genai.configure(api_key=cfg["gemini_key"])
            model = genai.GenerativeModel('gemini-2.0-flash') 
            response = model.generate_content(construir_prompt_gemini())
            if response.text and response.text.strip(): return response.text.strip(), None
        except Exception as e: return None, f"gemini_error:{str(e)[:100]}"
        return None, "gemini_sin_respuesta"

    def llamar_qwen():
        if not QWEN_DISPONIBLE or not cfg.get("dashscope_key"): return None, "qwen_no_configurado"
        try:
            response = Generation.call(model="qwen-turbo", messages=construir_prompt_qwen(), api_key=cfg["dashscope_key"], result_format="message", max_tokens=500, temperature=0.7)
            if response.status_code == HTTPStatus.OK and response.output and response.output.choices:
                respuesta = response.output.choices[0].message.content.strip()
                respuesta = re.sub(r'\*\*IA.*?\*\*|<\|.*?\|>|\[.*?\]', '', respuesta)
                return respuesta, None
        except Exception as e: return None, f"qwen_error:{str(e)[:100]}"
        return None, "qwen_sin_respuesta"

    if cfg.get("modo_ia", "fallback") == "routing":
        msg_norm = normalizar(mensaje_usuario)
        if any(kw in msg_norm for kw in ["precio", "costo", "cuenta", "bcp", "donde", "lugar", "hora", "fecha"]):
            return respuesta_del_banco(mensaje_usuario) 
    
    modelo_primario = "qwen" if cfg.get("modo_ia") == "ab_test" and hash(mensaje_usuario) % 2 == 0 else cfg.get("ia_primaria", "qwen")
    modelo_fallback = cfg.get("ia_fallback", "gemini" if modelo_primario == "qwen" else "qwen")
    
    respuesta, error = llamar_gemini() if modelo_primario == "gemini" else llamar_qwen()
    if not respuesta: respuesta, error = llamar_gemini() if modelo_fallback == "gemini" else llamar_qwen()
    if not respuesta: return respuesta_del_banco(mensaje_usuario)
    return respuesta

# ══════════════════════════════════════════════════════════════════════════
# 7. PROCESADOR PRINCIPAL DE MENSAJES (MÁQUINA DE ESTADOS)
# ══════════════════════════════════════════════════════════════════════════
def procesar_mensaje(telefono, texto, imo_nombre_completo):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    
    nombre_mostrar = imo_nombre_completo
    if not imo_nombre_completo:
        nm = sesion.get("nombre_prospecto")
        if not nm and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric() and sesion.get("menu_state") != "esperando_encuesta":
            nm = nombre_pila(texto)
            sesion["nombre_prospecto"] = nm
        nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"

    # -- INTERCEPTOR ENCUESTA CSAT --
    if sesion.get("menu_state") == "esperando_encuesta":
        if texto_limpio in ["1", "2", "3", "4", "5"]:
            threading.Thread(target=registrar_en_sheets, args=(telefono, nombre_mostrar, "Calificación del Asistente", f"{texto_limpio} Estrellas", "ENCUESTA CSAT"), daemon=True).start()
            enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟 Valoramos mucho tu opinión para seguir mejorando.\n\nQue tengas un día extraordinario. ✨\n\n_Si deseas iniciar una nueva consulta en cualquier momento, solo escribe la palabra MENU._", nombre_mostrar)
            borrar_sesion(telefono)
        else: enviar_mensaje(telefono, "Por favor, para finalizar califica respondiendo *únicamente con un número del 1 al 5*.", nombre_mostrar)
        return

    # -- TIMEOUT --
    try:
        if sesion.get("last_interaction"):
            last_time = datetime.strptime(sesion.get("last_interaction"), "%Y-%m-%d %H:%M:%S")
            minutos_inactividad = (datetime.now() - last_time).total_seconds() / 60.0
        else: minutos_inactividad = 9999
    except: minutos_inactividad = 9999

    sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if texto_limpio == "STOP":
        marcar_stop(telefono); borrar_sesion(telefono)
        enviar_mensaje(telefono, "Listo. Has sido dado de baja de este canal. No recibirás más mensajes.\n\n*Crear Poder Sin Límites*", nombre_mostrar)
        return

    if minutos_inactividad > 30 or "menu_state" not in sesion:
        sesion["menu_state"] = "main"
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        sesion["nombre_saludado"] = False
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    if texto_limpio in ["0", "MENU", "MENÚ", "INICIO"]:
        sesion["menu_state"] = "main"
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        sesion["estado_secundario"] = None 
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    if texto_limpio in ["9", "VOLVER", "ATRAS", "ATRÁS"]:
        history = sesion.get("menu_history", [])
        if history:
            prev_state = history.pop() 
            sesion["menu_state"] = prev_state
            sesion["menu_history"] = history
            sesion["menu_errors"] = 0
            sesion["estado_secundario"] = None
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, MENU_STRUCTURE[prev_state]["text"], nombre_mostrar)
        else:
            sesion["menu_state"] = "main"
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    estado_actual = sesion.get("menu_state", "main")

    # -- NAVEGACIÓN DEL MENÚ --
    if estado_actual in MENU_STRUCTURE:
        nodo_actual = MENU_STRUCTURE[estado_actual]
        siguiente_estado = nodo_actual.get("options", {}).get(texto_limpio)
        
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            if siguiente_estado == "action_humano":
                nm = sesion.get("nombre_prospecto")
                necesidad = obtener_necesidad(estado_actual, texto_limpio, texto)
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, necesidad)
                enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{coord_asignada}*. Ella te escribirá por aquí en breve para apoyarte personalmente. 🚀\n\n_Escribe *0* si deseas cancelar y volver al menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return
                
            elif siguiente_estado == "action_salir":
                sesion["menu_state"] = "esperando_encuesta"
                set_sesion(telefono, sesion)
                msg_encuesta = ("Antes de irte, nos encantaría saber cómo te fue. 🤖\n\n¿Cómo calificarías tu experiencia de hoy con nuestra *IA Cuántica*?\n\nResponde con un número del *1 al 5*:\n\n1️⃣ = Mala experiencia\n5️⃣ = ¡Excelente, me apoyó rápido!")
                enviar_mensaje(telefono, msg_encuesta, nombre_mostrar)
                return
                
            elif siguiente_estado == "volver":
                pass 
                
            else:
                historial = sesion.get("menu_history", [])
                if estado_actual != "main" and (not historial or historial[-1] != estado_actual):
                    historial.append(estado_actual)
                
                sesion["menu_state"] = siguiente_estado
                sesion["menu_history"] = historial
                set_sesion(telefono, sesion)
                
                if siguiente_estado in MENU_STRUCTURE:
                    enviar_mensaje(telefono, MENU_STRUCTURE[siguiente_estado]["text"], nombre_mostrar)
                
                elif siguiente_estado == "chat_libre_ia":
                    enviar_mensaje(telefono, "Has ingresado a nuestro *Chat Inteligente*. 🧠\n\nPuedes preguntarme lo que desees sobre nuestros entrenamientos, precios, fechas o metodologías.\n\n_Escribe *0* para salir del chat y volver al menú._", nombre_mostrar)
                
                elif siguiente_estado == "action_imo":
                    _, px_list = cargar_px_del_imo(telefono)
                    if px_list: enviar_mensaje(telefono, f"¡Hola líder! 👋\n\nHas ingresado al *Portal IMO*. Por favor, envíame un mensaje con el estatus de tus participantes pendientes para registrarlos.\n\n_Escribe *0* para volver al menú._", nombre_mostrar)
                    else:
                        sesion["menu_state"] = "main"
                        set_sesion(telefono, sesion)
                        enviar_mensaje(telefono, "⚠️ Nuestro sistema indica que actualmente no tienes participantes pendientes vinculados a este número.\n\n_Si crees que esto es un error, selecciona la opción *6* en el menú para hablar con una coordinadora._", nombre_mostrar)
                        time.sleep(1)
                        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)

        else:
            # SMART ROUTING: Entiende que quiere chatear libremente si escribe frases largas
            if not texto_limpio.isnumeric() and len(texto.split()) > 1:
                sesion["menu_state"] = "chat_libre_ia"
                set_sesion(telefono, sesion)
                
                nombre_guardado = sesion.get("nombre_prospecto")
                nombre_ya_saludado = sesion.get("nombre_saludado", False)
                respuesta_embudo = embudo_ventas_ia(texto, nombre_guardado, nombre_ya_saludado)
                
                if nombre_guardado and not nombre_ya_saludado and "potencial ilimitado" in respuesta_embudo:
                    sesion["nombre_saludado"] = True
                    set_sesion(telefono, sesion)
                
                enviar_mensaje(telefono, respuesta_embudo + "\n\n_(Escribe *0* en cualquier momento para volver al menú principal)_", nombre_mostrar)
                return

            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            
            if errores >= 3:
                sesion["menu_errors"] = 0
                nm = sesion.get("nombre_prospecto")
                necesidad = f"El usuario se atascó en el menú enviando múltiples respuestas inválidas. Último intento: '{texto}'"
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, necesidad)
                enviar_mensaje(telefono, f"Noto que estamos teniendo problemas de comunicación. 🤖\n\nNo te preocupes, he notificado a nuestra coordinadora *{coord_asignada}* para que te asista personalmente de manera humana.\n\n_Escribe *0* si prefieres volver a ver el menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                msg_error = f"⚠️ *Opción no válida*. Por favor, responde únicamente con el *número* (ej. 1, 2, 3) de la opción que deseas explorar.\n\n{nodo_actual['text']}"
                enviar_mensaje(telefono, msg_error, nombre_mostrar)
                
            set_sesion(telefono, sesion)

    elif estado_actual == "action_imo":
        enviar_mensaje(telefono, f"Excelente líder. Has enviado tu estatus. Estamos procesándolo.\n\n_Escribe *0* para volver al menú._", nombre_mostrar)
        return
        
    elif estado_actual == "esperando_humano":
        set_sesion(telefono, sesion)
        return

    elif estado_actual == "chat_libre_ia":
        if texto_limpio == "3":
            necesidad = "Solicitó un humano tras conversar libremente con la IA."
            coord_asignada = notificar_coordinadora_aleatoria(telefono, sesion.get("nombre_prospecto"), necesidad)
            enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{coord_asignada}*. Ella te escribirá por aquí en breve para apoyarte personalmente. 🚀\n\n_Escribe *0* si deseas cancelar y volver al menú principal._", nombre_mostrar)
            sesion["menu_state"] = "esperando_humano"
            set_sesion(telefono, sesion)
            return

        nombre_guardado = sesion.get("nombre_prospecto")
        nombre_ya_saludado = sesion.get("nombre_saludado", False)
        
        if not nombre_guardado and len(texto.split()) <= 3 and len(texto) > 2 and not nombre_ya_saludado:
            sesion["nombre_prospecto"] = nombre_pila(texto)
            nombre_guardado = sesion["nombre_prospecto"]
            
        respuesta_embudo = embudo_ventas_ia(texto, nombre_guardado, nombre_ya_saludado)
        if nombre_guardado and not nombre_ya_saludado and "potencial ilimitado esperando ser despertado" in respuesta_embudo:
            sesion["nombre_saludado"] = True
            
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, respuesta_embudo, nombre_mostrar)
        return

# ══════════════════════════════════════════════════════════════════════════
# 8. PANEL WEB (BUSCADOR INTELIGENTE) Y ENDPOINTS
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
                    <div>💬 Panel V37</div>
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
                
                // DATA PARA EL BUSCADOR OMNISCIENTE
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
        imo_nombre, _ = cargar_px_del_imo(tel)
        if not imo_nombre: 
            sesion = get_sesion(tel)
            nm = sesion.get("nombre_prospecto")
            imo_nombre = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"
        WhatsAppAPI.enviar_mensaje(tel, msg, imo_nombre, registrar_sheets=True, mensaje_usuario="[ENVIADO DESDE PANEL PRIVADO]")
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
            
            sesion_pre = get_sesion(telefono)
            sesion_pre["ultimo_mensaje_usuario"] = texto
            set_sesion(telefono, sesion_pre)
            
            imo_nombre_sheet, _ = cargar_px_del_imo(telefono)
            nombre_mostrar = imo_nombre_sheet
            
            if not imo_nombre_sheet:
                nm = sesion_pre.get("nombre_prospecto")
                nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"
            
            append_historial(telefono, nombre_mostrar, texto, "in")
            procesar_mensaje(telefono, texto, imo_nombre_sheet)

        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.", "")
    except Exception as e: 
        logger.error(f"Error crítico en Webhook: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): 
    return jsonify({
        "status": "activo", 
        "version": "v37_buscador_omnisciente_10k",
        "gemini": "disponible" if GEMINI_DISPONIBLE else "no instalado",
        "qwen": "disponible" if QWEN_DISPONIBLE else "no instalado"
    }), 200

threading.Thread(target=forzar_sincronizacion_sheets, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando bot en puerto {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
