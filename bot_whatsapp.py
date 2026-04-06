"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
v30 PREMIUM — Encuestas de Satisfacción (CSAT) + Menú Escalonado
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
# CONFIGURACION Y UTILIDADES
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
# GOOGLE SHEETS CORE (SÍNCRONO)
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
# HISTORIAL PARA EL PANEL WEB
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

# ══════════════════════════════════════════════════════════════════════════
# ESTRUCTURAS DE DATOS Y MENÚS
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
            "🌟 *Bienvenido a Crear Poder Sin Límites Perú* 🌟\n\n"
            "Soy *IA Cuántica*, tu asistente virtual. Es un honor acompañarte hacia tu siguiente nivel de liderazgo y transformación.\n\n"
            "Para brindarte una experiencia ágil y precisa, responde con el *número* de la opción que buscas hoy:\n\n"
            "1️⃣ *Explorar Entrenamientos* (C1, C2 y Maestría)\n"
            "2️⃣ *Acceso para Líderes* (Gestión exclusiva IMO)\n"
            "3️⃣ *Soporte a Participantes* (Acompañamiento)\n"
            "4️⃣ *Estado de mi Matrícula* (Revisar tu proceso)\n"
            "5️⃣ *Inversión y Pagos* (Modalidades y cuentas)\n"
            "6️⃣ *Atención Personalizada* (Contactar a una coordinadora)\n"
            "7️⃣ *Finalizar sesión*"
        ),
        "options": {
            "1": "info_entrenamientos", 
            "2": "action_imo", 
            "3": "soporte_participante", 
            "4": "estado_proceso", 
            "5": "pagos", 
            "6": "action_humano", 
            "7": "action_salir" # El action_salir ahora activará la encuesta CSAT
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
            "🚀 *Capítulo 1 (C1)*: Es la fase de Descubrimiento. "
            "Un entrenamiento vivencial de 3 días diseñado para romper paradigmas, darte cuenta de tus barreras "
            "y empezar a crear resultados excepcionales.\n\n"
            "Escribe *1* si deseas contactar a un asesor para dar tu primer paso.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": (
            "🔥 *Capítulo 2 (C2)*: Experiencia y Transformación profunda. "
            "Usualmente son 4 días inmersivos diseñados para rediseñar tu forma de relacionarte con el mundo "
            "y descubrir tu verdadero poder de liderazgo.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": (
            "👑 *Maestría (MJ)*: El nivel donde el liderazgo se lleva a la acción. "
            "100 días de entrenamiento continuo para integrar lo aprendido y crear hábitos inquebrantables "
            "que sostengan tu éxito a largo plazo.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": (
            "📅 *Fechas y Lugares*\n"
            "Nuestra sede principal en Perú es el Hotel José Antonio Deluxe (Calle Bellavista 133, Miraflores, Lima). "
            "Contamos con distintos equipos cada mes. Para darte la fecha exacta del próximo entrenamiento:\n\n"
            "1️⃣ Solicitar calendario a una coordinadora\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "soporte_participante": {
        "text": (
            "👤 *Soporte y Acompañamiento*\n"
            "Estamos aquí para apoyarte en tu proceso. ¿Qué necesitas hoy?\n\n"
            "1️⃣ Tengo dudas sobre mi asistencia o fechas\n"
            "2️⃣ Requisitos y qué llevar al salón\n"
            "3️⃣ Realizar una consulta a un humano\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "2": "requisitos_salon", "3": "action_humano", "9": "volver", "0": "main"}
    },
    "requisitos_salon": {
        "text": (
            "🎒 *Requisitos para el Salón*\n"
            "Te sugerimos llevar ropa muy cómoda y una botella de agua para hidratarte. "
            "No necesitas cuadernos ni apuntes. Es importante recordar que no se permiten alimentos externos "
            "y el entrenamiento es exclusivo para mayores de 18 años.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9": "volver", "0": "main"}
    },
    "estado_proceso": {
        "text": (
            "📊 *Estado de mi Matrícula*\n"
            "Para revisar el estatus exacto de tu matrícula, reprogramaciones o tu avance en los 100 días, "
            "necesitamos que una coordinadora verifique tu DNI en nuestro sistema seguro.\n\n"
            "1️⃣ Solicitar revisión a coordinadora\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": (
            "💳 *Inversión y Pagos*\n"
            "Aceptamos pagos por transferencia al BCP a nombre de Creación Cuántica E.I.R.L. "
            "(Cuenta Soles: 1934218307060 / CCI: 00219300421830706018), tarjetas de crédito y PayPal.\n\n"
            "1️⃣ Enviar voucher de pago a Coordinadora\n"
            "2️⃣ Necesito ayuda con mi factura/boleta\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1": "action_humano", "2": "action_humano", "9": "volver", "0": "main"}
    }
}

# ══════════════════════════════════════════════════════════════════════════
# FUNCIONES DE ENVÍO Y MANEJO DE SESIONES
# ══════════════════════════════════════════════════════════════════════════

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
    if not timestamp_str: 
        return 99999 
    try:
        last_time = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        diferencia = datetime.now() - last_time
        return diferencia.total_seconds() / 60.0
    except:
        return 99999

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
    msg_coord = f"🚨 *NUEVO CONTACTO PARA CREAR* 🚀\n\n*Nombre:* {nombre_txt}\n*Teléfono:* wa.me/{prospecto_tel}\n*Escribió/Solicitó:* \"{ultimo_mensaje}\"\n\nEl contacto ha solicitado soporte humano en el Menú Automático. ¡Es tu turno de apoyarlo!"
    
    sesion_coord = get_sesion(coord_tel)
    sesion_coord["primera_vez"] = False 
    set_sesion(coord_tel, sesion_coord)

    nombre_mostrar_coord = f"COORDINADORA: {coord_nombre}"
    enviar_mensaje(coord_tel, msg_coord, nombre_mostrar_coord)
    registrar_en_sheets(coord_tel, nombre_mostrar_coord, f"Alerta generada por Contacto: {prospecto_tel}", msg_coord, "ALERTA LEAD")
    
    return coord_nombre

# ══════════════════════════════════════════════════════════════════════════
# NLP BÁSICO Y FUNCIONES IMO (Aisladas)
# ══════════════════════════════════════════════════════════════════════════
def nombre_pila(s):
    partes = re.split(r'\s+', s.strip())
    if len(partes) >= 3: return partes[2].title()
    if len(partes) >= 2: return partes[1].title()
    return partes[0].title() if partes else s

def formatear_resumen(extraidos):
    iconos = {"CONFIRMADO":"✅","SIGUIENTE":"➡️","NO_INTERESADO":"❌","NO_CONTESTA":"📵","PENDIENTE":"⏳","GESTIONANDO":"🔄","YA_SE_SENTO":"🎓", "FALLECIO_ENFERMO":"🏥"}
    return "\n".join(f"{iconos.get(e['estatus'],'•')} {e['px']} — *{e['estatus']}*" for e in extraidos)

def es_confirmacion(texto):
    t = str(texto).lower().strip()
    return t in ["si", "sí", "ok", "dale", "correcto", "perfecto", "claro"]

# Aquí cargarías el Excel como antes
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
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    tel_n = norm_tel(telefono)
    with _excel_lock, FileLock(ep() + ".lock"):
        try:
            wb = load_workbook(ep())
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                imo_t = norm_tel(str(row[3].value or "")); px_c = str(row[4].value or "").strip()
                if imo_t != tel_n: continue
                for r in resultados:
                    if r["px"].lower().strip() == px_c.lower().strip() or r["px"].split()[0].lower() == px_c.split()[0].lower():
                        row[6].value = r["estatus"]; row[7].value = hoy; break
            wb.save(ep()); wb.close()
        except: pass

def marcar_stop(telefono):
    tel_n = norm_tel(telefono)
    hoy   = datetime.now().strftime("%d/%m/%Y %H:%M")
    with _excel_lock, FileLock(ep() + ".lock"):
        try:
            wb = load_workbook(ep())
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                if norm_tel(str(row[3].value or "")) == tel_n: row[6].value = "STOP"; row[7].value = hoy
            wb.save(ep()); wb.close()
        except: pass

def ejecutar_flujo_antiguo_imo(telefono, texto, imo_nombre_completo, sesion, nombre_mostrar):
    _, px_list = cargar_px_del_imo(telefono)
    pila = nombre_pila(imo_nombre_completo) if imo_nombre_completo else ""
    
    if sesion.get("estado_secundario") == "esperando_confirmacion":
        if es_confirmacion(texto):
            extraidos = sesion.get("extraidos", [])
            actualizar_excel(extraidos, telefono)
            confirmados = [e for e in extraidos if e["estatus"] == "CONFIRMADO"]
            if confirmados:
                px_nombres = [e["px"] for e in confirmados]
                sesion["estado_secundario"] = "esperando_fecha"
                sesion["px_confirmados"] = px_nombres
                set_sesion(telefono, sesion)
                nombres_fmt = "\n".join(f"• {x}" for x in px_nombres)
                enviar_mensaje(telefono, f"Hola {pila},\n\nConfirmación registrada para:\n\n{nombres_fmt}\n\n¿En qué día estarán presentes?\n*(Viernes 1, Sábado 2, Domingo 3 de mayo)*\n\n_Escribe 0 para menú_", nombre_mostrar)
            else:
                sesion["estado_secundario"] = None
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, f"¡Gracias {pila}! Todo quedó registrado en el sistema y retirado de tus pendientes.\n\n_Escribe *0* para volver al menú principal._", nombre_mostrar)
        else:
            sesion["estado_secundario"] = None
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, "Comprendido. Operación cancelada. Por favor vuelve a enviarme el estatus.\n\n_Escribe *0* para regresar._", nombre_mostrar)
        return

    if sesion.get("estado_secundario") == "esperando_fecha":
        sesion["estado_secundario"] = None 
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, f"¡Excelente {pila}!\n\nConfirmación de fecha registrada.\nLos esperamos en el *Hotel Jose Antonio Deluxe*, Mesa de registro a las *9:00 am*.\n\n_Escribe *0* para volver al menú principal._", nombre_mostrar)
        return

    # Si escribe algo que no detectamos (SIMPLIFICADO PARA ESTA V30)
    enviar_mensaje(telefono, f"Has ingresado información de estatus. Como líder IMO, puedes indicarme nombres como 'Pedro confirma', 'María pendiente'.\n\n_Escribe *0* para volver al menú principal._", nombre_mostrar)

# ══════════════════════════════════════════════════════════════════════════
# ENRUTADOR FRONTAL (MÁQUINA DE ESTADOS DEL MENÚ + ENCUESTA)
# ══════════════════════════════════════════════════════════════════════════

def procesar_mensaje(telefono, texto, imo_nombre_completo):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    
    # Etiquetas Web
    nombre_mostrar = imo_nombre_completo
    if not imo_nombre_completo:
        nm = sesion.get("nombre_prospecto")
        if not nm and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric():
            nm = nombre_pila(texto)
            sesion["nombre_prospecto"] = nm
        nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"

    # -- 1. CONTROL DE ENCUESTA CSAT (INTERCEPTOR PRIORITARIO) --
    if sesion.get("menu_state") == "esperando_encuesta":
        if texto_limpio in ["1", "2", "3", "4", "5"]:
            # Guardamos la calificación asíncronamente en Sheets
            threading.Thread(target=registrar_en_sheets, args=(telefono, nombre_mostrar, "Calificación del Asistente", f"{texto_limpio} Estrellas", "ENCUESTA CSAT"), daemon=True).start()
            
            enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟 Valoramos mucho tu opinión para seguir mejorando.\n\nQue tengas un día extraordinario. ✨\n\n_Si deseas iniciar una nueva consulta en cualquier momento, solo escribe la palabra MENU._", nombre_mostrar)
            borrar_sesion(telefono)
        else:
            enviar_mensaje(telefono, "Por favor, para finalizar califica respondiendo *únicamente con un número del 1 al 5*.", nombre_mostrar)
        return

    # -- 2. TIMEOUT Y CONTROL DE SESIÓN --
    minutos_inactividad = get_minutos_inactividad(sesion.get("last_interaction"))
    sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if texto_limpio == "STOP":
        marcar_stop(telefono)
        borrar_sesion(telefono)
        cfg = get_config()
        req_lib.post(api_url(), json={"messaging_product":"whatsapp","to":str(telefono),"type":"text","text":{"body":"Listo. Has sido dado de baja de este canal. No recibirás más mensajes.\n\n*Crear Poder Sin Límites*","preview_url":False}}, headers={"Authorization":f"Bearer {cfg['token']}", "Content-Type":"application/json"}, timeout=10)
        return

    # Reinicio si pasó mucho tiempo o es nuevo
    if minutos_inactividad > 30 or "menu_state" not in sesion:
        sesion["menu_state"] = "main"
        sesion["menu_history"] = []
        sesion["menu_errors"] = 0
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)
        return

    # -- 3. COMANDOS DE NAVEGACIÓN UNIVERSAL --
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

    # -- 4. INTERCEPCIÓN DE ESTADOS LIBRES --
    if estado_actual == "action_imo":
        ejecutar_flujo_antiguo_imo(telefono, texto, imo_nombre_completo, sesion, nombre_mostrar)
        return
        
    if estado_actual == "esperando_humano":
        # Silencio mientras habla la coordinadora
        set_sesion(telefono, sesion)
        return

    # -- 5. NAVEGACIÓN DEL ÁRBOL DE MENÚS --
    if estado_actual in MENU_STRUCTURE:
        nodo_actual = MENU_STRUCTURE[estado_actual]
        opciones_validas = nodo_actual.get("options", {})
        
        siguiente_estado = opciones_validas.get(texto_limpio)
        
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            # --- EVALUACIÓN DE ACCIONES ---
            if siguiente_estado == "action_humano":
                nm = sesion.get("nombre_prospecto")
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, f"Solicitud desde la opción del menú actual")
                enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{coord_asignada}*. Ella te escribirá por aquí en breve para apoyarte personalmente. 🚀\n\n_Escribe *0* si deseas volver al menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return
                
            elif siguiente_estado == "action_salir":
                # AQUÍ ACTIVAMOS LA ENCUESTA DE SATISFACCIÓN (CSAT)
                sesion["menu_state"] = "esperando_encuesta"
                set_sesion(telefono, sesion)
                msg_encuesta = (
                    "Antes de irte, nos encantaría saber cómo te fue. 🤖\n\n"
                    "¿Cómo calificarías tu experiencia de hoy con nuestra *IA Cuántica*?\n\n"
                    "Responde con un número del *1 al 5*:\n\n"
                    "1️⃣ = Mala experiencia\n"
                    "5️⃣ = ¡Excelente, me apoyó rápido!"
                )
                enviar_mensaje(telefono, msg_encuesta, nombre_mostrar)
                return
                
            elif siguiente_estado == "volver":
                pass 
                
            # --- TRANSICIÓN A OTRO MENÚ O FLUJO ---
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
                    pila = nombre_pila(imo_nombre_completo) if imo_nombre_completo else ""
                    if px_list:
                        enviar_mensaje(telefono, f"¡Hola líder {pila}! 👋\n\nHas ingresado al *Portal IMO*. Por favor, envíame un mensaje con el estatus de tus participantes pendientes para registrarlos en el sistema.\n\n_Escribe *0* para finalizar la gestión y volver al menú._", nombre_mostrar)
                    else:
                        sesion["menu_state"] = "main"
                        set_sesion(telefono, sesion)
                        enviar_mensaje(telefono, "⚠️ Nuestro sistema indica que actualmente no tienes participantes pendientes vinculados a este número.\n\n_Si crees que esto es un error, selecciona la opción *6* en el menú para hablar con una coordinadora._", nombre_mostrar)
                        time.sleep(1)
                        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)

        else:
            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            
            if errores >= 3:
                sesion["menu_errors"] = 0
                nm = sesion.get("nombre_prospecto")
                coord_asignada = notificar_coordinadora_aleatoria(telefono, nm, f"El usuario se atascó en el menú con la respuesta: '{texto}'")
                enviar_mensaje(telefono, f"Noto que estamos teniendo problemas de comunicación. 🤖\n\nNo te preocupes, he notificado a nuestra coordinadora *{coord_asignada}* para que te asista personalmente de manera humana.\n\n_Escribe *0* si prefieres volver al menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                msg_error = f"⚠️ *Opción no válida*. Por favor, responde únicamente con el *número* (ej. 1, 2, 3) de la opción que deseas explorar.\n\n{nodo_actual['text']}"
                enviar_mensaje(telefono, msg_error, nombre_mostrar)
                
            set_sesion(telefono, sesion)
    else:
        sesion["menu_state"] = "main"
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, MENU_STRUCTURE["main"]["text"], nombre_mostrar)

# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS Y RUTAS WEB
# ══════════════════════════════════════════════════════════════════════════

@app.route("/chat", methods=["GET"])
def panel_chat(): 
    # Mantenemos un HTML ligero, el tuyo es perfecto
    return "<h1>Panel Activo. Usa tu index HTML aquí.</h1>"

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
            
        enviar_mensaje(tel, msg, imo_nombre)
        registrar_en_sheets(tel, imo_nombre, "[ENVIADO DESDE PANEL PRIVADO]", msg, "MANUAL")
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
            
            # Nombre para mostrar en Panel
            nombre_mostrar = imo_nombre_sheet
            if not imo_nombre_sheet:
                sesion = get_sesion(telefono)
                nm = sesion.get("nombre_prospecto")
                if not nm and len(texto.split()) <= 3 and len(texto) > 2 and not texto.strip().upper().isnumeric():
                    nm = nombre_pila(texto)
                nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"
            
            append_historial(telefono, nombre_mostrar, texto, "in")
            procesar_mensaje(telefono, texto, imo_nombre_sheet)
            
            # Actualizar nombre post-procesamiento
            sesion_updated = get_sesion(telefono)
            if not imo_nombre_sheet:
                nm_updated = sesion_updated.get("nombre_prospecto")
                nombre_mostrar = f"CONTACTO: {nm_updated}" if nm_updated else "NUEVO CONTACTO"

            respuesta_enviada = _respuestas_enviadas.pop(str(telefono), "")
            if respuesta_enviada:
                registrar_en_sheets(telefono, nombre_mostrar, texto, respuesta_enviada[:500], "MENÚ INTERACTIVO" if not imo_nombre_sheet else "IMO")
            
        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.", "")
    except Exception as e: 
        print(f"Error webhook: {e}")
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): return jsonify({"status": "activo", "version": "v30_encuestas_csat"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=forzar_sincronizacion_sheets, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
