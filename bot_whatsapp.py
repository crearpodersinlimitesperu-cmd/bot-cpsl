"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
✅ Versión V57 MASTER: CRM Total + IA Alternada (DeepSeek & Gemini) + Cero Qwen
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
DEEPSEEK_DISPONIBLE = True # Usamos API REST directa vía requests
genai = None

try:
    import google.generativeai as genai_module
    genai = genai_module
    GEMINI_DISPONIBLE = True
except ImportError: pass

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
    DATASET_PATH = "dataset_entrenamiento.csv"
    
    # 🧠 LLAVES DE INTELIGENCIA ARTIFICIAL
    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "sk-b77a476c9e17420aa89a1ee86ff44d6e") # LLAVE INCRUSTADA
    
    MODO_IA = os.environ.get("MODO_IA", "alternar").lower() # alternar, deepseek, o gemini
    
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
                    with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: return json.load(f).get(str(telefono), {})
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
                h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": datetime.now().strftime("%d/%m %H:%M")})
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h[-10000:], f, ensure_ascii=False, indent=2)
            except: pass

    @staticmethod
    def guardar_dataset(telefono, mensaje_usuario, respuesta_ia, modelo_usado):
        with FileLock(Config.DATASET_PATH + ".lock"):
            try:
                archivo_existe = os.path.exists(Config.DATASET_PATH)
                with open(Config.DATASET_PATH, "a", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    if not archivo_existe: writer.writerow(["Fecha", "Telefono", "Mensaje Usuario", "Respuesta IA", "Modelo"])
                    writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telefono, mensaje_usuario, respuesta_ia, modelo_usado])
            except: pass

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
# 3. SISTEMA DE COLAS (QUEUE) Y GOOGLE SHEETS
# ══════════════════════════════════════════════════════════════════════════
cola_mensajes = queue.Queue()
cola_sheets = queue.Queue()

class GoogleSheetsAPI:
    @classmethod
    def registrar_accion(cls, telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
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
                             json={"values": [[ahora, str(telefono), imo_nombre, mensaje, respuesta_bot, estado, "", ""]]}, 
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        except Exception as e: pass

def worker_sheets():
    while True:
        try:
            tarea = cola_sheets.get()
            GoogleSheetsAPI.registrar_accion(tarea['tel'], tarea['nom'], tarea['msg'], tarea['resp'], tarea['est'])
        except: pass
        finally: cola_sheets.task_done()

def worker_procesar_mensajes():
    while True:
        try:
            tarea = cola_mensajes.get()
            procesar_mensaje(tarea["telefono"], tarea["texto"])
        except Exception as e: logger.error(f"Error Worker Mensajes: {e}")
        finally: cola_mensajes.task_done()

threading.Thread(target=worker_sheets, daemon=True).start()
threading.Thread(target=worker_procesar_mensajes, daemon=True).start()

def registrar_en_sheets_async(tel, nom, msg, resp, est=""):
    if str(tel).startswith("SIM_"): return 
    cola_sheets.put({'tel': tel, 'nom': nom, 'msg': msg, 'resp': resp, 'est': est})

# ══════════════════════════════════════════════════════════════════════════
# 4. CONECTORES DE WHATSAPP API
# ══════════════════════════════════════════════════════════════════════════
class WhatsAppAPI:
    @staticmethod
    def enviar_mensaje(telefono, texto, nombre_mostrar="", registrar_sheets=False, mensaje_usuario=""):
        if str(telefono).startswith("SIM_"):
            SessionManager.append_historial(telefono, f"🤖 [BOT SIMULADO]", texto, "out")
            return True

        url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto, "preview_url": False}}
        try:
            r = req_lib.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                append_historial(telefono, nombre_mostrar, texto, "out")
                if registrar_sheets:
                    estado_actual = "SISTEMA" if nombre_mostrar == "SISTEMA" else "INTERACTIVO"
                    registrar_en_sheets_async(telefono, nombre_mostrar, mensaje_usuario or "[Bot]", texto[:500], estado_actual)
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

# ══════════════════════════════════════════════════════════════════════════
# 5. UTILIDADES, CSV, CAMBIO DE CUPO Y CRM OMNICANAL
# ══════════════════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0") and len(t) == 10: return t[1:]
    if len(t) > 10 and not t.startswith("9"): return t[-9:]
    return t

def son_mismo_numero(tel1, tel2):
    t1, t2 = re.sub(r'\D', '', str(tel1)), re.sub(r'\D', '', str(tel2))
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

