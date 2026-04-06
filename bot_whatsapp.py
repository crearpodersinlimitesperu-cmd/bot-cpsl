"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
v19 MAGISTRAL — Memoria Prospectos Fix y Etiquetado en Chat
"""

import os, re, json, threading, time, csv, io
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
    historial = []
    try:
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
                    if msg_in: historial.append({"telefono": tel, "nombre": imo_n, "texto": msg_in, "tipo": "in", "hora": hora})
                    if msg_out: historial.append({"telefono": tel, "nombre": imo_n, "texto": msg_out, "tipo": "out", "hora": hora})
            with open(HISTORIAL_FILE, "w", encoding="utf-8") as f: json.dump(historial[-1500:], f, ensure_ascii=False, indent=2) 
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
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f: json.dump(h[-1500:], f, ensure_ascii=False, indent=2)
    except: pass

# ══════════════════════════════════════════════════════════════════════════
# MOTOR DE IA + BANCO MAESTRO DE RESPUESTAS (SIN IA)
# ══════════════════════════════════════════════════════════════════════════

def humanizar_con_gemini(mensaje_usuario, plantilla_base, imo_nombre, es_pregunta_compleja=False):
    cfg = get_config()
    if not es_pregunta_compleja: return plantilla_base
    if not cfg["gemini_key"] or genai is None: return plantilla_base 
    try:
        client = genai.Client(api_key=cfg["gemini_key"])
        prompt = f"""
        Eres el asistente de WhatsApp de 'Crear Poder Sin Límites Perú'.
        Hablas con el líder (IMO): {imo_nombre}.
        Mensaje recibido: "{mensaje_usuario}"
        Responde basándote en esta información obligatoria: "{plantilla_base}"
        Reglas Estrictas: 
        1. SÉ EXTREMADAMENTE BREVE Y PROFESIONAL.
        2. NO uses "entender", "entiendo". Usa "comprender", "comprendo".
        3. NO uses "ayudar". Usa "apoyar", "acompañar" o "crear".
        4. ELIMINA TODO RASTRO DE IA.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if response.text: return response.text.strip()
        return plantilla_base
    except: return plantilla_base

def embudo_ventas_gemini(mensaje_usuario, nombre_conocido=None):
    cfg = get_config()
    
    # 🌟 BANCO MAESTRO DE RESPUESTAS (FALLBACK ANTI-FALLOS)
    def respuesta_del_banco(mensaje):
        msg_norm = normalizar(mensaje)
        banco_preguntas = [
            (["precio", "costo", "cuanto cuesta", "pagar", "inversion", "cuenta", "banco", "transferencia"], f"Para brindarte los detalles de inversión y formas de pago, por favor comunícate directamente con nuestras coordinadoras:\n\n{COORDINADORAS}"),
            (["horario", "hora", "cuando empieza", "cuando termina", "dias", "fechas", "cronograma", "agenda"], f"El entrenamiento dura 3 días:\n\n{INFO_C1}"),
            (["donde", "lugar", "direccion", "ubicacion", "hotel", "distrito", "llegar", "mapa"], f"El entrenamiento se realiza en el Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores, Lima."),
            (["ropa", "vestimenta", "que llevar", "llevar", "cuaderno", "lapicero", "frio", "calor"], "Te sugerimos llevar ropa muy cómoda y una botella de agua. No necesitas materiales para tomar nota."),
            (["comida", "almuerzo", "refrigerio", "comer", "desayuno", "cena", "snacks"], "No se permiten alimentos ni bebidas externas al salón. Habrá espacios y tiempos adecuados para salir a comer por la zona."),
            (["que es", "de que trata", "que hacen", "para que sirve", "informacion", "info", "detalles", "explicame", "beneficios", "ayuda", "sanacion", "saber"], "El Capítulo 1 es un entrenamiento vivencial de 3 días diseñado para romper paradigmas, descubrir tus barreras y apoyarte a crear nuevos resultados excepcionales en tu vida."),
            (["hola", "buenos dias", "buenas tardes", "buenas noches", "saludos", "que tal"], f"¡Hola! Somos Crear Poder Sin Límites Perú. ¿Con quién tengo el gusto y cómo podemos apoyarte hoy?"),
            (["edad", "niños", "menores", "jovenes", "adolescentes", "hijo", "hija"], "El Capítulo 1 está diseñado para adultos. Para conocer nuestros programas para niños y adolescentes, contacta a nuestras coordinadoras."),
            (["coordinadora", "asesor", "humano", "persona", "llamar", "numero", "telefono", "contactar"], f"Claro, para una atención más personalizada comunícate con nuestras coordinadoras:\n\n{COORDINADORAS}")
        ]
        
        for palabras_clave, respuesta in banco_preguntas:
            if any(kw in msg_norm for kw in palabras_clave):
                return respuesta
        
        if nombre_conocido:
            return f"¡Comprendido, {nombre_conocido}! Para resolver tu consulta a detalle y brindarte atención personalizada, por favor escríbele a nuestras coordinadoras:\n\n{COORDINADORAS}"
        else:
            return f"Hola, somos Crear Poder Sin Límites Perú. Para brindarte la información exacta y apoyarte mejor, por favor dinos tu nombre o comunícate directamente con nuestras coordinadoras:\n\n{COORDINADORAS}"

    if not cfg["gemini_key"] or genai is None: return respuesta_del_banco(mensaje_usuario)
    
    try:
        client = genai.Client(api_key=cfg["gemini_key"])
        prompt = f"""
        Eres un Asesor Profesional de 'Crear Poder Sin Límites Perú'.
        Un prospecto acaba de escribir: "{mensaje_usuario}"
        
        Contexto: Su nombre es: "{nombre_conocido if nombre_conocido else 'Desconocido'}".
        
        Reglas Estrictas de Venta y Comunicación:
        1. REGLA #1 (EL NOMBRE): Si no sabes su nombre, tu ÚNICO objetivo es saludar y PREGUNTAR SU NOMBRE. Si YA SABES SU NOMBRE, úsalo de forma natural y NO LO VUELVAS A PREGUNTAR.
        2. PALABRAS PROHIBIDAS: "sanación", "sanar", "curar", "terapia", "paciente", "ayuda", "ayudar", "entender", "entiendo".
        3. PALABRAS DE PODER: Usa "comprender", "apoyar", "acompañar", "transformación", "crear", "liderazgo".
        4. CERO RASTROS DE IA: Eres un profesional humano y experto.
        5. BREVEDAD ABSOLUTA: Respuesta muy corta (máximo 2 oraciones).
        6. Vende el Capítulo 1 enfocado en crear resultados y termina con una pregunta corta para continuar la conversación.
        """
        response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
        if response.text: return response.text.strip()
    except Exception as e:
        error_str = str(e)
        if "503" in error_str or "429" in error_str:
            time.sleep(1) 
        return respuesta_del_banco(mensaje_usuario)
        
    return respuesta_del_banco(mensaje_usuario)

