"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
v28 MAGISTRAL — Menú Jerárquico Avanzado (Tipo Corporativo)
"""

import os, re, json, threading, time, csv, io, random
from flask import Flask, request, jsonify, Response
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock

try:
    from google import genai
except ImportError:
    genai = None

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACION Y UTILIDADES
# ══════════════════════════════════════════════════════════════════════════

def get_config():
    return {
        "token":         os.environ.get("WA_TOKEN", ""),
        "phone_id":      os.environ.get("WA_PHONE_ID", ""),
        "verify_token":  os.environ.get("WA_VERIFY_TOKEN", "cpsl2026"),
        "excel_path":    os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx"),
        "jose_tel":      os.environ.get("JOSE_LUIS_TEL", ""),
        "sessions_path": os.environ.get("SESSIONS_PATH", "sesiones.json"),
        "gemini_key":    os.environ.get("GEMINI_API_KEY", ""), 
    }

def api_url(): return f"https://graph.facebook.com/v19.0/{get_config()['phone_id']}/messages"
_excel_lock = threading.Lock()

def norm_tel(tel):
    t = str(tel).strip().replace("+","").replace(" ","").replace("-","")
    if t.startswith("51") and len(t) == 11: t = t[2:]
    elif t.startswith("0") and len(t) == 10: t = t[1:]
    elif len(t) > 10 and not t.startswith("9"): t = t[-9:]
    return t

def ep(): return get_config()["excel_path"]

# ══════════════════════════════════════════════════════════════════════════
# 2. GOOGLE SHEETS CORE
# ══════════════════════════════════════════════════════════════════════════
import base64

def _make_jwt(creds_dict):
    now = int(time.time())
    header  = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps({"iss": creds_dict["client_email"],"scope": "https://www.googleapis.com/auth/spreadsheets","aud": "https://oauth2.googleapis.com/token","iat": now, "exp": now + 3600}).encode()).rstrip(b"=")
    msg = header + b"." + payload
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        pk  = serialization.load_pem_private_key(creds_dict["private_key"].encode(), password=None)
        sig = pk.sign(msg, padding.PKCS1v15(), hashes.SHA256())
        return (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
    except: return None

_sheets_token_cache = {"token": None, "exp": 0}

def get_sheets_token():
    global _sheets_token_cache
    now = int(time.time())
    if _sheets_token_cache["token"] and now < _sheets_token_cache["exp"] - 60: return _sheets_token_cache["token"]
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json: return None
        jwt = _make_jwt(json.loads(creds_json))
        if not jwt: return None
        r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            _sheets_token_cache = {"token": d["access_token"], "exp": now + d.get("expires_in", 3600)}
            return d["access_token"]
    except: pass
    return None

def registrar_en_sheets(telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return
    try:
        token = get_sheets_token()
        if not token: return
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        url   = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Hoja%201!A:H:append")
        req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, json={"values": [[ahora, str(telefono), imo_nombre, mensaje, respuesta_bot, estado, "", ""]]}, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print(f"[ERROR SAVE SHEETS] {e}")

def leer_sheet():
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return []
    try:
        token = get_sheets_token()
        if not token: return []
        r = req_lib.get(f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}/values/Hoja%201!A:H", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if r.status_code == 200: return r.json().get("values", [])
    except: pass
    return []

# ══════════════════════════════════════════════════════════════════════════
# 3. HISTORIAL Y SESIONES
# ══════════════════════════════════════════════════════════════════════════
HISTORIAL_FILE = "historial_chat.json"
_syncing = False

def forzar_sincronizacion_sheets():
    global _syncing
    if _syncing: return
    _syncing = True
    try:
        local_hist = get_historial()
        existing = set(f"{m.get('telefono','')}_{m.get('texto','')}" for m in local_hist)
        rows = leer_sheet()
        if rows:
            for row in rows[1:]:
                if len(row) < 4: continue
                hora = str(row[0]).strip(); tel = norm_tel(str(row[1]).strip())
                imo_n = str(row[2]).strip() if len(row) > 2 else ""
                msg_in, msg_out = "", ""
                if len(row) > 3: msg_in  = str(row[3]).strip()
                if len(row) > 4: msg_out = str(row[4]).strip()
                if len(row) > 6 and str(row[6]).strip(): msg_out = str(row[6]).strip()
                if tel:
                    if msg_in and f"{tel}_{msg_in}" not in existing:
                        local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_in, "tipo": "in", "hora": hora})
                        existing.add(f"{tel}_{msg_in}")
                    if msg_out and f"{tel}_{msg_out}" not in existing:
                        local_hist.append({"telefono": tel, "nombre": imo_n, "texto": msg_out, "tipo": "out", "hora": hora})
                        existing.add(f"{tel}_{msg_out}")
            with open(HISTORIAL_FILE, "w", encoding="utf-8") as f: 
                json.dump(local_hist[-2000:], f, ensure_ascii=False, indent=2) 
    except: pass
    finally: _syncing = False

def get_historial():
    try:
        if os.path.exists(HISTORIAL_FILE):
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return []

def append_historial(telefono, nombre, texto, tipo):
    try:
        h = get_historial()
        hora_actual = datetime.now().strftime("%d/%m %H:%M")
        h.append({"telefono": str(telefono), "nombre": nombre, "texto": texto, "tipo": tipo, "hora": hora_actual})
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f: json.dump(h[-2000:], f, ensure_ascii=False, indent=2)
    except: pass

def _sf(): return get_config()["sessions_path"]
def cargar_sesiones():
    try:
        with open(_sf(), "r", encoding="utf-8") as f: return json.load(f)
    except: return {}
def guardar_sesiones(s):
    with open(_sf(), "w", encoding="utf-8") as f: json.dump(s, f, ensure_ascii=False, indent=2)
def get_sesion(tel): return cargar_sesiones().get(str(tel), {})
def set_sesion(tel, d): s = cargar_sesiones(); s[str(tel)] = d; guardar_sesiones(s)
def borrar_sesion(tel): s = cargar_sesiones(); s.pop(str(tel), None); guardar_sesiones(s)

def get_minutos_inactividad(timestamp_str):
    if not timestamp_str: return 99999 
    try:
        last_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        diferencia = datetime.now() - last_time
        return diferencia.total_seconds() / 60.0
    except:
        return 99999

_respuestas_enviadas = {}

# ══════════════════════════════════════════════════════════════════════════
# 4. ESTRUCTURAS DE DATOS Y MENÚS
# ══════════════════════════════════════════════════════════════════════════

COORDINADORAS_CONTACTOS = {
    "Diana Moscoso": "51912379744",
    "Joyce Marín": "51933599903",
    "Leyla Pasquel": "51919502385",
    "Zuley Urteaga": "51933599864"
}
COORDINADORAS_LISTA = "\n• Diana Moscoso: +51 912 379 744\n• Joyce Marin: +51 933 599 903\n• Leyla Pasquel: +51 919 502 385\n• Zuley Urteaga: +51 933 599 864"
COORDINADORAS = f"Coordinadoras C1 y C2:{COORDINADORAS_LISTA}"
FIRMA = "\n\n*Comunicaciones Crear Poder Sin Limites Peru*"

MENU_STRUCTURE = {
    "main": {
        "text": (
            "🤖 *Bienvenido a Crear Poder Sin Límites Perú*\n"
            "Soy IA Cuántica, tu asistente virtual. Para brindarte el mejor apoyo, "
            "responde con el *número* de la opción deseada:\n\n"
            "1️⃣ Información de Entrenamientos\n"
            "2️⃣ Soporte para IMO (Líder)\n"
            "3️⃣ Soporte para Participante / Prospecto\n"
            "4️⃣ Estado de mi proceso\n"
            "5️⃣ Pagos y facturación\n"
            "6️⃣ Hablar con un humano (Coordinadora)\n"
            "7️⃣ Salir / Finalizar conversación"
        ),
        "options": {"1": "info_entrenamientos", "2": "action_imo", "3": "soporte_participante", "4": "estado_proceso", "5": "pagos", "6": "action_humano", "7": "action_salir"}
    },
    "info_entrenamientos": {
        "text": (
            "📘 *Información de Entrenamientos*\n"
            "Selecciona el entrenamiento sobre el que deseas aprender más:\n\n"
            "1️⃣ Capítulo 1 (C1)\n"
            "2️⃣ Capítulo 2 (C2)\n"
            "3️⃣ Maestría (MJ)\n"
            "4️⃣ Fechas y lugares\n\n"
            "9️⃣ Regresar\n"
            "0️⃣ Menú principal"
        ),
        "options": {"1": "info_c1", "2": "info_c2", "3": "info_mj", "4": "info_fechas", "9": "volver", "0": "main"}
    },
    "info_c1": {
        "text": (
            "🚀 *Capítulo 1 (C1)*: Es la fase de Descubrimiento. "
            "Un entrenamiento de 3 días para romper paradigmas, darte cuenta de tus barreras "
            "y empezar a crear resultados excepcionales.\n\n"
            "Escribe *1* si deseas contactar a un asesor para inscripción.\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": (
            "🔥 *Capítulo 2 (C2)*: Experiencia y Transformación profunda. "
            "Usualmente son 4 días inmersivos diseñados para rediseñar tu forma de relacionarte con el mundo.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": (
            "👑 *Maestría (MJ)*: El nivel donde el liderazgo se lleva a la acción. "
            "100 días de entrenamiento continuo para integrar lo aprendido y crear hábitos inquebrantables.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": (
            "📅 *Fechas y Lugares*\n"
            "Nuestra sede principal en Perú es el Hotel José Antonio Deluxe (Miraflores, Lima). "
            "Para fechas exactas del próximo equipo, elige la opción de hablar con una coordinadora.\n\n"
            "1️⃣ Hablar con coordinadora\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "soporte_participante": {
        "text": (
            "👤 *Soporte para Participante / Prospecto*\n"
            "¿En qué te podemos apoyar hoy?\n\n"
            "1️⃣ Tengo dudas sobre mi asistencia\n"
            "2️⃣ Requisitos y qué llevar al salón\n"
            "3️⃣ Realizar una consulta libre (IA Cuántica)\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "2": "requisitos_salon", "3": "action_ai_libre", "9": "volver", "0": "main"}
    },
    "requisitos_salon": {
        "text": (
            "🎒 *Requisitos para el Salón*\n"
            "Te sugerimos llevar ropa muy cómoda y una botella de agua para hidratarte. "
            "No se permiten alimentos externos y debes ser mayor de 18 años.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "estado_proceso": {
        "text": (
            "📊 *Estado de mi proceso*\n"
            "Para revisar el estatus exacto de tu matrícula o tu avance en los 100 días, "
            "necesitamos que una coordinadora verifique tu DNI en el sistema.\n\n"
            "1️⃣ Solicitar revisión a coordinadora\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": (
            "💳 *Pagos y facturación*\n"
            "Aceptamos pagos por transferencia BCP a nombre de Creación Cuántica E.I.R.L. "
            "(Cuenta: 1934218307060 / CCI: 00219300421830706018), tarjetas de crédito y PayPal.\n\n"
            "1️⃣ Enviar voucher de pago a Coordinadora\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    }
}

# ══════════════════════════════════════════════════════════════════════════
# 5. FUNCIONES DE ENVÍO Y COMUNICACIÓN
# ══════════════════════════════════════════════════════════════════════════

def enviar_mensaje(telefono, texto, nombre_imo=""):
    cfg = get_config()
    try:
        r = req_lib.post(api_url(),
            json={"messaging_product":"whatsapp","to":str(telefono),"type":"text","text":{"body":texto,"preview_url":False}},
            headers={"Authorization":f"Bearer {cfg['token']}", "Content-Type":"application/json"}, timeout=10)
        if r.status_code == 200: 
            _respuestas_enviadas[str(telefono)] = texto
            append_historial(telefono, nombre_imo, texto, "out") 
        return r.status_code == 200
    except: return False

def notificar_coordinadora_aleatoria(prospecto_tel, prospecto_nombre, ultimo_mensaje):
    coord_nombre, coord_tel = random.choice(list(COORDINADORAS_CONTACTOS.items()))
    nombre_txt = prospecto_nombre if prospecto_nombre else "No especificado"
    msg_coord = f"🚨 *NUEVO CONTACTO PARA CREAR* 🚀\n\n*Nombre:* {nombre_txt}\n*Teléfono:* wa.me/{prospecto_tel}\n*Escribió/Solicitó:* \"{ultimo_mensaje}\"\n\nEl contacto ha solicitado soporte humano en el Menú. ¡Es tu turno de apoyarlo!"
    
    sesion_coord = get_sesion(coord_tel)
    sesion_coord["primera_vez"] = False 
    set_sesion(coord_tel, sesion_coord)

    nombre_mostrar_coord = f"COORDINADORA: {coord_nombre}"
    enviar_mensaje(coord_tel, msg_coord, nombre_mostrar_coord)
    registrar_en_sheets(coord_tel, nombre_mostrar_coord, f"Alerta generada por: {prospecto_tel}", msg_coord, "ALERTA")
    return coord_nombre

def nombre_pila(s):
    partes = re.split(r'\s+', s.strip())
    if len(partes) >= 3: return partes[2].title()
    if len(partes) >= 2: return partes[1].title()
    return partes[0].title() if partes else s

# ══════════════════════════════════════════════════════════════════════════
# 6. ENRUTADOR PRINCIPAL (EL CEREBRO DEL MENÚ)
# ══════════════════════════════════════════════════════════════════════════

def procesar_mensaje(telefono, texto, imo_nombre_completo):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    
    # Etiquetado para el Panel
    nombre_mostrar = imo_nombre_completo
    if not imo_nombre_completo:
        nm = sesion.get("nombre_prospecto")
        if not nm and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric():
            nm = nombre_pila(texto)
            sesion["nombre_prospecto"] = nm
        nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"

    # 1. TIMEOUT Y CONTROL DE SESIÓN
    minutos_inactividad = get_minutos_inactividad(sesion.get("last_interaction"))
    sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Comandos Globales de Salida
    if texto_limpio == "STOP":
        marcar_stop(telefono)
        borrar_sesion(telefono)
        cfg = get_config()
        req_lib.post(api_url(), json={"messaging_product":"whatsapp","to":str(telefono),"type":"text","text":{"body":"Listo. Has sido dado de baja de este canal.\n\n*Crear Poder Sin Límites*","preview_url":False}}, headers={"Authorization":f"Bearer {cfg['token']}", "Content-Type":"application/json"}, timeout=10)
        return

    # Si pasaron 30 mins o es usuario nuevo, reiniciar menú
    if minutos_inactividad > 30 or "menu_state" not in sesion:
        sesion["menu_state"] = "main"
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    # Comandos de Navegación del Menú
    if texto_limpio in ["0", "MENU", "MENÚ"]:
        sesion["menu_state"] = "main"
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    if texto_limpio in ["9", "VOLVER"]:
        history = sesion.get("menu_history", [])
        if history:
            prev_state = history.pop() 
            sesion["menu_state"] = prev_state
            sesion["menu_history"] = history
            sesion["menu_errors"] = 0
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, MENU_STRUCTURE[prev_state]["text"], nombre_mostrar)
        else:
            sesion["menu_state"] = "main"
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    estado_actual = sesion.get("menu_state", "main")

    # -- INTERCEPCIÓN DE ESTADOS LIBRES (IA o IMO) --
    if estado_actual == "action_imo":
        ejecutar_flujo_antiguo_imo(telefono, texto, imo_nombre_completo, sesion, nombre_mostrar)
        return
        
    if estado_actual == "action_ai_libre":
        nm = sesion.get("nombre_prospecto")
        # Aquí usarías tu función Gemini original (simplificada para este bloque)
        enviar_mensaje(telefono, f"Tu consulta '{texto}' ha sido recibida. Un asesor la revisará.\n\n_Escribe *0* para volver al menú principal._", nombre_mostrar)
        set_sesion(telefono, sesion)
        return
        
    if estado_actual == "esperando_humano":
        # Modo silencioso, ya lo tiene la coordinadora
        set_sesion(telefono, sesion)
        return

    # -- NAVEGACIÓN DEL ÁRBOL DE MENÚS --
    if estado_actual in MENU_STRUCTURE:
        nodo_actual = MENU_STRUCTURE[estado_actual]
        opciones_validas = nodo_actual.get("options", {})
        
        siguiente_estado = opciones_validas.get(texto_limpio)
        
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            if siguiente_estado == "action_humano":
                nm = sesion.get("nombre_prospecto")
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, "Solicitud desde Menú Interactivo")
                enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{coord_asignada}*. Ella te escribirá en breve para apoyarte personalmente. 🚀\n\n_Escribe *0* si deseas volver al menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return
                
            elif siguiente_estado == "action_salir":
                enviar_mensaje(telefono, "Gracias por comunicarte con Crear Poder Sin Límites. ¡Que tengas un día extraordinario! ✨\n\n_Si deseas reiniciar, solo escribe MENU._", nombre_mostrar)
                borrar_sesion(telefono)
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
                elif siguiente_estado == "action_imo":
                    _, px_list = cargar_px_del_imo(telefono)
                    if px_list:
                        enviar_mensaje(telefono, f"¡Hola líder! 👋\n\nEstás en modo *Soporte IMO*. Por favor, envíame el estatus de tus participantes pendientes para registrarlos.\n\n_Escribe *0* para volver al menú principal._", nombre_mostrar)
                    else:
                        sesion["menu_state"] = "main"
                        set_sesion(telefono, sesion)
                        enviar_mensaje(telefono, "Actualmente no tienes participantes vinculados a este número en nuestro sistema.\n\n_Escribe *0* para regresar._", nombre_mostrar)
                elif siguiente_estado == "action_ai_libre":
                    enviar_mensaje(telefono, "Has ingresado al *Chat Libre*. 🧠\n\nCuéntame, ¿en qué área te gustaría que te apoyemos hoy?\n\n_Escribe *0* para salir del chat libre y volver al menú._", nombre_mostrar)

        else:
            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            
            if errores >= 3:
                sesion["menu_errors"] = 0
                nm = sesion.get("nombre_prospecto")
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, "Múltiples errores en menú interactivo")
                enviar_mensaje(telefono, f"Noto que estás teniendo inconvenientes. 🤖\n\nHe notificado a nuestra coordinadora *{coord_asignada}* para que te asista de manera humana.\n\n_Escribe *0* si prefieres volver al menú._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                msg_error = f"⚠️ *Opción no válida*. Por favor, responde únicamente con el *número* de la opción deseada.\n\n{nodo_actual['text']}"
                enviar_mensaje(telefono, msg_error, nombre_mostrar)
                
            set_sesion(telefono, sesion)
    else:
        sesion["menu_state"] = "main"
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)


# ══════════════════════════════════════════════════════════════════════════
# 7. EXCLUIDOS Y CARGA DE EXCEL PARA LÓGICA IMO ANTIGUA
# ══════════════════════════════════════════════════════════════════════════

def cargar_px_del_imo(telefono):
    lock = FileLock(ep() + ".lock")
    with lock:
        try:
            wb = load_workbook(ep(), data_only=True, read_only=True)
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

def actualizar_excel(resultados, telefono):
    pass # (Mantén tu lógica original de Excel aquí si la usabas en ejecutar_flujo_antiguo_imo)

def marcar_stop(telefono):
    pass # (Mantén tu lógica original de Excel aquí)

def formatear_resumen(extraidos):
    iconos = {"CONFIRMADO":"✅","SIGUIENTE":"➡️","NO_INTERESADO":"❌","NO_CONTESTA":"📵","PENDIENTE":"⏳"}
    return "\n".join(f"{iconos.get(e['estatus'],'•')} {e['px']} — *{e['estatus']}*" for e in extraidos)

def es_confirmacion(texto):
    t = str(texto).lower().strip()
    return t in ["si", "sí", "ok", "dale", "correcto", "perfecto"]

def ejecutar_flujo_antiguo_imo(telefono, texto, imo_nombre_completo, sesion, nombre_mostrar):
    """
    Simulación de la lógica IMO. Aquí puedes pegar tu bloque "buscar_px_en_texto" y "detectar_intencion".
    Se ejecuta solo cuando el IMO está dentro de la opción 2.
    """
    _, px_list = cargar_px_del_imo(telefono)
    pila = nombre_pila(imo_nombre_completo) if imo_nombre_completo else ""
    
    if sesion.get("estado_secundario") == "esperando_confirmacion":
        if es_confirmacion(texto):
            sesion["estado_secundario"] = None
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, f"¡Gracias {pila}! Todo quedó registrado en el sistema.\n\n_Escribe *0* para volver al menú principal._", imo_nombre_completo)
        else:
            sesion["estado_secundario"] = None
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, "Comprendido. Operación cancelada. Por favor vuelve a enviar el estatus.\n\n_Escribe *0* para volver al menú._", imo_nombre_completo)
        return
        
    # Flujo por defecto IMO (Reemplazar con tu NLP)
    sesion["estado_secundario"] = "esperando_confirmacion"
    set_sesion(telefono, sesion)
    enviar_mensaje(telefono, f"Perfecto {pila}, he detectado que quieres actualizar a tus participantes.\n\n¿Está correcto? Responde *SÍ* para confirmar.\n\n_Escribe *0* para cancelar y volver al menú._", imo_nombre_completo)

# ══════════════════════════════════════════════════════════════════════════
# 8. PANEL WEB Y ENDPOINTS DE FLASK
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
        .sidebar-header { background: #f0f2f5; padding: 15px 20px; font-weight: 600; font-size: 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
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
        .chat-input-area { background: #f0f2f5; padding: 15px 25px; display: flex; align-items: center; z-index: 1; gap: 15px; }
        .chat-input-area textarea { flex: 1; border: none; padding: 12px 15px; border-radius: 8px; resize: none; outline: none; font-size: 15px; }
        .send-btn { background: var(--primary); color: white; border: none; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; flex-shrink:0; }
        .hidden { display: none !important; }
        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; z-index: 1; color: var(--text-muted); text-align: center; padding: 20px;}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <div>💬 Panel V28 (Menú Jerárquico)</div>
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
        function renderContacts() {
            const list = document.getElementById('contactsList'); list.innerHTML = '';
            const phones = Object.keys(chatHistory).reverse();
            phones.forEach(phone => {
                const contactData = chatHistory[phone]; 
                const lastMessage = contactData.messages[contactData.messages.length - 1].text;
                const displayName = contactData.nombre ? contactData.nombre : `+${phone}`;
                const div = document.createElement('div');
                div.className = `contact-item ${activeContact === phone ? 'active' : ''}`;
                div.onclick = () => openChat(phone, displayName);
                div.innerHTML = `<div class="avatar">👤</div><div class="contact-info"><h4>${displayName}</h4><p>${lastMessage}</p></div>`;
                list.appendChild(div);
            });
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

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    data = request.json; tel = data.get("telefono"); msg = data.get("mensaje")
    if tel and msg:
        enviar_mensaje(tel, msg, "PANEL WEB")
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Faltan datos"}), 400

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode, token, challenge = (request.args.get(k) for k in ["hub.mode","hub.verify_token","hub.challenge"])
    if mode == "subscribe" and token == get_config()["verify_token"]: return challenge, 200
    return "Token invalido", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json(silent=True)
    if not data: return jsonify({"status":"ok"}), 200
    try:
        changes  = data["entry"][0]["changes"][0]["value"]
        if "messages" not in changes: return jsonify({"status":"ok"}), 200
        msg      = changes["messages"][0]
        telefono = msg["from"]
        tipo     = msg.get("type","")
        if tipo == "text":
            texto = msg["text"]["body"]
            imo_nombre_sheet, _ = cargar_px_del_imo(telefono)
            
            append_historial(telefono, imo_nombre_sheet or "CONTACTO", texto, "in")
            procesar_mensaje(telefono, texto, imo_nombre_sheet)
            
        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada.", "")
    except Exception as e: 
        print(f"Error general webhook: {e}")
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): return jsonify({"status": "activo", "version": "v28_menu_jerarquico"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=forzar_sincronizacion_sheets, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