def obtener_perfil_crm(telefono):
    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    es_imo = False
    
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
                    if estado in ("PENDIENTE","ENVIADO","") and px_n: px_list.append(px_n)
            wb.close()
            if imo_nombre and len(px_list) > 0:
                es_imo = True
                perfil["rol"] = "IMO"
                perfil["nombre"] = imo_nombre
        except: pass
        
    try:
        if os.path.exists(Config.CSV_BD_PATH):
            with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
                primera_linea = f.readline()
                delimitador = ';' if ';' in primera_linea else ','
                f.seek(0)
                reader = csv.DictReader(f, delimiter=delimitador)
                if reader.fieldnames:
                    keys = {k.strip().lower(): k for k in reader.fieldnames if k}
                    tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None)
                    nom_key = next((k for k in keys.values() if "nombre" in k.lower()), None)
                    ape_key = next((k for k in keys.values() if "apellido" in k.lower()), None)
                    c1_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None)
                    c2_key = next((k for k in keys.values() if "c2" == k.lower().strip()), None)
                    mj_key = next((k for k in keys.values() if "maestr" in k.lower()), None)
                    imo_nom_key = next((k for k in keys.values() if "imo" in k.lower() and "tel" not in k.lower()), None)
                    imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)

                    for row in reader:
                        try:
                            if imo_tel_key and son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
                                es_imo = True
                                if not perfil["nombre"]: perfil["nombre"] = nombre_pila(str(row.get(imo_nom_key, "")))

                            if tel_key and son_mismo_numero(str(row.get(tel_key, "")), telefono):
                                n_base = str(row.get(nom_key, "")).strip()
                                a_base = str(row.get(ape_key, "")).strip() if ape_key else ""
                                n = n_base.split()[0] if n_base.split() else ""
                                a = a_base.split()[0] if a_base.split() else ""
                                nombre_completo = f"{n} {a}".title().strip() if (n and a) else nombre_pila(n_base)
                                
                                c1_stat = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                                c2_stat = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
                                mj_stat = str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                                
                                perfil["px_nombre"] = nombre_completo
                                perfil["px_mj_stat"] = mj_stat
                                
                                pendiente = "Capítulo 1 (C1)"
                                if c1_stat == "SI": pendiente = "Capítulo 2 (C2)"
                                if c1_stat == "SI" and c2_stat == "SI": pendiente = "Maestría (MJ)"
                                perfil["px_pendiente"] = pendiente
                                perfil["imo_nombre"] = nombre_pila(str(row.get(imo_nom_key, "Tu líder")).strip()) if imo_nom_key else "Tu líder"
                                perfil["imo_tel"] = str(row.get(imo_tel_key, "")) if imo_tel_key else ""
                        except IndexError: continue
    except: pass

    if es_imo:
        perfil["rol"] = "IMO"
        if not perfil.get("nombre"): perfil["nombre"] = "Líder"
    elif perfil.get("px_nombre"):
        perfil["nombre"] = perfil["px_nombre"]
        perfil["pendiente"] = perfil.get("px_pendiente")
        if perfil.get("px_mj_stat") == "SI": perfil["rol"] = "MJ"
        else: perfil["rol"] = "PX"
        
    return perfil

def buscar_pendientes_imo_csv(telefono):
    try:
        if not os.path.exists(Config.CSV_BD_PATH): return []
        pendientes = []
        with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
            primera_linea = f.readline()
            delimitador = ';' if ';' in primera_linea else ','
            f.seek(0)
            reader = csv.DictReader(f, delimiter=delimitador)
            if not reader.fieldnames: return []
            keys = {k.strip().lower(): k for k in reader.fieldnames if k}
            
            imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)
            nom_key = next((k for k in keys.values() if "nombre" in k.lower()), None)
            ape_key = next((k for k in keys.values() if "apellido" in k.lower()), None)
            c1_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None)
            c2_key = next((k for k in keys.values() if "c2" == k.lower().strip()), None)

            if not imo_tel_key: return []

            for row in reader:
                if not row or not row.get(imo_tel_key): continue
                if son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
                    c1_stat = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                    c2_stat = str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO"

                    falta = ""
                    if c1_stat != "SI": falta = "C1"
                    elif c2_stat != "SI": falta = "C2"

                    if falta:
                        n_base = str(row.get(nom_key, "")).strip()
                        a_base = str(row.get(ape_key, "")).strip() if ape_key else ""
                        n = n_base.split()[0] if n_base.split() else ""
                        a = a_base.split()[0] if a_base.split() else ""
                        if n and a: nombre_completo = f"{n} {a}".title()
                        elif n: nombre_completo = n.title()
                        else: continue
                        pendientes.append(f"• {nombre_completo} (Falta {falta})")
        return pendientes
    except: return []