# ══════════════════════════════════════════════════════════════════════════
# EXCLUIDOS Y LECTURA DE EXCEL
# ══════════════════════════════════════════════════════════════════════════

EXCLUIDOS_CAMPAÑA = [
    "VERóNICA CECILIA SILVA SOTELO", "MOISéS SAMUEL ESTRADA CIRILO", "DANILO PRETEL OCAMPO",
    "MELANNY KATIUSKA TRUJILLO HUALLPATUERO", "MARCO ANTONIO TINGO TAYPE", "MILTO CHOCAN MORALES",
    "BELéN MARíA GUTIéRREZ VáSQUEZ", "LUIS ENRIQUE VALDIVIA BENDEZU", "NATALí VERA PACHAS",
    "VIOLETA CALLE VALDIVIEZO", "HAROLD DIAZ HUBY", "OSCAR VIDAL LAIMITO SIMICH",
    "LIZ TENORIO VASQUEZ", "MILUSKA CaCERES", "SUSAN ROSEMARY GUTIERREZ ESTRELLA",
    "MERCEDES OCHOA AGUIRRE", "DIANA CORRALES HOLGUIN", "CHRISTIAN MICHEL GUILLeN OSCO",
    "MELANIE ROSA HUAMaN VILLENA", "XAVIER LUIS CACERES ZEVALLOS", "JORGE PARDO AJALCRInA",
    "RUBeN LEODAN VALVERDE ROJAS", "OMAR JUNIOR GUTIeRREZ MAMANI", "GUIDO SALLO CJUIRO",
    "YURI FRANK CORNEJO PUMA", "KARLA ANDREA VELA GONZaLES", "BARBARA YAHAIRA LLONTOP ASTUCURI",
    "DEYSI MELO VIZCARRA"
]

def esta_excluido(nombre_px):
    px_norm = normalizar(nombre_px)
    for excluido in EXCLUIDOS_CAMPAÑA:
        if normalizar(excluido) in px_norm or px_norm in normalizar(excluido): return True
    return False

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
                        if not esta_excluido(px_n): px_list.append(px_n)
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
                    pa_r = normalizar(r["px"].split()[0]) if r["px"].split() else ""
                    pa_c = normalizar(px_c.split()[0]) if px_c.split() else ""
                    if normalizar(r["px"]) == normalizar(px_c) or (pa_r == pa_c and len(pa_r) > 3):
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

