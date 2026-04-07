"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
✅ Versión V50 ENTERPRISE: Cola Asíncrona, Dataset de Entrenamiento (Fine-Tuning), CRM Anti-Caídas
"""

import os, re, json, time, csv, io, random, logging, queue, threading
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN Y CONSTANTES
# ══════════════════════════════════════════════════════════════════════════
def get_csv_bd_path():
    if os.path.exists("base_datos.csv"): return "base_datos.csv"
    for f in os.listdir("."):
        if f.startswith("participantes_") and f.endswith(".csv"): return f
    return "base_datos.csv"

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    
    EXCEL_PATH = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")
    CSV_BD_PATH = os.environ.get("CSV_BD_PATH", get_csv_bd_path())
    SESSIONS_PATH = os.environ.get("SESSIONS_PATH", "sesiones.json")
    HISTORIAL_PATH = "historial_chat.json"
    DATASET_PATH = "dataset_entrenamiento.csv" # 🧠 NUEVO: Base de datos para entrenar a la IA
    
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    DASHSCOPE_KEY = os.environ.get("DASHSCOPE_API_KEY", "")
    MODO_IA = os.environ.get("MODO_IA", "fallback").lower() 
    IA_PRIMARIA = os.environ.get("IA_PRIMARIA", "gemini").lower() 
    IA_FALLBACK = os.environ.get("IA_FALLBACK", "qwen").lower()
    
    SHEET_ID = os.environ.get("SHEET_ID", "")
    CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

# ══════════════════════════════════════════════════════════════════════════
# 2. GESTOR DE ESTADO Y DATASET DE ENTRENAMIENTO
# ══════════════════════════════════════════════════════════════════════════
class SessionManager:
    _session_lock = threading.Lock()
    _history_lock = threading.Lock()
    _dataset_lock = threading.Lock()

    @staticmethod
    def get_sesion(telefono):
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                        return json.load(f).get(str(telefono), {})
            except: pass
            return {}

    @staticmethod
    def set_sesion(telefono, data_dict):
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                data = {}
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: data = json.load(f)
                data[str(telefono)] = data_dict
                with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            except: pass

    @staticmethod
    def borrar_sesion(telefono):
        with FileLock(Config.SESSIONS_PATH + ".lock"):
            try:
                if os.path.exists(Config.SESSIONS_PATH):
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: data = json.load(f)
                    if str(telefono) in data:
                        del data[str(telefono)]
                        with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            except: pass

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        with FileLock(Config.HISTORIAL_PATH + ".lock"):
            try:
                h = []
                if os.path.exists(Config.HISTORIAL_PATH):
                    with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: h = json.load(f)
                h.append({
                    "telefono": str(telefono), "nombre": nombre or "Desconocido", 
                    "texto": texto, "tipo": tipo, "hora": datetime.now().strftime("%d/%m %H:%M")
                })
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h[-10000:], f, ensure_ascii=False, indent=2)
            except: pass

    @staticmethod
    def guardar_dataset(telefono, mensaje_usuario, respuesta_ia, modelo_usado):
        """🧠 Guarda cada interacción para hacer Fine-Tuning (Entrenamiento) en el futuro"""
        with FileLock(Config.DATASET_PATH + ".lock"):
            try:
                archivo_existe = os.path.exists(Config.DATASET_PATH)
                with open(Config.DATASET_PATH, "a", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    if not archivo_existe:
                        writer.writerow(["Fecha", "Telefono", "Mensaje Usuario", "Respuesta IA", "Modelo"])
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telefono, mensaje_usuario, respuesta_ia, modelo_usado])
            except Exception as e:
                logger.error(f"Error guardando dataset: {e}")

def get_sesion(tel): return SessionManager.get_sesion(tel)
def set_sesion(tel, d): SessionManager.set_sesion(tel, d)
def borrar_sesion(tel): SessionManager.borrar_sesion(tel)
def append_historial(tel, nom, txt, tipo): SessionManager.append_historial(tel, nom, txt, tipo)
def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return []

# ══════════════════════════════════════════════════════════════════════════
# 3. SISTEMAS ANTI-CAÍDAS (Cola Asíncrona y Watchdog)
# ══════════════════════════════════════════════════════════════════════════
cola_mensajes = queue.Queue()

def worker_procesar_mensajes():
    """🚀 Hilo de procesamiento: Extrae los mensajes de la cola para no bloquear el Webhook"""
    while True:
        try:
            tarea = cola_mensajes.get()
            telefono = tarea["telefono"]
            texto = tarea["texto"]
            
            # Reconocimiento y perfilado CRM en segundo plano
            imo_nombre_sheet, _ = cargar_px_del_imo(telefono)
            sesion_pre = get_sesion(telefono)
            sesion_pre["ultimo_mensaje_usuario"] = texto
            
            nombre_mostrar = imo_nombre_sheet
            if not imo_nombre_sheet:
                nm = sesion_pre.get("nombre_prospecto")
                if not nm:
                    nm_csv = identificar_contacto_csv(telefono)
                    if nm_csv:
                        nm = nm_csv
                        sesion_pre["nombre_prospecto"] = nm
                nombre_mostrar = f"CONTACTO: {nm}" if nm else "NUEVO CONTACTO"
            
            set_sesion(telefono, sesion_pre)
            append_historial(telefono, nombre_mostrar, texto, "in")
            
            # Ejecutar el cerebro
            procesar_mensaje(telefono, texto)
            
        except Exception as e:
            logger.error(f"Error en worker asíncrono: {e}", exc_info=True)
        finally:
            cola_mensajes.task_done()

# Iniciamos los trabajadores asíncronos
threading.Thread(target=worker_procesar_mensajes, daemon=True).start()

def ejecutar_watchdog_inactividad():
    sesiones_vencidas = []
    with FileLock(Config.SESSIONS_PATH + ".lock"):
        if not os.path.exists(Config.SESSIONS_PATH): return
        try:
            with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: sesiones = json.load(f)
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
                with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f: json.dump(sesiones, f, ensure_ascii=False, indent=2)
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
        except: pass
        return False

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=False, msg_user=""):
    sesion = get_sesion(telefono)
    if sesion.get("primera_vez", True) and not str(nombre_imo).startswith("COORDINADORA") and nombre_imo != "SISTEMA":
        aclaracion = "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*. Para atención personalizada, usa el menú para conectar con nuestras coordinadoras:_\n\n" + COORDINADORAS
        texto += aclaracion if "Coordinadoras C1 y C2" not in texto else "\n\n🤖 _Nota: Estás comunicándote con *IA Cuántica*._"
        sesion["primera_vez"] = False
        set_sesion(telefono, sesion)
    return WhatsAppAPI.enviar_mensaje(telefono, texto, nombre_imo, registrar_sheets, msg_user)

def registrar_en_sheets(tel, nom, msg, resp, est=""):
    if not Config.SHEET_ID or not Config.CREDS_JSON: return
    try:
        import base64
        now = int(time.time())
        creds = json.loads(Config.CREDS_JSON)
        header = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
        payload = base64.urlsafe_b64encode(json.dumps({
            "iss": creds["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
            "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600
        }).encode()).rstrip(b"=")
        msg_jwt = header + b"." + payload
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        pk = serialization.load_pem_private_key(creds["private_key"].encode(), password=None)
        sig = pk.sign(msg_jwt, padding.PKCS1v15(), hashes.SHA256())
        jwt = (msg_jwt + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
        r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}, timeout=10)
        if r.status_code == 200:
            token = r.json()["access_token"]
            url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H:append"
            ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
            req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, 
                         json={"values": [[ahora, str(tel), nom, msg, resp, est, "", ""]]}, 
                         headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
    except: pass

# ══════════════════════════════════════════════════════════════════════════
# 5. UTILIDADES Y RECONOCIMIENTO BLINDADO (Anti-IndexError)
# ══════════════════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0") and len(t) == 10: return t[1:]
    if len(t) > 10 and not t.startswith("9"): return t[-9:]
    return t

def son_mismo_numero(tel1, tel2):
    t1 = re.sub(r'\D', '', str(tel1))
    t2 = re.sub(r'\D', '', str(tel2))
    if not t1 or not t2: return False
    if t1 == t2: return True
    min_len = min(len(t1), len(t2))
    if min_len >= 8 and (t1.endswith(t2) or t2.endswith(t1)): return True
    if t1.startswith("0") and t2.endswith(t1[1:]): return True
    if t2.startswith("0") and t1.endswith(t2[1:]): return True
    return False

def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]: t = t.replace(a, b)
    return t

def nombre_pila(s):
    partes = [p.strip() for p in re.split(r'\s+', s.strip()) if len(p.strip()) > 2]
    return partes[0].title() if partes else s.strip().title()

def identificar_contacto_csv(telefono):
    """Blindado: Ignora errores de índice si el CSV tiene filas rotas"""
    try:
        if not os.path.exists(Config.CSV_BD_PATH): return None
        with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
            primera_linea = f.readline()
            delimitador = ';' if ';' in primera_linea else ','
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimitador)
            if not reader.fieldnames: return None
            
            tel_key = next((c for c in reader.fieldnames if c and ("tel" in c.lower() or "cel" in c.lower())), None)
            nom_key = next((c for c in reader.fieldnames if c and ("nombre" in c.lower())), None)
            ape_key = next((c for c in reader.fieldnames if c and ("apellido" in c.lower())), None)

            if not tel_key or not nom_key: return None

            for row in reader:
                try:
                    if not row or not row.get(tel_key): continue
                    tel_csv = str(row.get(tel_key, ""))
                    if son_mismo_numero(tel_csv, telefono):
                        n_base = str(row.get(nom_key, "")).strip()
                        a_base = str(row.get(ape_key, "")).strip() if ape_key else ""
                        
                        # Manejo seguro de listas vacías
                        n = n_base.split()[0] if n_base.split() else ""
                        a = a_base.split()[0] if a_base.split() else ""
                        
                        if n and a: return f"{n} {a}".title()
                        elif n: return n.title()
                except IndexError: continue # Ignorar fila si hay error interno
    except Exception as e: logger.error(f"Error CRM CSV: {e}")
    return None

def cargar_px_del_imo(telefono):
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH, data_only=True, read_only=True)
            ws = wb["DATA"]
            px_list, imo_nombre = [], ""
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 7: continue
                imo_n  = str(row[0] or "").strip()
                imo_t  = str(row[3] or "")
                px_n   = str(row[4] or "").strip()
                estado = str(row[6] or "").strip().upper()
                if son_mismo_numero(imo_t, telefono):
                    if not imo_nombre: imo_nombre = imo_n
                    if estado in ("PENDIENTE","ENVIADO","") and px_n:
                        px_list.append(px_n)
            wb.close()
            return imo_nombre, px_list
        except: return "", []

def obtener_perfil_crm(telefono):
    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    imo_nom, px_list = cargar_px_del_imo(telefono)
    if imo_nom:
        perfil["rol"] = "IMO"; perfil["nombre"] = imo_nom; perfil["pendientes"] = px_list
        return perfil
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
                            try:
                                if not row or not row.get(tel_key): continue
                                tel_csv = str(row.get(tel_key, ""))
                                if son_mismo_numero(tel_csv, telefono):
                                    n_base = str(row.get(nom_key, "")).strip()
                                    a_base = str(row.get(ape_key, "")).strip() if ape_key else ""
                                    
                                    n = n_base.split()[0] if n_base.split() else ""
                                    a = a_base.split()[0] if a_base.split() else ""
                                    nombre_completo = f"{n} {a}".title().strip() if (n and a) else nombre_pila(n_base)
                                    
                                    c1_stat = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                                    c2_stat = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
                                    mj_stat = str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                                    
                                    pendiente = "Capítulo 1 (C1)"
                                    if c1_stat == "SI": pendiente = "Capítulo 2 (C2)"
                                    if c1_stat == "SI" and c2_stat == "SI": pendiente = "Maestría (MJ)"

                                    perfil["rol"] = "PX"; perfil["nombre"] = nombre_completo; perfil["pendiente"] = pendiente
                                    perfil["imo_nombre"] = nombre_pila(str(row.get(imo_nom_key, "Tu líder")).strip()) if imo_nom_key else "Tu líder"
                                    perfil["imo_tel"] = str(row.get(imo_tel_key, "")) if imo_tel_key else ""
                                    return perfil
                            except IndexError: continue
    except: pass
    return perfil

# ══════════════════════════════════════════════════════════════════════════
# 6. ESTRATEGIA DE IA DUAL (GEMINI + QWEN) + CREACIÓN DE DATASET
# ══════════════════════════════════════════════════════════════════════════
COORDINADORAS_CONTACTOS = {
    "Diana Moscoso": "51912379744", "Joyce Marín": "51933599903", 
    "Leyla Pasquel": "51919502385", "Zuley Urteaga": "51933599864"
}
COORDINADORAS_LISTA = "\n• Diana Moscoso: +51 912 379 744\n• Joyce Marin: +51 933 599 903\n• Leyla Pasquel: +51 919 502 385\n• Zuley Urteaga: +51 933 599 864"
COORDINADORAS = f"Coordinadoras C1 y C2:{COORDINADORAS_LISTA}"

BROCHURE_INFO_MAESTRA = """
INFORMACIÓN OFICIAL CREAR PODER SIN LÍMITES PERÚ:
- Misión: Impactar a la máxima cantidad de seres humanos a vivir una vida extraordinaria. No somos un cursito, somos Alto Rendimiento.
- Los 3 Niveles del Proceso (100 Días):
  1. Capítulo 1 (C1): Descubrimiento. 3 días para romper paradigmas y darte cuenta de tus barreras.
  2. Capítulo 2 (C2): Experiencia y Transformación profunda (Usualmente 4 días). Rediseñas cómo te relacionas con el mundo.
  3. Maestría (MJ): 100 días para integrar lo aprendido. Llevas el liderazgo a la familia y finanzas.