def buscar_todos_imo_csv(telefono):
    try:
        if not os.path.exists(Config.CSV_BD_PATH): return []
        with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
            primera_linea = f.readline()
            delimitador = ';' if ';' in primera_linea else ','
            f.seek(0)
            
            all_rows = list(csv.DictReader(f, delimiter=delimitador))
            if not all_rows: return []
            
            keys = {k.strip().lower(): k for k in all_rows[0].keys() if k}
            
            id_key = next((k for k in keys.values() if "identificaci" in k.lower() or "dni" in k.lower()), None)
            cambio_key = next((k for k in keys.values() if "cambio" in k.lower()), None)
            imo_tel_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)
            nom_key = next((k for k in keys.values() if "nombre" in k.lower()), None)
            ape_key = next((k for k in keys.values() if "apellido" in k.lower()), None)
            c1_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None)
            c2_key = next((k for k in keys.values() if "c2" == k.lower().strip()), None)
            mj_key = next((k for k in keys.values() if "maestr" in k.lower()), None)

            if not imo_tel_key: return []

            participantes_por_id = {}
            if id_key:
                for row in all_rows:
                    val_id = str(row.get(id_key, "")).strip()
                    if val_id and val_id != "-": participantes_por_id[val_id] = row

            resultados = []
            for row in all_rows:
                if not row or not row.get(imo_tel_key): continue
                imo_t = str(row.get(imo_tel_key, ""))
                
                if son_mismo_numero(imo_t, telefono):
                    px_actual = row
                    if cambio_key:
                        reemplazo_id = str(row.get(cambio_key, "")).strip()
                        if reemplazo_id and reemplazo_id != '-' and reemplazo_id in participantes_por_id:
                            px_actual = participantes_por_id[reemplazo_id] 
                            
                    n_base = str(px_actual.get(nom_key, "")).strip()
                    a_base = str(px_actual.get(ape_key, "")).strip() if ape_key else ""
                    n = n_base.split()[0] if n_base.split() else ""
                    a = a_base.split()[0] if a_base.split() else ""
                    nombre_completo = f"{n} {a}".title().strip() if (n and a) else nombre_pila(n_base)
                    
                    if not nombre_completo: continue

                    c1 = str(px_actual.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
                    c2 = str(px_actual.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
                    mj = str(px_actual.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                    
                    if mj == "SI": estatus = "🎓 Graduado (MJ)"
                    elif c2 == "SI": estatus = "🔥 En Proceso (C2)"
                    elif c1 == "SI": estatus = "🚀 Inició (C1)"
                    else: estatus = "⏳ Rezagado (Falta C1)"

                    resultados.append(f"• {nombre_completo} - {estatus}")
            return resultados
    except: return []

def actualizar_excel(resultados, telefono_imo):
    if str(telefono_imo).startswith("SIM_"): return
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                imo_t = str(row[3].value or "")
                px_c = str(row[4].value or "").strip()
                if not son_mismo_numero(imo_t, telefono_imo): continue
                for r in resultados:
                    if r["px"].split()[0].lower() in px_c.lower():
                        row[6].value = r["estatus"]; row[7].value = hoy; break
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

def marcar_stop(telefono):
    if str(telefono).startswith("SIM_"): return 
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            for row in wb["DATA"].iter_rows(min_row=2):
                if row and len(row) >= 7:
                    imo_t = str(row[3].value or "")
                    if son_mismo_numero(imo_t, telefono):
                        row[6].value = "STOP"; row[7].value = hoy
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

# ══════════════════════════════════════════════════════════════════════════
# 6. ESTRATEGIA DE IA DUAL (DEEPSEEK & GEMINI) CON ALTERNANCIA
# ══════════════════════════════════════════════════════════════════════════
BROCHURE_INFO_MAESTRA = """
INFORMACIÓN OFICIAL CREAR PODER SIN LÍMITES PERÚ:
- Misión: Impactar a la máxima cantidad de seres humanos a vivir una vida extraordinaria. No somos un cursito, somos Alto Rendimiento.
- Los 3 Niveles del Proceso (100 Días):
  1. Capítulo 1 (C1): Descubrimiento. 3 días para romper paradigmas y darte cuenta de tus barreras.
  2. Capítulo 2 (C2): Experiencia y Transformación profunda (Usualmente 4 días). Rediseñas cómo te relacionas con el mundo.
  3. Maestría (MJ): 100 días para integrar lo aprendido. Llevas el liderazgo a la familia y finanzas.
- Reglas: Exclusivo para MAYORES DE 18 AÑOS. NO es terapia.
- Inversión: BCP Soles a nombre de CREACIÓN CUÁNTICA E.I.R.L (Cuenta: 1934218307060).
"""

def llamar_deepseek(prompt_system, prompt_user):
    """🧠 Integración Directa con la API de DeepSeek"""
    if not Config.DEEPSEEK_KEY: return None, "deepseek_no_configurado"
    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {Config.DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": prompt_system},
            {"role": "user", "content": prompt_user}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    try:
        response = req_lib.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            respuesta = data['choices'][0]['message']['content'].strip()
            respuesta = re.sub(r'\*\*IA.*?\*\*|<\|.*?\|>|\[.*?\]', '', respuesta)
            return respuesta, None
        else:
            return None, f"deepseek_api_error: {response.status_code}"
    except Exception as e:
        return None, f"deepseek_error:{str(e)[:100]}"

def llamar_gemini(prompt_system, prompt_user):
    if not Config.GEMINI_KEY or not GEMINI_DISPONIBLE: return None, "gemini_no_configurado"
    try:
        genai.configure(api_key=Config.GEMINI_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt_completo = f"{prompt_system}\n\nContexto del usuario:\n{prompt_user}"
        r = model.generate_content(prompt_completo)
        if r.text: return r.text.strip(), None
    except Exception as e: return None, f"gemini_error:{str(e)[:100]}"
    return None, "gemini_sin_respuesta"

def embudo_ventas_ia(mensaje_usuario, nombre_conocido=None, nombre_ya_saludado=False, telefono=None):
    def guardar_y_retornar(respuesta, modelo):
        if telefono: SessionManager.guardar_dataset(telefono, mensaje_usuario, respuesta, modelo)
        return respuesta

    msg_len = len(mensaje_usuario.split())
    if msg_len <= 3 and nombre_conocido and not nombre_ya_saludado:
        resp = f"¡Hola, {nombre_conocido}! Qué gran paso estás dando al comunicarte. 🌟 Creemos firmemente que tienes un potencial ilimitado esperando ser despertado.\n\nA través de nuestra Transformación Cuántica, te acompañamos a romper las barreras que hoy te frenan. Todo esto se vive en el *Capítulo 1*, un entrenamiento vivencial de 3 días para rediseñar tu realidad. ¿Te gustaría conocer detalles de la próxima fecha?"
        return guardar_y_retornar(resp, "REGLA_CORTA")
    
    prompt_sys = f"""Eres un Coach de Enrolamiento de 'Crear Poder Sin Límites Perú'.
    BASE DE CONOCIMIENTO: {BROCHURE_INFO_MAESTRA}
    REGLAS DE ORO:
    1. CONEXIÓN EMPÁTICA: Tu tono es cálido, apasionado y enérgico. NUNCA suenes como robot. Usa emojis sutiles.
    2. NO SEAS MONÓTONO: Explica la TRANSFORMACIÓN (romper miedos, mejorar relaciones, elevar el liderazgo).
    3. PALABRAS PROHIBIDAS: "sanar", "terapia", "ayudar", "paciente".
    4. PREGUNTA DE CIERRE: Termina SIEMPRE tu respuesta con una pregunta poderosa que invite a la acción."""
    
    prompt_usr = f"""Hablas con: "{nombre_conocido if nombre_conocido else 'un contacto'}".
    Mensaje del usuario: "{mensaje_usuario}" """

    # 🚀 LÓGICA DE ALTERNANCIA (A/B TESTING)
    modo = Config.MODO_IA
    if modo == "alternar":
        modelo_primario = random.choice(["deepseek", "gemini"])
        modelo_fallback = "gemini" if modelo_primario == "deepseek" else "deepseek"
    else:
        modelo_primario = Config.IA_PRIMARIA
        modelo_fallback = Config.IA_FALLBACK

    # Intento 1
    if modelo_primario == "deepseek":
        respuesta, error = llamar_deepseek(prompt_sys, prompt_usr)
    else:
        respuesta, error = llamar_gemini(prompt_sys, prompt_usr)
        
    if respuesta: return guardar_y_retornar(respuesta, modelo_primario.upper())

    # Intento 2 (Fallback)
    logger.warning(f"Fallo en {modelo_primario}. Usando {modelo_fallback}...")
    if modelo_fallback == "deepseek":
        respuesta, error = llamar_deepseek(prompt_sys, prompt_usr)
    else:
        respuesta, error = llamar_gemini(prompt_sys, prompt_usr)
        
    if respuesta: return guardar_y_retornar(respuesta, f"FALLBACK_{modelo_fallback.upper()}")

    return guardar_y_retornar("Para brindarte un apoyo 100% personalizado y humano, te invito a presionar el número de la opción que te derive con una coordinadora.", "FALLBACK_ERROR")

# ══════════════════════════════════════════════════════════════════════════
# 7. ESTRUCTURAS DE MENÚ Y MÁQUINA DE ESTADOS
# ══════════════════════════════════════════════════════════════════════════
COORDINADORAS_CONTACTOS = {"Diana Moscoso": "51912379744", "Joyce Marín": "51933599903", "Leyla Pasquel": "51919502385", "Zuley Urteaga": "51933599864"}
COORDINADORAS = f"Coordinadoras C1 y C2:\n• Diana Moscoso: +51 912 379 744\n• Joyce Marin: +51 933 599 903\n• Leyla Pasquel: +51 919 502 385\n• Zuley Urteaga: +51 933 599 864"

MENU_STRUCTURE = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites Perú* 🌟\nSoy *IA Cuántica*, tu asistente virtual.\n\n1️⃣ *Explorar Entrenamientos* (C1, C2 y Maestría)\n2️⃣ *Inversión y Pagos*\n3️⃣ *Hablar con IA Cuántica* (Chat libre)\n4️⃣ *Atención Personalizada* (Coordinadora)\n0️⃣ *Finalizar sesión*",
        "options": {"1": "info_entrenamientos", "2": "pagos", "3": "chat_libre_ia", "4": "action_humano", "0": "action_salir"}
    },
    "main_imo": {
        "text": "🌟 *Bienvenido Líder IMO {nombre}* 🌟\nEs un honor apoyarte. Selecciona una opción:\n\n1️⃣ *Reportar Asistencia* de mis participantes\n2️⃣ *Ver mis participantes pendientes (C1/C2)*\n3️⃣ *Ver TODOS mis enrolados y estatus*\n4️⃣ *Explorar Entrenamientos*\n5️⃣ *Hablar con una Coordinadora*\n0️⃣ *Finalizar sesión*",
        "options": {"1": "action_imo", "2": "ver_pendientes_imo", "3": "ver_todos_imo", "4": "info_entrenamientos", "5": "action_humano", "0": "action_salir"}
    },
    "main_px": {
        "text": "🌟 *Bienvenido de vuelta, {nombre}* 🌟\nVemos que tienes pendiente tu: *{pendiente}*.\n\n1️⃣ *¡CONFIRMAR MI ASISTENCIA!*\n2️⃣ *Ver fechas y horarios*\n3️⃣ *Solicitar reprogramación*\n4️⃣ *Hablar con coordinadora*\n5️⃣ *Chat Libre con IA*\n0️⃣ *Finalizar sesión*",
        "options": {"1": "px_confirma", "2": "info_fechas", "3": "action_humano", "4": "action_humano", "5": "chat_libre_ia", "0": "action_salir"}
    },
    "main_mj": {
        "text": "🌟 *Hola Líder {nombre}* 🌟\nVemos en nuestra base de datos que has participado en Maestría. ¿Cuál es tu estatus actual en el proceso?\n\n1️⃣ Soy Graduado 🎓\n2️⃣ Estoy en proceso ⏳\n3️⃣ Me retiré / Deserté 🛑\n4️⃣ Quiero enrolar a alguien 🚀\n0️⃣ Finalizar sesión",
        "options": {"1": "mj_graduado", "2": "mj_proceso", "3": "mj_deserto", "4": "action_humano", "0": "action_salir"}
    },
    "mj_graduado": {
        "text": "¡Felicidades por tu graduación! 🎉 Como líder, ¿en qué te podemos apoyar hoy?\n\n1️⃣ Quiero enrolar a un nuevo participante\n2️⃣ Ver TODOS mis enrolados y estatus\n3️⃣ Hablar con una coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "2": "ver_todos_imo", "3": "action_humano", "9": "volver", "0": "main"}
    },
    "mj_proceso": {
        "text": "¡Excelente! Sigue firme en tus 100 días de transformación. 💪\n\n1️⃣ Hablar con mi coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "mj_deserto": {
        "text": "Comprendemos. Cada persona tiene su propio ritmo y momento. Si alguna vez deseas retomar tu proceso de transformación, las puertas siempre están abiertas.\n\n1️⃣ Hablar con una coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "info_entrenamientos": {
        "text": "📘 *Explorar Entrenamientos*\n\n1️⃣ Capítulo 1 (C1)\n2️⃣ Capítulo 2 (C2)\n3️⃣ Maestría (MJ)\n4️⃣ Fechas y lugares\n9️⃣ Regresar\n0️⃣ Menú principal",
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
        "text": "📅 *Fechas y Lugares*\nHotel José Antonio Deluxe (Miraflores, Lima).\n\n1️⃣ Solicitar calendario a coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher a Coordinadora\n2️⃣ Ayuda con factura/boleta\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "action_humano", "2": "action_humano", "9": "volver", "0": "main"}
    }
}

def notificar_coordinadora_aleatoria(prospecto_tel, prospecto_nombre, necesidad):
    coord_nombre, coord_tel = random.choice(list(COORDINADORAS_CONTACTOS.items()))
    msg = f"🚨 *NUEVO CONTACTO PARA CREAR* 🚀\n*Nombre:* {prospecto_nombre or 'No especificado'}\n*Teléfono:* wa.me/{prospecto_tel}\n*Necesidad:* {necesidad}"
    sesion_coord = get_sesion(coord_tel)
    sesion_coord["primera_vez"] = False; set_sesion(coord_tel, sesion_coord)
    enviar_mensaje(coord_tel, msg, f"COORDINADORA: {coord_nombre}")
    return coord_nombre

def procesar_mensaje(telefono, texto):
    sesion = get_sesion(telefono)
    texto_limpio = str(texto).strip().upper()
    
    if texto_limpio in ["0", "MENU", "MENÚ", "INICIO"] or "perfil" not in sesion:
        perfil = obtener_perfil_crm(telefono)
        if perfil["rol"] == "PROSPECTO" and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric():
            perfil["nombre"] = nombre_pila(texto)
        sesion["perfil"] = perfil; set_sesion(telefono, sesion)
    else:
        perfil = sesion.get("perfil")
        
    nombre_mostrar = f"({perfil['rol']}) {perfil['nombre']}" if perfil['nombre'] else "NUEVO CONTACTO"

    if sesion.get("menu_state") == "esperando_encuesta":
        if texto_limpio in ["1", "2", "3", "4", "5"]:
            registrar_en_sheets_async(telefono, nombre_mostrar, "Calificación", f"{texto_limpio} Estrellas", "CSAT")
            enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟 Valoramos mucho tu opinión.\n\n_Escribe MENU para reiniciar._", nombre_mostrar)
            borrar_sesion(telefono)
        else: enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_mostrar)
        return

    try:
        last_time = datetime.strptime(sesion.get("last_interaction", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
        minutos_inactividad = (datetime.now() - last_time).total_seconds() / 60.0
    except: minutos_inactividad = 9999

    sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if texto_limpio == "STOP":
        borrar_sesion(telefono)
        enviar_mensaje(telefono, "Has sido dado de baja. No recibirás más mensajes.\n\n*Crear Poder Sin Límites*", nombre_mostrar)
        return

    def get_main_key(rol):
        if rol == "IMO": return "main_imo"
        if rol == "MJ": return "main_mj"
        if rol == "PX": return "main_px"
        return "main_prospecto"
        
    main_key = get_main_key(perfil["rol"])

    def render_menu(m_key):
        txt = MENU_STRUCTURE[m_key]["text"]
        if "{" in txt: txt = txt.format(nombre=perfil.get("nombre", "Participante"), imo=perfil.get("imo_nombre", "tu líder"), pendiente=perfil.get("pendiente", "tu entrenamiento"))
        return txt

    if minutos_inactividad > 30 or "menu_state" not in sesion or texto_limpio in ["0", "MENU", "MENÚ", "INICIO"]:
        sesion["menu_state"] = main_key; sesion["menu_history"] = []; sesion["menu_errors"] = 0; set_sesion(telefono, sesion)
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
        siguiente_estado = MENU_STRUCTURE[estado_actual].get("options", {}).get(texto_limpio)
        if siguiente_estado:
            sesion["menu_errors"] = 0
            
            if siguiente_estado == "px_confirma":
                msg_exito = f"¡Extraordinario, {perfil['nombre']}! 🎉\nHemos registrado tu confirmación. Le avisaremos automáticamente a tu líder {perfil['imo_nombre']} para que esté al tanto.\n\n_Escribe 0 para volver al menú._"
                enviar_mensaje(telefono, msg_exito, nombre_mostrar)
                if perfil["imo_tel"]: threading.Thread(target=actualizar_excel, args=([{"px": perfil["nombre"], "estatus": "CONFIRMADO"}], perfil["imo_tel"]), daemon=True).start()
                sesion["menu_state"] = "esperando_fecha"; set_sesion(telefono, sesion)
                return

            elif siguiente_estado == "ver_pendientes_imo":
                lista = buscar_pendientes_imo_csv(telefono)
                if lista: msg = f"📊 *Reporte de tu Equipo (Rezagados)*\n\n" + "\n".join(lista) + "\n\n_Escribe *0* para volver._"
                else: msg = "¡Felicidades! 🎉 Todos tus participantes se han sentado o no tienes pendientes en la base.\n\n_Escribe *0* para volver._"
                enviar_mensaje(telefono, msg, nombre_mostrar)
                hist = sesion.get("menu_history", []); 
                if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                sesion["menu_state"] = "ver_pendientes_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                return

            elif siguiente_estado == "ver_todos_imo":
                lista_todos = buscar_todos_imo_csv(telefono)
                if lista_todos: msg = f"📊 *Reporte Completo de tu Equipo*\n\n" + "\n".join(lista_todos) + "\n\n_Escribe *0* para volver._"
                else: msg = "No encontramos participantes vinculados a tu número.\n\n_Escribe *0* para volver._"
                enviar_mensaje(telefono, msg, nombre_mostrar)
                hist = sesion.get("menu_history", [])
                if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                sesion["menu_state"] = "ver_todos_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
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
                enviar_mensaje(telefono, f"Noto que estamos teniendo problemas. 🤖\nHe notificado a la coordinadora *{c_nom}* para que te asista de manera humana.\n\n_Escribe *0* para menú principal._", nombre_mostrar)
                sesion["menu_state"] = "esperando_humano"
            else:
                enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado_actual)}", nombre_mostrar)
            set_sesion(telefono, sesion)

    elif estado_actual in ["action_imo", "chat_libre_ia"]:
        if estado_actual == "chat_libre_ia":
            resp_ia = embudo_ventas_ia(texto, perfil["nombre"], sesion.get("nombre_saludado", False), telefono)
            enviar_mensaje(telefono, resp_ia, nombre_mostrar)
        else:
            enviar_mensaje(telefono, f"Mensaje recibido. Procesando...\n\n_Escribe *0* para volver al menú._", nombre_mostrar)
        
    elif estado_actual in ["esperando_humano", "esperando_fecha", "ver_todos_imo", "ver_pendientes_imo"]:
        set_sesion(telefono, sesion)

# ══════════════════════════════════════════════════════════════════════════
# 8. PANEL WEB (HTML), ENDPOINTS Y SIMULADOR
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
        .download-btn { background: #00a884; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; text-decoration: none;}
        .sim-btn { background: #1a73e8; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-size: 12px; transition: 0.2s; }
        .sim-banner { background: #ffe0b2; color: #174ea6; padding: 10px; text-align: center; font-size: 13px; font-weight: bold; border-bottom: 1px solid #f2c779;}
    </style>
</head>
<body>
    <div class="app-container">
        <div class="sidebar">
            <div class="sidebar-header">
                <div class="header-top">
                    <div>💬 Panel V57 (DeepSeek)</div>
                    <div class="header-actions">
                        <button class="sim-btn" onclick="iniciarSimulador()">🧪 Simular</button>
                        <a href="/api/descargar_respaldo" class="download-btn">📥 Backup</a>
                        <a href="/api/descargar_dataset" class="sim-btn" style="background:#5e35b1;">🧠 AI Data</a>
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
                <p style="margin-top: 10px; font-size:14px;">Selecciona un chat o inicia el Simulador.</p>
            </div>
            <div class="sim-banner hidden" id="simBanner">⚠️ MODO SIMULADOR: Estás escribiendo como si fueras el cliente. Nada se enviará a WhatsApp.</div>
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
                item.style.display = searchData.includes(query) ? "flex" : "none";
            });
        }

        function iniciarSimulador() {
            let num = prompt("Ingresa el número a simular:\\nEj: 999888777");
            if (!num) return;
            num = num.replace(/\\D/g, '');
            let simTel = "SIM_" + num;
            activeContact = simTel;
            
            fetch('/api/mensaje_simulador', { 
                method: 'POST', headers: {'Content-Type': 'application/json'}, 
                body: JSON.stringify({telefono: simTel, texto: "MENU"}) 
            }).then(() => cargarDatos());
        }

        function renderContacts() {
            const list = document.getElementById('contactsList'); list.innerHTML = '';
            const phones = Object.keys(chatHistory).reverse();
            if(phones.length === 0) return;
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
                
                let icon = phone.startsWith("SIM_") ? "🧪" : "👤";
                div.innerHTML = `<div class="avatar">${icon}</div><div class="contact-info"><h4>${displayName}</h4><p>${lastMessage}</p></div>`;
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
            
            if (phone.startsWith("SIM_")) document.getElementById('simBanner').classList.remove('hidden');
            else document.getElementById('simBanner').classList.add('hidden');
            
            renderContacts(); renderMessages();
        }

        function renderMessages() {
            const container = document.getElementById('messagesContainer'); container.innerHTML = '';
            if (!activeContact || !chatHistory[activeContact]) return;
            
            const isSim = activeContact.startsWith("SIM_");
            chatHistory[activeContact].messages.forEach(msg => {
                const div = document.createElement('div'); 
                let isSentByMe = isSim ? !msg.sent : msg.sent;
                div.className = `message ${isSentByMe ? 'sent' : 'received'}`;
                div.innerHTML = `${msg.text.replace(/\\n/g, '<br>')}<span class="time">${msg.time}</span>`;
                container.appendChild(div);
            });
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const textarea = document.getElementById('messageInput'); const mensaje = textarea.value.trim(); const destino = activeContact;
            if (!mensaje || !destino) return;
            textarea.value = '';
            
            const isSim = destino.startsWith("SIM_");
            chatHistory[destino].messages.push({ text: mensaje, time: new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}), sent: !isSim });
            renderMessages(); renderContacts();
            
            try {
                if (isSim) await fetch('/api/mensaje_simulador', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ telefono: destino, texto: mensaje }) });
                else await fetch('/api/enviar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ telefono: destino, mensaje: mensaje }) });
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

@app.route("/api/descargar_dataset", methods=["GET"])
def descargar_dataset():
    if os.path.exists(Config.DATASET_PATH):
        with open(Config.DATASET_PATH, "r", encoding="utf-8-sig") as f: data = f.read()
    else: data = "Fecha,Telefono,Mensaje Usuario,Respuesta IA,Modelo\nSin datos aun"
    return Response(data, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename=Dataset_Entrenamiento.csv"})

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

@app.route("/api/mensaje_simulador", methods=["POST"])
def mensaje_simulador():
    data = request.json; tel = data.get("telefono"); texto = data.get("texto")
    if not tel or not texto: return jsonify({"error": "Faltan datos"}), 400
    procesar_mensaje(tel, texto)
    sesion = get_sesion(tel)
    perfil = sesion.get("perfil", {})
    nombre_mostrar = f"({perfil.get('rol', 'PROSPECTO')}) {perfil.get('nombre', 'Simulado')}" if perfil.get('nombre') else "SIMULACIÓN"
    append_historial(tel, nombre_mostrar, texto, "in")
    return jsonify({"status": "ok"}), 200

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
            
            procesar_mensaje(telefono, texto)
            
            sesion = get_sesion(telefono)
            perfil = sesion.get("perfil", {})
            nombre_mostrar = f"({perfil.get('rol', 'PROSPECTO')}) {perfil.get('nombre', 'Nuevo')}" if perfil.get('nombre') else "NUEVO CONTACTO"
            append_historial(telefono, nombre_mostrar, texto, "in")

        elif tipo in ("audio","image","document","video","sticker"):
            WhatsAppAPI.enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.")
            
    except Exception as e: logger.error(f"Error Webhook: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