# ══════════════════════════════════════════════════════════════════════════
# KEYWORDS NLP Y PROCESAMIENTO
# ══════════════════════════════════════════════════════════════════════════
KEYWORDS = {
    "STOP": ["stop","baja","no mas mensajes","no quiero mensajes","desuscribir","alto","detener","no me escriban","no escriban","no les escriban"],
    "NO_INTERESADO": ["no quiere","ya no quiere","no le interesa","no interesa","desistio","desistió","no va a continuar","no continua","no desea","se retira","no va a ir","no piensa ir","no va a asistir","no quiere.","no tiene intencion","desinteresada","desinteresado","no le gusto","no le gustó","se retiró","no quiere continuar","ninguno","ninguna","nadie","ambas desistieron","los dos desistieron"],
    "NO_CONTESTA": ["no contesta","no me contesta","no responde","no me responde","sin respuesta","no lo ubico","no la ubico","bloqueo","bloqueó","me bloqueo","me bloqueó","perdí el rastro","ya no tengo contacto","ya no responde","no atiende"],
    "YA_SE_SENTO": ["ya se sento","ya se sentó","ya asistio","ya asistió","ya fue","ya estuvo","ya participo","ya participó","se sento","se sentó","ya vino","ya vinieron","fue cambiada","fue cambiado","ya se sentaron","si se sento","sí se sentó","si asistió","si fue"],
    "FALLECIO_ENFERMO": ["fallecio","falleció","murio","murió","hospitalizado","grave","accidente","gestando","embarazada","en duelo"],
    "SIGUIENTE": ["siguiente equipo","otro equipo","proximo equipo","siguiente c1","otro c1","en el proximo","en mayo","siguiente oportunidad"],
    "CONFIRMADO": ["confirma","confirmado","confirmada","confirmo","si va","sí va","va a venir","va a asistir","va al c1","se sienta","van todos","vienen todos","se sento","se sentó","si se van a sentar","tiene vuelos","vuelos comprados", "ambos", "todos"],
    "PENDIENTE": ["pendiente","aun no se","todavia no","esta pensando","evaluando","en proceso","provincias","de viaje","fuera de lima","regresa","para esa fecha si","si estaran","sí estarán"],
    "DEVOLUCION": ["devolucion","devolución","devolver dinero","reembolso","quiero mi dinero","devuelvan","quiere su dinero"],
    "CAMBIO": ["cambio de nombre","cambiar nombre","traspaso","cambio de participante","a cambio de","quiero cambiar","cambiar a","en lugar de","deseo cambiar","cambiar por","sustituir","reemplazar"],
    "INFO_C1": ["horario","donde es","dónde es","direccion","dirección","fecha","cuando es","cuándo es","hotel","miraflores","proximo c1","próximo c1","c1 de mayo","informacion del c1","info del c1"],
    "VOLANTE": ["volante","flyer","invitacion","invitación","afiche","imagen del c1","informacion del entrenamiento","info del entrenamiento","comparte la info","comparte la informacion","mandame la info","mandame el flyer","mandame el volante","compartir la informacion"],
    "CONSULTA_PX": ["ya confirmo","ya confirmó","ya confirma","confirmo ella","confirmo el","se inscribio","se inscribió","ya pago","ya pagó","esta inscrita","esta inscrito","ya esta","ya está","ya confirmas","ya lo confirma","ya la confirma","tiene lugar","tiene espacio","aparece en el sistema"],
    "QUIEN_ERES": ["con quien hablo","con quien tengo el gusto","quien me escribe","quien eres","de donde me escriben","que numero es este","de donde","con quien","quién"],
    "NO_RECUERDA": ["no recuerdo","no se quien","no conozco","quien es esta persona","no tengo informacion"],
    "GESTIONANDO": ["lo estoy gestionando","me muevo","me comunicare","voy a hablar","voy a contactar","tratare de","voy a preguntar","para darle una respuesta","estare informando","cuenten con mi acompanamiento","ahora me muevo","si estare atento","le voy a recordar","estoy en conversaciones","estoy contactandolo","seguimiento"],
}

def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]: t = t.replace(a, b)
    return t

def detectar_intencion(texto):
    t = normalizar(texto)
    orden = ["STOP", "NO_INTERESADO", "NO_CONTESTA", "YA_SE_SENTO", "FALLECIO_ENFERMO", 
             "SIGUIENTE", "CONFIRMADO", "PENDIENTE", "DEVOLUCION", "CAMBIO", 
             "INFO_C1", "VOLANTE", "CONSULTA_PX", "QUIEN_ERES", "NO_RECUERDA", "GESTIONANDO"]
    for intent in orden:
        for kw in KEYWORDS[intent]:
            if re.search(r'(?<![a-z])' + re.escape(normalizar(kw)) + r'(?![a-z])', t): return intent
    return None