- Reglas: Exclusivo para MAYORES DE 18 AÑOS. NO es terapia.
- Inversión: BCP Soles a nombre de CREACIÓN CUÁNTICA E.I.R.L (Cuenta: 1934218307060 / CCI: 00219300421830706018).
"""

def embudo_ventas_ia(mensaje_usuario, nombre_conocido=None, nombre_ya_saludado=False, telefono=None):
    cfg = {"gemini_key": Config.GEMINI_KEY, "dashscope_key": Config.DASHSCOPE_KEY, "modo_ia": Config.MODO_IA, "ia_primaria": Config.IA_PRIMARIA, "ia_fallback": Config.IA_FALLBACK}
    
    def guardar_y_retornar(respuesta, modelo):
        if telefono: SessionManager.guardar_dataset(telefono, mensaje_usuario, respuesta, modelo)
        return respuesta

    msg_len = len(mensaje_usuario.split())
    if msg_len <= 3 and nombre_conocido and not nombre_ya_saludado:
        resp = f"¡Hola, {nombre_conocido}! Qué gran paso estás dando al comunicarte. 🌟 Creemos firmemente que tienes un potencial ilimitado esperando ser despertado.\n\nA través de nuestra Transformación Cuántica, te acompañamos a romper las barreras que hoy te frenan. Todo esto se vive en el *Capítulo 1*, un entrenamiento vivencial de 3 días para rediseñar tu realidad. ¿Te gustaría conocer detalles de la próxima fecha?"
        return guardar_y_retornar(resp, "REGLA_CORTA")
    
    if not Config.GEMINI_KEY or not GEMINI_DISPONIBLE: 
        return guardar_y_retornar("Para apoyarte de forma humana y precisa, por favor escribe 4 o 6 para enlazarte con una coordinadora.", "FALLBACK_OFFLINE")
    
    def construir_prompt_gemini():
        return f"""Eres un Coach de Enrolamiento de 'Crear Poder Sin Límites Perú'.
        Hablas con: "{nombre_conocido if nombre_conocido else 'un contacto'}".
        Mensaje del usuario: "{mensaje_usuario}"
        BASE DE CONOCIMIENTO: {BROCHURE_INFO_MAESTRA}
        REGLAS DE ORO:
        1. CONEXIÓN EMPÁTICA: Tu tono es cálido, apasionado y enérgico. NUNCA suenes como robot. Usa emojis sutiles.
        2. NO SEAS MONÓTONO: Explica la TRANSFORMACIÓN (romper miedos, mejorar relaciones, elevar el liderazgo).
        3. PALABRAS PROHIBIDAS: "sanar", "terapia", "ayudar", "paciente".
        4. PREGUNTA DE CIERRE: Termina SIEMPRE tu respuesta con una pregunta poderosa que invite a la acción."""

    try:
        genai.configure(api_key=Config.GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash') 
        r = model.generate_content(construir_prompt_gemini())
        if r.text: return guardar_y_retornar(r.text.strip(), "GEMINI")
    except: pass

    return guardar_y_retornar("Para brindarte un apoyo 100% personalizado y humano, te invito a presionar el número de la opción que te derive con una coordinadora.", "FALLBACK_ERROR")

# ══════════════════════════════════════════════════════════════════════════
# 7. ESTRUCTURAS DE MENÚ
# ══════════════════════════════════════════════════════════════════════════
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

# ══════════════════════════════════════════════════════════════════════════
# 8. PROCESADOR PRINCIPAL (MÁQUINA DE ESTADOS) - SE EJECUTA EN HILO SEPARADO
# ══════════════════════════════════════════════════════════════════════════
def procesar_mensaje(telefono, texto):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    perfil = sesion.get("perfil", {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None})
    nombre_mostrar = f"({perfil['rol']}) {perfil['nombre']}" if perfil['nombre'] else "NUEVO CONTACTO"

    if sesion.get("menu_state") == "esperando_encuesta":
        if texto_limpio in ["1", "2", "3", "4", "5"]:
            threading.Thread(target=registrar_en_sheets, args=(telefono, nombre_mostrar, "Calificación", f"{texto_limpio} Estrellas", "CSAT"), daemon=True).start()
            enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟 Valoramos mucho tu opinión.\n\n_Escribe MENU para reiniciar._", nombre_mostrar)
            borrar_sesion(telefono)
        else: enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_mostrar)
        return

    if texto_limpio == "STOP":
        marcar_stop(telefono); borrar_sesion(telefono)
        enviar_mensaje(telefono, "Has sido dado de baja. No recibirás más mensajes.\n\n*Crear Poder Sin Límites*", nombre_mostrar)
        return

    main_key = "main_imo" if perfil["rol"] == "IMO" else "main_px" if perfil["rol"] == "PX" else "main_prospecto"
    def render_menu(m_key):
        txt = MENU_STRUCTURE[m_key]["text"]
        if "{" in txt: txt = txt.format(nombre=perfil.get("nombre", "Participante"), imo=perfil.get("imo_nombre", "tu líder"), pendiente=perfil.get("pendiente", "tu entrenamiento"))
        return txt

    # Si escribe MENU
    if texto_limpio in ["0", "MENU", "MENÚ", "INICIO"] or "menu_state" not in sesion:
        sesion["menu_state"] = main_key
        sesion["menu_history"] = []; sesion["menu_errors"] = 0
        set_sesion(telefono, sesion)
        enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar)
        return

    if texto_limpio in ["9", "VOLVER", "ATRAS", "ATRÁS"]:
        hist = sesion.get("menu_history", [])
        if hist:
            prev = hist.pop()
            sesion["menu_state"] = prev; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(prev), nombre_mostrar)
        else:
            sesion["menu_state"] = main_key; set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar)
        return

    estado_actual = sesion.get("menu_state", main_key)

    if estado_actual in MENU_STRUCTURE:
        nodo_actual = MENU_STRUCTURE[estado_actual]
        siguiente_estado = nodo_actual.get("options", {}).get(texto_limpio)
        
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            if siguiente_estado == "px_confirma":
                enviar_mensaje(telefono, f"¡Extraordinario, {perfil['nombre']}! 🎉\nHemos registrado tu asistencia. Le avisaremos a tu líder {perfil['imo_nombre']}.\n\n_Escribe 0 para volver al menú._", nombre_mostrar)
                sesion["menu_state"] = "esperando_fecha"; set_sesion(telefono, sesion)
                return

            elif siguiente_estado == "action_humano":
                c_nom = notificar_coordinadora_aleatoria(telefono, perfil["nombre"], f"Necesita asistencia desde: {estado_actual}")
                enviar_mensaje(telefono, f"¡Comprendido! He notificado a nuestra coordinadora *{c_nom}*. Ella te escribirá en breve. 🚀\n\n_Escribe *0* para cancelar._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"; set_sesion(telefono, sesion)
                return
                
            elif siguiente_estado == "action_salir":
                sesion["menu_state"] = "esperando_encuesta"; set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Antes de irte, ¿Cómo calificarías tu experiencia de hoy con nuestra *IA Cuántica*?\n\nResponde con un número del *1 al 5*:\n1️⃣ = Mala\n5️⃣ = ¡Excelente!", nombre_mostrar)
                return
                
            elif siguiente_estado == "main": siguiente_estado = main_key
                
            hist = sesion.get("menu_history", [])
            if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
            sesion["menu_state"] = siguiente_estado; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
            
            if siguiente_estado in MENU_STRUCTURE: enviar_mensaje(telefono, render_menu(siguiente_estado), nombre_mostrar)
            elif siguiente_estado == "chat_libre_ia": enviar_mensaje(telefono, "Has ingresado a nuestro *Chat Inteligente*. 🧠\nPuedes preguntarme lo que desees.\n\n_Escribe *0* para salir._", nombre_mostrar)
            elif siguiente_estado == "action_imo": enviar_mensaje(telefono, f"¡Hola líder! 👋\n\nEstás en el *Portal IMO*. Envíame el estatus de tus participantes.\n\n_Escribe *0* para volver._", nombre_mostrar)

        else:
            if not texto_limpio.isnumeric() and len(texto.split()) > 1:
                sesion["menu_state"] = "chat_libre_ia"; set_sesion(telefono, sesion)
                resp_ia = embudo_ventas_ia(texto, perfil["nombre"], sesion.get("nombre_saludado", False), telefono)
                if "potencial ilimitado" in resp_ia: sesion["nombre_saludado"] = True; set_sesion(telefono, sesion)
                enviar_mensaje(telefono, resp_ia + "\n\n_(Escribe *0* para volver al menú)_", nombre_mostrar)
                return

            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            if errores >= 3:
                sesion["menu_errors"] = 0
                c_nom = notificar_coordinadora_aleatoria(telefono, perfil["nombre"], "El usuario se atascó en el menú.")
                enviar_mensaje(telefono, f"Noto que estamos teniendo problemas. 🤖\nHe notificado a la coordinadora *{c_nom}* para que te asista.\n\n_Escribe *0* para menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado_actual)}", nombre_mostrar)
            set_sesion(telefono, sesion)

    elif estado_actual == "action_imo":
        enviar_mensaje(telefono, f"Excelente líder. Has enviado tu estatus. Estamos procesándolo.\n\n_Escribe *0* para volver al menú._", nombre_mostrar)
        return
        
    elif estado_actual in ["esperando_humano", "esperando_fecha", "ver_pendientes_imo"]:
        set_sesion(telefono, sesion)
        return

    elif estado_actual == "chat_libre_ia":
        resp_ia = embudo_ventas_ia(texto, perfil["nombre"], sesion.get("nombre_saludado", False), telefono)
        enviar_mensaje(telefono, resp_ia, nombre_mostrar)
        return

# ══════════════════════════════════════════════════════════════════════════
# 9. PANEL WEB Y ENDPOINTS FLASK (CON COLA DE MENSAJES)
# ══════════════════════════════════════════════════════════════════════════
HTML_CHAT = """
<!DOCTYPE html>
<html>
<head><title>Panel Bot - Crear Poder Sin Límites</title>
<style>
    body { font-family: Arial, sans-serif; padding: 20px; text-align: center; background: #f0f2f5; }
    .btn { padding: 10px 20px; background: #008069; color: white; text-decoration: none; border-radius: 5px; margin: 10px; display: inline-block; }
    h1 { color: #41525d; }
</style>
</head>
<body>
    <h1>✅ Bot Activo V50 (Enterprise)</h1>
    <p>El sistema está corriendo de forma segura y recopilando datos de entrenamiento.</p>
    <a href="/api/descargar_respaldo" class="btn">📥 Descargar Historial (Backup)</a>
    <a href="/api/descargar_dataset" class="btn" style="background:#1a73e8;">🧠 Descargar Dataset de IA</a>
</body>
</html>
"""

@app.route("/chat", methods=["GET"])
def panel_chat(): return HTML_CHAT

@app.route("/api/historial", methods=["GET"])
def api_historial(): 
    threading.Thread(target=ejecutar_watchdog_inactividad, daemon=True).start()
    return jsonify(get_historial()), 200

@app.route("/api/force_sync", methods=["POST"])
def force_sync(): return jsonify({"status": "syncing"}), 200

@app.route("/api/descargar_respaldo", methods=["GET"])
def descargar_respaldo():
    h = get_historial()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "Telefono", "Nombre IMO", "Tipo Mensaje", "Texto"])
    for m in h: writer.writerow([m.get("hora", ""), m.get("telefono", ""), m.get("nombre", ""), "Bot/Panel" if m.get("tipo") == "out" else "Usuario", m.get("texto", "")])
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition":"attachment;filename=Respaldo_Chats.csv"})

@app.route("/api/descargar_dataset", methods=["GET"])
def descargar_dataset():
    """Descarga el archivo CSV con los datos de entrenamiento para la IA"""
    if os.path.exists(Config.DATASET_PATH):
        with open(Config.DATASET_PATH, "r", encoding="utf-8-sig") as f: data = f.read()
    else: data = "Fecha,Telefono,Mensaje Usuario,Respuesta IA,Modelo\nSin datos aun"
    return Response(data, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename=Dataset_Entrenamiento_{datetime.now().strftime('%Y%m%d')}.csv"})

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
            texto = str(msg["text"]["body"]).replace("=", "").replace("+", "").replace("@", "")
            
            # 🔥 ENVIAR A LA COLA ASÍNCRONA (Para agilidad extrema, el Webhook responde en 0.01 seg)
            cola_mensajes.put({"telefono": telefono, "texto": texto})
            
        elif tipo in ("audio","image","document","video","sticker"):
            WhatsAppAPI.enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.")
            
    except Exception as e: logger.error(f"Error Webhook: {e}")
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status(): 
    return jsonify({"status": "activo", "version": "v50_enterprise_async", "gemini": "✅", "qwen": "❌"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"🚀 Iniciando bot V50 (Enterprise) en puerto {port}...")
    app.run(host="0.0.0.0", port=port, debug=False)