def buscar_px_en_texto(texto, px_list):
    resultados = []
    t_norm = normalizar(texto)
    intencion_global = detectar_intencion(texto)

    global_words = ["ninguno", "ninguna", "ambos", "ambas", "todos", "todas", "los dos", "las dos", "nadie"]
    if any(gw in t_norm.split() for gw in global_words) and intencion_global:
        if intencion_global not in ("INFO_C1", "VOLANTE", "QUIEN_ERES", "CAMBIO", "DEVOLUCION", "STOP", "NO_RECUERDA", "CONSULTA_PX"):
            for px in px_list: resultados.append({"px": px, "estatus": intencion_global})
            return resultados

    if len(px_list) == 1:
        if intencion_global and intencion_global not in ("STOP","CAMBIO","INFO_C1","NO_RECUERDA","QUIEN_ERES","DEVOLUCION","VOLANTE","CONSULTA_PX"):
            resultados.append({"px": px_list[0], "estatus": intencion_global})
        return resultados

    for px in px_list:
        tokens = [p for p in px.split() if len(p) > 3]
        for token in tokens:
            patron  = r'(?<![a-z])' + re.escape(normalizar(token)) + r'(?![a-z])'
            if re.search(patron, t_norm):
                match = re.search(patron, t_norm)
                fragmento = texto[max(0, match.start() - 15):min(len(texto), match.end() + 100)]
                intencion = detectar_intencion(fragmento) or intencion_global
                if intencion and intencion not in ("STOP","CAMBIO","INFO_C1","NO_RECUERDA","QUIEN_ERES","DEVOLUCION", "VOLANTE","CONSULTA_PX"):
                    resultados.append({"px": px, "estatus": intencion})
                break
    
    vistos, dedup = set(), []
    for r in resultados:
        if r["px"] not in vistos: vistos.add(r["px"]); dedup.append(r)
    return dedup

# ══════════════════════════════════════════════════════════════════════════
# SESIONES Y ENVIO
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

_respuestas_enviadas = {}

# Textos Base Globales
INFO_C1 = """Capítulo 1 — Equipo 27\n\nHotel José Antonio Deluxe\nCalle Bellavista 133, Miraflores, Lima\n\n*Viernes 1 de mayo*\n- 09:00 am Mesa de registro (obligatorio)\n- 10:00 am Inicio\n\n*Sábado 2 de mayo*\n- 09:00 am Ingreso\n- 10:00 am Inicio\n\n*Domingo 3 de mayo*\n- 09:00 am Inicio\n- 09:00 pm Cierre y celebración\n\nRopa cómoda, botella de agua."""
COORDINADORAS = """Coordinadoras C1 y C2:\nDiana Moscoso: +51 912 379 744\nJoyce Marin: +51 933 599 903\nLeyla Pasquel: +51 919 502 385\nZuley Urteaga: +51 933 599 864"""
STOP_CLAUSULA = "\n\n_Si no deseas recibir mas mensajes de este numero, responde STOP._"
FIRMA = "\n\n*Comunicaciones Crear Poder Sin Limites Peru*"

def enviar_mensaje(telefono, texto, nombre_imo=""):
    sesion = get_sesion(telefono)
    
    if sesion.get("primera_vez", True):
        aclaracion = "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*. Mis respuestas pueden ser limitadas. Para más información o si el sistema se satura, comunícate con nuestras coordinadoras:_\n\n" + COORDINADORAS
        if "Coordinadoras C1 y C2" not in texto:
            texto += aclaracion
        else:
            texto += "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*. Mis respuestas pueden ser limitadas. En caso de saturación, contacta a las coordinadoras mencionadas._"
        sesion["primera_vez"] = False
        set_sesion(telefono, sesion)

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

def nombre_pila(s):
    partes = re.split(r'\s+', s.strip())
    if len(partes) >= 3: return partes[2].title()
    if len(partes) >= 2: return partes[1].title()
    return partes[0].title() if partes else s

def formatear_resumen(extraidos):
    iconos = {"CONFIRMADO":"✅","SIGUIENTE":"➡️","NO_INTERESADO":"❌","NO_CONTESTA":"📵","PENDIENTE":"⏳","GESTIONANDO":"🔄","YA_SE_SENTO":"🎓", "FALLECIO_ENFERMO":"🏥"}
    return "\n".join(f"{iconos.get(e['estatus'],'•')} {e['px']} — *{e['estatus']}*" for e in extraidos)

def es_confirmacion(texto):
    t = normalizar(texto)
    tokens = re.findall(r'[a-z]+', t)
    ok  = {"ok","dale","correcto","exacto","perfecto","listo","claro","afirmativo","confirmado","confirmo","si","yes","asi"}
    neg = {"no","pero","aunque","contesta","puede","podria","quiero","deseo","cambiar","espera"}
    if not tokens: return False
    if all(tok in ok for tok in tokens): return True
    if any(neg in t for neg in neg): return False
    if tokens[0] in ok and len(tokens) <= 3: return True
    return False

def r_quien_eres(pila=""): return (f"Hola {pila},\n\nTe contactamos de *Crear Poder Sin Limites Peru*.\n\nSomos comunicaciones en seguimiento del *Capitulo 1 — Equipo 27* (1, 2 y 3 de mayo).\n\nComo IMO, tienes participantes con inscripcion activa." + FIRMA)
def r_cambio(pila): return (f"Hola {pila},\n\nLos cambios de nombre se gestionan directamente con tu coordinadora. El límite es el miércoles previo a las 6:00 pm.\n\n" + COORDINADORAS + FIRMA)
def r_devolucion(pila): return (f"Hola {pila},\n\nEn Crear no realizamos devoluciones una vez efectuado el pago. Lo que aplica es que la inversión queda activa para el siguiente equipo.\n\n" + COORDINADORAS + FIRMA)
def r_info_c1(pila): return (f"Hola {pila}, aqui tienes la informacion completa:\n\n" + INFO_C1 + "\n\n" + COORDINADORAS + FIRMA)
def r_ya_sento(pila): return (f"Hola {pila},\n\nGracias por informarnos. El participante quedará registrado como que ya tomó el entrenamiento.\n\nCada persona que toma la decisión de sentarse da un paso que transforma su vida." + FIRMA)
def r_no_recuerda(pila): return (f"Hola {pila},\n\nSin problema. Si tienes alguna consulta sobre tu equipo, comunicate con tu coordinadora:\n\n" + COORDINADORAS + FIRMA)
def r_fallecio_enfermo(pila): return (f"Hola {pila},\n\nRecibimos tu mensaje. Lamentamos la situacion. 🙏\n\nQuedará registrado para no incomodar. Por favor comunicate con tu coordinadora:\n\n" + COORDINADORAS + FIRMA)
def r_no_interesado(pila, px_list): return (f"Hola {pila},\n\nRecibido. Cada persona elige en que momento toma accion. Mientras tanto, su inscripcion sigue activa hasta el *3 de mayo*." + FIRMA)
def r_no_contesta(pila, px_list): return (f"Hola {pila},\n\nComprendido. Te recomendamos intentar por via telefonica directa. La inscripcion sigue activa hasta el *1 de mayo*." + FIRMA)
def r_volante(pila): return (f"Hola {pila},\n\nAqui tienes toda la informacion del entrenamiento:\n\n" + INFO_C1 + "\n\n" + FIRMA)
def r_consulta_px(pila): return (f"Hola {pila},\n\nEste canal no tiene acceso al sistema de registros. Para confirmar asistencia, comunicate directamente con el participante." + FIRMA)
def r_pendiente(pila, px_list):
    lista = "\n".join(f"• {px}" for px in px_list) if px_list else ""
    return (f"Hola {pila},\n\nRecibido. El C1 E27 es el *1, 2 y 3 de mayo*.\n\nPersonas pendientes:\n{lista}\n\nCuando tengas una actualizacion, escribenos." + FIRMA) if px_list else (f"Hola {pila}, recibido. Cualquier novedad, escribenos." + FIRMA)
def r_no_entendido(pila, px_list):
    lista = "\n".join(f"• {px}" for px in px_list)
    return (f"Hola {pila},\n\nComprendo tu mensaje. 🤔\n\nPara poder registrarlo bien, por favor dime si asisten o no asisten estas personas:\n\n{lista}\n\n*(Ejemplo: 'Todos asisten', 'Ninguno va', o detalla por nombre)*" + FIRMA)
def r_pedir_fecha(pila, px_confirmados):
    nombres = "\n".join(f"• {px}" for px in px_confirmados)
    return (f"Hola {pila},\n\nConfirmacion registrada para:\n\n{nombres}\n\n¿En que dia estaran presentes?\n*(Viernes 1, Sabado 2, Domingo 3 de mayo — o los tres dias)*" + FIRMA)

# ══════════════════════════════════════════════════════════════════════════
# LOGICA PRINCIPAL DEL BOT
# ══════════════════════════════════════════════════════════════════════════

def procesar_mensaje(telefono, texto, imo_nombre_completo):
    sesion    = get_sesion(telefono)
    intencion = detectar_intencion(texto)

    if intencion == "STOP":
        marcar_stop(telefono); borrar_sesion(telefono)
        cfg = get_config()
        req_lib.post(api_url(), json={"messaging_product":"whatsapp","to":str(telefono),"type":"text","text":{"body":"Listo. Has sido dado de baja de este canal. No recibiras mas mensajes." + FIRMA,"preview_url":False}}, headers={"Authorization":f"Bearer {cfg['token']}", "Content-Type":"application/json"}, timeout=10)
        return

    _, px_list = cargar_px_del_imo(telefono)
    pila = nombre_pila(imo_nombre_completo) if imo_nombre_completo else ""
    
    if not imo_nombre_completo:
        nombre_guardado = sesion.get("nombre_prospecto")
        
        # 🧠 INTELIGENCIA DE NOMBRES: Si es un mensaje corto y no teníamos el nombre, lo guardamos.
        if not nombre_guardado and len(texto.split()) <= 3 and len(texto) > 2:
            sesion["nombre_prospecto"] = nombre_pila(texto)
            set_sesion(telefono, sesion)
            nombre_guardado = sesion["nombre_prospecto"]
            
        nombre_mostrar = f"NUEVO PROSPECTO: {nombre_guardado}" if nombre_guardado else "NUEVO PROSPECTO"
        respuesta_embudo = embudo_ventas_gemini(texto, nombre_guardado)
        enviar_mensaje(telefono, respuesta_embudo, nombre_mostrar)
        return

    if sesion.get("estado") == "esperando_fecha":
        borrar_sesion(telefono)
        px_confirm = sesion.get("px_confirmados", [])
        msg_base = f"Hola {pila},\n\nConfirmacion registrada.\n\nLos esperamos en el *Hotel Jose Antonio Deluxe*, Mesa de registro a las *9:00 am*." + FIRMA
        enviar_mensaje(telefono, humanizar_con_gemini(texto, msg_base, pila, es_pregunta_compleja=False), imo_nombre_completo)
        return

    if sesion.get("estado") == "esperando_confirmacion":
        if es_confirmacion(texto):
            extraidos = sesion.get("extraidos", [])
            actualizar_excel(extraidos, telefono)
            confirmados = [e for e in extraidos if e["estatus"] == "CONFIRMADO"]
            if confirmados:
                px_nombres = [e["px"] for e in confirmados]
                set_sesion(telefono, {"estado": "esperando_fecha", "px_confirmados": px_nombres, "primera_vez": False}) 
                enviar_mensaje(telefono, r_pedir_fecha(pila, px_nombres), imo_nombre_completo)
            else:
                borrar_sesion(telefono)
                msg_base = f"Gracias {pila}, todo quedo registrado. Te hemos quitado estas personas de tu lista de pendientes." + FIRMA
                enviar_mensaje(telefono, humanizar_con_gemini(texto, msg_base, pila, es_pregunta_compleja=False), imo_nombre_completo)
        else:
            borrar_sesion(telefono)
            enviar_mensaje(telefono, "Comprendido. Por favor vuelvenos a enviar el estatus de tus personas." + STOP_CLAUSULA, imo_nombre_completo)
        return

    if not px_list:
        if intencion in ("INFO_C1", "VOLANTE"): enviar_mensaje(telefono, humanizar_con_gemini(texto, r_volante(pila), pila, es_pregunta_compleja=True), imo_nombre_completo); return
        if intencion == "CAMBIO": enviar_mensaje(telefono, humanizar_con_gemini(texto, r_cambio(pila), pila, es_pregunta_compleja=False), imo_nombre_completo); return
        enviar_mensaje(telefono, humanizar_con_gemini(texto, f"Hola {pila},\n\nYa tienes el estatus registrado para todas tus personas pendientes. Si hay algun cambio antes del *1 de mayo*, escribenos." + FIRMA, pila, es_pregunta_compleja=False), imo_nombre_completo)
        return

    respuestas_info = {
        "QUIEN_ERES": r_quien_eres(pila), "CAMBIO": r_cambio(pila), "DEVOLUCION": r_devolucion(pila),
        "INFO_C1": r_info_c1(pila), "NO_RECUERDA": r_no_recuerda(pila), "VOLANTE": r_volante(pila), "CONSULTA_PX": r_consulta_px(pila)
    }
    if intencion in respuestas_info:
        enviar_mensaje(telefono, humanizar_con_gemini(texto, respuestas_info[intencion], pila, es_pregunta_compleja=True), imo_nombre_completo)
        return

    extraidos = buscar_px_en_texto(texto, px_list)

    if not extraidos:
        respuestas_estados = {
            "NO_INTERESADO": r_no_interesado(pila, px_list), "NO_CONTESTA": r_no_contesta(pila, px_list),
            "PENDIENTE": r_pendiente(pila, px_list), "GESTIONANDO": r_pendiente(pila, px_list),
            "SIGUIENTE": f"Hola {pila},\n\nRecibido. Las inscripciones siguen activas para el siguiente equipo." + FIRMA,
            "YA_SE_SENTO": r_ya_sento(pila), "FALLECIO_ENFERMO": r_fallecio_enfermo(pila)
        }
        if intencion in respuestas_estados:
            enviar_mensaje(telefono, humanizar_con_gemini(texto, respuestas_estados[intencion], pila, es_pregunta_compleja=False), imo_nombre_completo)
            return
        
        enviar_mensaje(telefono, humanizar_con_gemini(texto, r_no_entendido(pila, px_list), pila, es_pregunta_compleja=True), imo_nombre_completo)
        return

    es_primera = sesion.get("primera_vez", True)
    set_sesion(telefono, {"estado": "esperando_confirmacion", "extraidos": extraidos, "primera_vez": es_primera})
    no_mencionados = [px for px in px_list if not any(normalizar(px.split()[0]) == normalizar(e["px"].split()[0]) for e in extraidos)]
    
    msg = f"Perfecto {pila}, registre lo siguiente:\n\n{formatear_resumen(extraidos)}"
    if no_mencionados: msg += "\n\n⚠️ Faltaron:\n" + "\n".join(f"• {p}" for p in no_mencionados) + "\nPuedes incluirlas luego."
    msg += "\n\n¿Esta correcto? Responde *SI* para confirmar."
    enviar_mensaje(telefono, msg, imo_nombre_completo)

# ══════════════════════════════════════════════════════════════════════════
# PANEL WEB HTML
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
        .status-dot { width: 10px; height: 10px; background: #00a884; border-radius: 50%; display: inline-block; margin-right: 5px; box-shadow: 0 0 5px #00a884; }
        .contacts-list { flex: 1; overflow-y: auto; }
        .contact-item { padding: 15px 20px; border-bottom: 1px solid var(--border); cursor: pointer; transition: background 0.2s; display: flex; align-items: center; }
        .contact-item:hover, .contact-item.active { background: #f0f2f5; }
        .avatar { width: 45px; height: 45px; background: #dfe5e7; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin-right: 15px; font-size: 20px; flex-shrink: 0;}
        .contact-info { flex: 1; min-width: 0; }
        .contact-info h4 { margin-bottom: 4px; font-weight: 500; font-size:15px; color: #111b21;}
        .contact-info p { font-size: 13px; color: var(--text-muted); text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
        .chat-area { flex: 1; display: flex; flex-direction: column; background: var(--bg-chat); position: relative; }
        .chat-area::before { content: ''; position: absolute; top:0; left:0; right:0; bottom:0; background-image: url('https://user-images.githubusercontent.com/15075759/28719144-86dc0f70-73b1-11e7-911d-60d70fcded21.png'); opacity: 0.06; pointer-events: none; z-index: 0; }
        .chat-header { background: #f0f2f5; padding: 15px 25px; font-weight: 500; border-bottom: 1px solid var(--border); z-index: 1; display: flex; align-items: center; }
        .messages-container { flex: 1; padding: 30px; overflow-y: auto; z-index: 1; display: flex; flex-direction: column; scroll-behavior: smooth; }
        .message { max-width: 65%; padding: 8px 12px; border-radius: 8px; margin-bottom: 12px; position: relative; font-size: 14.5px; line-height: 1.4; box-shadow: 0 1px 1px rgba(0,0,0,0.1); word-wrap: break-word; }
        .message.sent { align-self: flex-end; background: var(--chat-bubble-out); border-top-right-radius: 0; }
        .message.received { align-self: flex-start; background: #ffffff; border-top-left-radius: 0; }
        .message .time { font-size: 11px; color: var(--text-muted); float: right; margin-top: 5px; margin-left: 15px; }
        .chat-input-area { background: #f0f2f5; padding: 15px 25px; display: flex; align-items: center; z-index: 1; gap: 15px; }
        .chat-input-area textarea { flex: 1; border: none; padding: 12px 15px; border-radius: 8px; resize: none; outline: none; font-size: 15px; }
        .send-btn { background: var(--primary); color: white; border: none; width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; transition: 0.2s; flex-shrink:0; }
        .send-btn:hover { background: #005c4b; }
        .hidden { display: none !important; }
        .empty-state { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; z-index: 1; color: var(--text-muted); text-align: center; padding: 20px;}
        .sync-btn { background: #e9edef; border: 1px solid #ccc; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; }
        .sync-btn:hover { background: #d1d7db; }
        .sync-btn.loading { background: #ffe082; pointer-events: none; }
        .download-btn { background: #00a884; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; text-decoration: none;}
        .download-btn:hover { background: #008069; }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <div>💬 Panel de Chats</div>
                <div style="font-size:12px; font-weight:normal; display:flex; align-items:center; gap:8px;">
                    <a href="/api/descargar_respaldo" class="download-btn">📥 Respaldo</a>
                    <button class="sync-btn" id="syncBtn" onclick="forceSync()">🔄 Sync</button>
                </div>
            </div>
            <div class="contacts-list" id="contactsList"></div>
        </div>
        <div class="chat-area" id="chatArea">
            <div class="empty-state" id="emptyState">
                <div style="font-size: 50px; margin-bottom: 20px;">🚀</div>
                <h2 style="color: #41525d; font-weight: 300;">Creación Cuántica Web</h2>
                <p style="margin-top: 10px; font-size:14px;">Selecciona un chat de la columna izquierda para responder a tus líderes.</p>
            </div>
            <div class="chat-header hidden" id="chatHeader">
                <div class="avatar">👤</div>
                <h3 id="chatHeaderName" style="color: #111b21;"></h3>
            </div>
            <div class="messages-container hidden" id="messagesContainer"></div>
            <div class="chat-input-area hidden" id="chatInputArea">
                <textarea id="messageInput" rows="1" placeholder="Escribe tu respuesta aquí..." onkeydown="handleEnter(event)"></textarea>
                <button class="send-btn" onclick="sendMessage()">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
                </button>
            </div>
        </div>
    </div>
    <script>
        let chatHistory = {}; let activeContact = null; let isUserScrolling = false;
        
        document.getElementById('messagesContainer').addEventListener('scroll', function() {
            isUserScrolling = (this.scrollHeight - this.scrollTop - this.clientHeight) > 50;
        });

        async function cargarDatos() {
            try {
                let res = await fetch('/api/historial'); let data = await res.json();
                let newHistory = {};
                for(let m of data) {
                    if (!newHistory[m.telefono]) newHistory[m.telefono] = { nombre: "", messages: [] };
                    if (m.nombre) newHistory[m.telefono].nombre = m.nombre;
                    newHistory[m.telefono].messages.push({ text: m.texto, time: m.hora, sent: m.tipo === 'out' });
                }
                chatHistory = newHistory; renderContacts(); if (activeContact) renderMessages(false);
            } catch (e) { }
        }

        async function forceSync() {
            const btn = document.getElementById('syncBtn');
            btn.classList.add('loading'); btn.innerText = "⏳...";
            try {
                await fetch('/api/force_sync', {method: 'POST'});
                setTimeout(async () => {
                    await cargarDatos();
                    btn.classList.remove('loading'); btn.innerText = "🔄 Sync";
                }, 4000);
            } catch(e) { btn.classList.remove('loading'); btn.innerText = "🔄 Sync"; }
        }

        function renderContacts() {
            const list = document.getElementById('contactsList'); list.innerHTML = '';
            const phones = Object.keys(chatHistory).reverse();
            if(phones.length === 0) { list.innerHTML = '<div style="padding: 20px; text-align: center; color: #888;">No hay chats recientes. Haz clic en Sync.</div>'; return; }
            phones.forEach(phone => {
                const contactData = chatHistory[phone]; 
                const lastMessage = contactData.messages[contactData.messages.length - 1].text;
                const displayName = contactData.nombre ? contactData.nombre : `+${phone}`;

                const div = document.createElement('div');
                div.className = `contact-item ${activeContact === phone ? 'active' : ''}`;
                div.onclick = () => openChat(phone, displayName);
                div.innerHTML = `
                    <div class="avatar">👤</div>
                    <div class="contact-info">
                        <h4>${displayName}</h4>
                        <p>${lastMessage}</p>
                    </div>`;
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
            isUserScrolling = false; renderContacts(); renderMessages(true);
            setTimeout(() => document.getElementById('messageInput').focus(), 100);
        }

        function renderMessages(forceBottom) {
            const container = document.getElementById('messagesContainer'); container.innerHTML = '';
            if (!activeContact || !chatHistory[activeContact]) return;
            chatHistory[activeContact].messages.forEach(msg => {
                const div = document.createElement('div'); div.className = `message ${msg.sent ? 'sent' : 'received'}`;
                div.innerHTML = `${msg.text.replace(/\\n/g, '<br>')}<span class="time">${msg.time}</span>`;
                container.appendChild(div);
            });
            if (forceBottom || !isUserScrolling) container.scrollTop = container.scrollHeight;
        }

        function handleEnter(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }

        async function sendMessage() {
            const textarea = document.getElementById('messageInput'); const mensaje = textarea.value.trim(); const destino = activeContact;
            if (!mensaje || !destino) return;
            textarea.value = '';
            chatHistory[destino].messages.push({ text: mensaje, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}), sent: true });
            isUserScrolling = false; renderMessages(true); renderContacts();
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

# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS Y RUTAS WEB
# ══════════════════════════════════════════════════════════════════════════

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
        tipo_str = "Bot/Panel envió" if m.get("tipo") == "out" else "IMO/Prospecto respondió"
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
            imo_nombre = f"NUEVO PROSPECTO: {nm}" if nm else "NUEVO PROSPECTO"
            
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
            
            # Nombre para mostrar si es prospecto
            nombre_mostrar = imo_nombre_sheet
            if not imo_nombre_sheet:
                sesion = get_sesion(telefono)
                nm = sesion.get("nombre_prospecto")
                # Si no tenía nombre y nos lo dio recién en este mensaje, lo atrapamos
                if not nm and len(texto.split()) <= 3 and len(texto) > 2:
                    nm = nombre_pila(texto)
                nombre_mostrar = f"NUEVO PROSPECTO: {nm}" if nm else "NUEVO PROSPECTO"
            
            append_historial(telefono, nombre_mostrar, texto, "in")
            procesar_mensaje(telefono, texto, imo_nombre_sheet)
            
            # Actualizar nombre por si la IA lo extrajo en este turno
            sesion_updated = get_sesion(telefono)
            if not imo_nombre_sheet:
                nm_updated = sesion_updated.get("nombre_prospecto")
                nombre_mostrar = f"NUEVO PROSPECTO: {nm_updated}" if nm_updated else "NUEVO PROSPECTO"

            respuesta_enviada = _respuestas_enviadas.pop(str(telefono), "")
            if respuesta_enviada:
                registrar_en_sheets(telefono, nombre_mostrar, texto, respuesta_enviada[:500], "EMBUDO" if not imo_nombre_sheet else "")
            
        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono, "Comprendido. Por favor responde con texto para poder registrar tu respuesta en nuestro sistema. No procesamos archivos multimedia.", "")
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): return jsonify({"status": "activo", "version": "v19_memoria_arreglada"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    threading.Thread(target=forzar_sincronizacion_sheets, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
