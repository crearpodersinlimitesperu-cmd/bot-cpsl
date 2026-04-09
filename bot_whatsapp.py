"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ Versión V82: Quantum Architecture (Doble Opt-In, Smart Routing, Date Flip, Cultura Pura)
"""

import os, re, json, time, csv, io, random, logging, threading, queue
from flask import Flask, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN Y ZONA HORARIA (LIMA)
# ══════════════════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))

def ahora_lima():
    return datetime.now(TZ_LIMA)

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
    SESSIONS_PATH = "sesiones.json"
    HISTORIAL_PATH = "historial_chat.json"
    BACKUP_ABSOLUTO_CSV = "backup_absoluto_mensajes.csv"
    SHEET_ID = os.environ.get("SHEET_ID", "")
    CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS", "")

# ══════════════════════════════════════════════════════════════════════════
# 2. GESTOR DE ESTADO LOCAL Y CAJA NEGRA
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
                h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": ahora_lima().strftime("%d/%m %H:%M")})
                with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h[-10000:], f, ensure_ascii=False, indent=2)
            except: pass

    @staticmethod
    def guardar_backup_absoluto(telefono, nombre, mensaje, direccion, estado_sistema):
        with FileLock(Config.BACKUP_ABSOLUTO_CSV + ".lock"):
            try:
                archivo_existe = os.path.exists(Config.BACKUP_ABSOLUTO_CSV)
                with open(Config.BACKUP_ABSOLUTO_CSV, "a", encoding="utf-8-sig", newline="") as f:
                    writer = csv.writer(f)
                    if not archivo_existe: 
                        writer.writerow(["Fecha y Hora", "Telefono", "Nombre", "Direccion (In/Out)", "Mensaje", "Estado Sistema"])
                    writer.writerow([ahora_lima().strftime("%Y-%m-%d %H:%M:%S"), telefono, nombre, direccion, mensaje, estado_sistema])
            except Exception as e: pass

def get_sesion(tel): return SessionManager.get_sesion(tel)
def set_sesion(tel, d): SessionManager.set_sesion(tel, d)
def borrar_sesion(tel): SessionManager.borrar_sesion(tel)
def append_historial(tel, nom, txt, tipo): SessionManager.append_historial(tel, nom, txt, tipo)

# ══════════════════════════════════════════════════════════════════════════
# 3. GOOGLE SHEETS (SMART QUEUE)
# ══════════════════════════════════════════════════════════════════════════
cola_sheets = queue.Queue()

class GoogleSheetsAPI:
    @classmethod
    def registrar_accion(cls, telefono, imo_nombre, mensaje, respuesta_bot, estado="", respuesta_manual="", enviado_status=""):
        if not Config.SHEET_ID or not Config.CREDS_JSON: return
        try:
            import base64
            now = int(time.time())
            creds_text = str(Config.CREDS_JSON).strip()
            creds = json.loads(creds_text)
            
            header = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            payload = base64.urlsafe_b64encode(json.dumps({
                "iss": creds["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
                "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600
            }).encode()).rstrip(b"=")
            msg_jwt = header + b"." + payload
            
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            
            pk = serialization.load_pem_private_key(creds["private_key"].encode('utf-8').replace(b'\\n', b'\n'), password=None)
            sig = pk.sign(msg_jwt, padding.PKCS1v15(), hashes.SHA256())
            jwt = (msg_jwt + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token", data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt}, timeout=10)
            
            if r.status_code == 200:
                token = r.json()["access_token"]
                url = f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}/values/Hoja%201!A:H:append"
                ahora_str = ahora_lima().strftime("%d/%m/%Y %H:%M")
                valores = [[ahora_str, str(telefono), imo_nombre, mensaje, respuesta_bot, estado, respuesta_manual, enviado_status]]
                req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, json={"values": valores}, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        except Exception as e: pass

def worker_sheets():
    while True:
        try:
            tarea = cola_sheets.get()
            GoogleSheetsAPI.registrar_accion(tarea['tel'], tarea['nom'], tarea['msg'], tarea['resp'], tarea['est'], tarea.get('resp_man', ""), tarea.get('env_stat', ""))
            time.sleep(1.5)  
        except: pass
        finally: cola_sheets.task_done()

threading.Thread(target=worker_sheets, daemon=True).start()

def registrar_en_sheets_smart(tel, nom, msg, resp, est="", resp_man="", env_stat=""):
    if str(tel).startswith("SIM_"): return 
    cola_sheets.put({'tel': tel, 'nom': nom, 'msg': msg, 'resp': resp, 'est': est, 'resp_man': resp_man, 'env_stat': env_stat})

# ══════════════════════════════════════════════════════════════════════════
# 4. CONECTORES DE WHATSAPP API
# ══════════════════════════════════════════════════════════════════════════
class WhatsAppAPI:
    @staticmethod
    def enviar_mensaje(telefono, texto, nombre_mostrar="", registrar_sheets=True, estado_menu=""):
        if str(telefono).startswith("SIM_"):
            append_historial(telefono, nombre_mostrar, texto, "out")
            registrar_en_sheets_smart(telefono, nombre_mostrar, "", texto[:500], estado_menu or "SIMULADOR")
            SessionManager.guardar_backup_absoluto(telefono, nombre_mostrar, texto, "OUT", estado_menu or "SIMULADOR")
            return True

        url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": str(telefono), "type": "text", "text": {"body": texto, "preview_url": False}}
        try:
            r = req_lib.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                append_historial(telefono, nombre_mostrar, texto, "out")
                SessionManager.guardar_backup_absoluto(telefono, nombre_mostrar, texto, "OUT", estado_menu or "INTERACTIVO")
                if registrar_sheets: registrar_en_sheets_smart(telefono, nombre_mostrar, "", texto[:500], estado_menu or "INTERACTIVO")
                return True
        except: pass
        return False

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=True, estado_menu="INTERACTIVO"):
    return WhatsAppAPI.enviar_mensaje(telefono, texto, nombre_imo, registrar_sheets, estado_menu)

# ══════════════════════════════════════════════════════════════════════════
# 5. CRM OMNICANAL
# ══════════════════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0") and len(t) == 10: return t[1:]
    if len(t) > 10 and not t.startswith("9"): return t[-9:]
    return t

def son_mismo_numero(tel1, tel2):
    t1, t2 = norm_tel(tel1), norm_tel(tel2)
    if not t1 or not t2: return False
    if t1 == t2: return True
    return min(len(t1), len(t2)) >= 8 and (t1.endswith(t2) or t2.endswith(t1))

def nombre_pila(s): return [p.strip() for p in re.split(r'\s+', s.strip()) if len(p.strip()) > 2][0].title() if [p.strip() for p in re.split(r'\s+', s.strip()) if len(p.strip()) > 2] else s.strip().title()

def cargar_px_del_imo(telefono):
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH, data_only=True, read_only=True)
            px_list, imo_nombre = [], ""
            for row in wb["DATA"].iter_rows(min_row=2, values_only=True):
                if row and len(row) >= 7 and son_mismo_numero(str(row[3] or ""), telefono):
                    if not imo_nombre: imo_nombre = str(row[0] or "").strip()
                    if str(row[6] or "").strip().upper() in ("PENDIENTE","ENVIADO","") and str(row[4] or "").strip(): px_list.append(str(row[4]).strip())
            wb.close()
            return imo_nombre, px_list
        except: return "", []

def obtener_perfil_crm(telefono):
    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    es_imo = False
    
    imo_nom, px_list = cargar_px_del_imo(telefono)
    if imo_nom and len(px_list) > 0: es_imo = True; perfil["rol"] = "IMO"; perfil["nombre"] = imo_nom
        
    try:
        if os.path.exists(Config.CSV_BD_PATH):
            with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f, delimiter=';' if ';' in f.readline() else ',')
                f.seek(0); next(reader)
                keys = {k.strip().lower(): k for k in reader.fieldnames if k}
                tel_key, nom_key, ape_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" not in k.lower()), None), next((k for k in keys.values() if "nombre" in k.lower()), None), next((k for k in keys.values() if "apellido" in k.lower()), None)
                c1_key, c2_key, mj_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None), next((k for k in keys.values() if "c2" == k.lower().strip()), None), next((k for k in keys.values() if "maestr" in k.lower()), None)
                imo_nom_key, imo_tel_key = next((k for k in keys.values() if "imo" in k.lower() and "tel" not in k.lower()), None), next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None)

                for row in reader:
                    if imo_tel_key and son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
                        es_imo = True; perfil["nombre"] = perfil.get("nombre") or nombre_pila(str(row.get(imo_nom_key, "")))
                    if tel_key and son_mismo_numero(str(row.get(tel_key, "")), telefono):
                        n = str(row.get(nom_key, "")).strip().split()[0] if str(row.get(nom_key, "")).strip() else ""
                        a = str(row.get(ape_key, "")).strip().split()[0] if ape_key and str(row.get(ape_key, "")).strip() else ""
                        perfil["px_nombre"] = f"{n} {a}".title().strip() if (n and a) else nombre_pila(str(row.get(nom_key, "")))
                        
                        c1, c2, mj = str(row.get(c1_key, "NO")).strip().upper() if c1_key else "NO", str(row.get(c2_key, "NO")).strip().upper() if c2_key else "NO", str(row.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
                        si_c1, si_c2, si_mj = (c1 in ("SI","S")), (c2 in ("SI","S")), (mj in ("SI","S"))
                        
                        if not si_c1: perfil["px_pendiente"] = "Capítulo 1 (C1)"; perfil["rol_base"] = "PX_REZAGADO_C1"
                        elif si_c1 and not si_c2: perfil["px_pendiente"] = "Capítulo 2 (C2)"; perfil["rol_base"] = "PX_UPSELL_C2"
                        elif si_c1 and si_c2 and not si_mj: perfil["px_pendiente"] = "Maestría (MJ)"; perfil["rol_base"] = "PX_UPSELL_MJ"
                        elif si_mj: perfil["px_pendiente"] = "Ninguno (Maestría iniciada)"; perfil["rol_base"] = "MJ"
                        else: perfil["px_pendiente"] = "Entrenamiento a validar"; perfil["rol_base"] = "PX"
                        
                        perfil["imo_nombre"] = nombre_pila(str(row.get(imo_nom_key, "Tu líder")).strip()) if imo_nom_key else "Tu líder"
                        perfil["imo_tel"] = str(row.get(imo_tel_key, "")) if imo_tel_key else ""
    except: pass

    if es_imo: perfil["rol"] = "IMO"; perfil["nombre"] = perfil.get("nombre") or "Líder"
    elif perfil.get("px_nombre"): perfil["nombre"], perfil["pendiente"], perfil["rol"] = perfil["px_nombre"], perfil.get("px_pendiente"), perfil.get("rol_base", "PX")
    return perfil

def buscar_pendientes_imo_csv(telefono):
    try:
        if not os.path.exists(Config.CSV_BD_PATH): return []
        with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=';' if ';' in f.readline() else ',')
            f.seek(0); next(reader); keys = {k.strip().lower(): k for k in reader.fieldnames if k}
            imo_tel_key, nom_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None), next((k for k in keys.values() if "nombre" in k.lower()), None)
            c1_key, c2_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None), next((k for k in keys.values() if "c2" == k.lower().strip()), None)
            if not imo_tel_key: return []
            return [f"• {nombre_pila(str(row.get(nom_key, '')))} (Falta {'C1' if str(row.get(c1_key, 'NO')).upper() not in ('SI','S') else 'C2'})" for row in reader if row.get(imo_tel_key) and son_mismo_numero(str(row[imo_tel_key]), telefono) and (str(row.get(c1_key, 'NO')).upper() not in ('SI','S') or str(row.get(c2_key, 'NO')).upper() not in ('SI','S'))]
    except: return []

def buscar_todos_imo_csv(telefono):
    try:
        if not os.path.exists(Config.CSV_BD_PATH): return []
        with open(Config.CSV_BD_PATH, "r", encoding="utf-8-sig") as f:
            all_rows = list(csv.DictReader(f, delimiter=';' if ';' in f.readline() else ','))
            f.seek(0); keys = {k.strip().lower(): k for k in all_rows[0].keys() if k}
            imo_tel_key, nom_key = next((k for k in keys.values() if "tel" in k.lower() and "imo" in k.lower()), None), next((k for k in keys.values() if "nombre" in k.lower()), None)
            c1_key, c2_key, mj_key = next((k for k in keys.values() if "c1" == k.lower().strip()), None), next((k for k in keys.values() if "c2" == k.lower().strip()), None), next((k for k in keys.values() if "maestr" in k.lower()), None)
            if not imo_tel_key: return []
            res = []
            for row in all_rows:
                if son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
                    n = nombre_pila(str(row.get(nom_key, "")))
                    c1, c2, mj = str(row.get(c1_key, "NO")).upper(), str(row.get(c2_key, "NO")).upper(), str(row.get(mj_key, "NO")).upper()
                    if mj in ("SI","S"): st = "🎓 MJ Iniciado/Graduado"
                    elif c2 in ("SI","S"): st = "🔥 En Proceso (C2)"
                    elif c1 in ("SI","S"): st = "🚀 Inició (C1)"
                    else: st = "⏳ Rezagado (Falta C1)"
                    if n: res.append(f"• {n} - {st}")
            return res
    except: return []

def reporte_sentados_imo(telefono):
    t = buscar_todos_imo_csv(telefono)
    return [r for r in t if "Rezagado" not in r and "Falta" not in r], [r for r in t if "Rezagado" in r or "Falta" in r]

def marcar_stop(telefono):
    if str(telefono).startswith("SIM_"): return 
    with FileLock(Config.EXCEL_PATH + ".lock"):
        try:
            wb = load_workbook(Config.EXCEL_PATH)
            for row in wb["DATA"].iter_rows(min_row=2):
                if row and len(row) >= 7 and son_mismo_numero(str(row[3].value or ""), telefono): row[6].value, row[7].value = "STOP", ahora_lima().strftime("%d/%m/%Y %H:%M")
            wb.save(Config.EXCEL_PATH); wb.close()
        except: pass

# ══════════════════════════════════════════════════════════════════════════
# 6. RELOJ DINÁMICO LIMA 2026 (CUTOFFS Y HORAS DE INICIO)
# ══════════════════════════════════════════════════════════════════════════
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def get_fecha_activa(tipo_evento):
    ahora = ahora_lima()
    eventos_c1 = [{"eq": "27", "co": datetime(2026, 5, 1, 11, 30, tzinfo=TZ_LIMA), "txt": "Viernes 01 de Mayo a las 9:00 AM (Equipo 27)"},
                  {"eq": "28", "co": datetime(2026, 6, 5, 11, 30, tzinfo=TZ_LIMA), "txt": "Viernes 05 de Junio a las 9:00 AM (Equipo 28)"},
                  {"eq": "29", "co": datetime(2026, 7, 10, 11, 30, tzinfo=TZ_LIMA), "txt": "Viernes 10 de Julio a las 9:00 AM (Equipo 29)"},
                  {"eq": "30", "co": datetime(2026, 8, 14, 11, 30, tzinfo=TZ_LIMA), "txt": "Viernes 14 de Agosto a las 9:00 AM (Equipo 30)"}]
    eventos_c2 = [{"eq": "26", "co": datetime(2026, 4, 9, 15, 30, tzinfo=TZ_LIMA), "txt": "Jueves 09 de Abril a las 1:00 PM (Equipo 26)"},
                  {"eq": "27", "co": datetime(2026, 5, 14, 15, 30, tzinfo=TZ_LIMA), "txt": "Jueves 14 de Mayo a las 1:00 PM (Equipo 27)"},
                  {"eq": "28", "co": datetime(2026, 6, 18, 15, 30, tzinfo=TZ_LIMA), "txt": "Jueves 18 de Junio a las 1:00 PM (Equipo 28)"},
                  {"eq": "29", "co": datetime(2026, 7, 23, 15, 30, tzinfo=TZ_LIMA), "txt": "Jueves 23 de Julio a las 1:00 PM (Equipo 29)"}]
    eventos_mj = [{"eq": "26", "co": datetime(2026, 4, 17, 19, 0, tzinfo=TZ_LIMA), "txt": "Viernes 17 de Abril a las 5:00 PM (Inicia Equipo 26)"},
                  {"eq": "27", "co": datetime(2026, 5, 22, 19, 0, tzinfo=TZ_LIMA), "txt": "Viernes 22 de Mayo a las 5:00 PM (Inicia Equipo 27)"},
                  {"eq": "28", "co": datetime(2026, 6, 26, 19, 0, tzinfo=TZ_LIMA), "txt": "Viernes 26 de Junio a las 5:00 PM (Inicia Equipo 28)"},
                  {"eq": "29", "co": datetime(2026, 7, 31, 19, 0, tzinfo=TZ_LIMA), "txt": "Viernes 31 de Julio a las 5:00 PM (Inicia Equipo 29)"}]

    eventos = eventos_c1 if tipo_evento == "C1" else eventos_c2 if tipo_evento == "C2" else eventos_mj
    for ev in eventos:
        if ahora <= ev["co"]: return ev["txt"]
    return "Nuevas fechas por confirmar."

# ══════════════════════════════════════════════════════════════════════════
# 7. SMART ROUTING (MANDOS Y TRANSICIÓN DE LEYLA)
# ══════════════════════════════════════════════════════════════════════════
def notificar_coordinadora_interna(prospecto_tel, prospecto_nombre, motivo, contexto="GENERAL"):
    ahora = ahora_lima()
    targets = {"Diana": "51912379744", "Joyce": "51933599903", "Zuley": "51933599864"} # Línea Frontal
    
    is_mj = "MAESTRÍA" in contexto or "MJ" in contexto or "RETOMAR" in contexto or "SOPORTE MJ" in contexto
    if is_mj:
        targets = {"Linid": "51912379686"}
        if ahora >= datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385" # Se activa post inducción
    else:
        if ahora < datetime(2026, 4, 17, 0, 0, tzinfo=TZ_LIMA): targets["Leyla"] = "51919502385" # Apoya en inducción

    coord_nombre, coord_tel = random.choice(list(targets.items()))
    msg = f"🚨 *NUEVO TICKET CORPORATIVO* 🚀\n*Nombre:* {prospecto_nombre or 'No especificado'}\n*Teléfono:* wa.me/{prospecto_tel}\n*Contexto:* {contexto}\n*Requerimiento:* {motivo}"
    enviar_mensaje(coord_tel, msg, f"COORDINACIÓN: {coord_nombre}", True, "ALERTA TICKET")
    return coord_nombre

# ══════════════════════════════════════════════════════════════════════════
# 8. MENÚS DE ENROLAMIENTO (NARRATIVA CUÁNTICA)
# ══════════════════════════════════════════════════════════════════════════
MENU_STRUCTURE = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial. Responde con el número de tu elección:\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Inversión y Métodos de Pago\n3️⃣ Soy Participante / Líder (Cambié de número)\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1": "info_entrenamientos", "2": "pagos", "3": "pre_action_humano_actualizar_numero", "4": "pre_action_humano_coordinacion", "0": "action_salir"}
    },
    "main_imo": {
        "text": "🌟 *Bienvenido Líder IMO {nombre}*\nCanal Corporativo Oficial. Selecciona una opción:\n\n1️⃣ Ver mis rezagados (Pendientes C1/C2)\n2️⃣ Ver estado de TODOS mis enrolados\n3️⃣ Hablar con Coordinación IMO\n0️⃣ Finalizar",
        "options": {"1": "ver_pendientes_imo", "2": "ver_todos_imo", "3": "pre_action_humano_soporte_imo", "0": "action_salir"}
    },
    "main_px_rezagado_c1": {
        "text": "🌟 *Hola {nombre}.*\nTienes pendiente vivir tu *Capítulo 1 (Fase de Descubrimiento)*. ¡Tu transformación te espera!\n\n1️⃣ Confirmar mi asistencia para la próxima fecha\n2️⃣ Ver fechas y horarios del C1\n3️⃣ Solicitar reprogramación a Coordinación\n4️⃣ Ver a mis invitados enrolados\n0️⃣ Finalizar",
        "options": {"1": "pre_action_humano_confirma_c1", "2": "info_fechas", "3": "pre_action_humano_reprogramacion_c1", "4": "ver_todos_imo", "0": "action_salir"}
    },
    "main_px_upsell_c2": {
        "text": "🌟 *¡Hola {nombre}! Diste el primer paso en C1.*\nTu siguiente nivel de transformación profunda te espera. Tienes pendiente tu *Capítulo 2 (C2)*.\n\n1️⃣ Información y fechas del Capítulo 2 (C2)\n2️⃣ Confirmar asistencia / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1": "info_fechas", "2": "pagos", "3": "ver_todos_imo", "4": "pre_action_humano_asesoria_c2", "0": "action_salir"}
    },
    "main_px_upsell_mj": {
        "text": "🌟 *¡Felicidades por completar tu C2, {nombre}!*\nEl último paso para llevar tu liderazgo a tu familia y finanzas es la *Maestría (MJ)*.\n\n1️⃣ Información y fechas de Maestría (MJ)\n2️⃣ Confirmar inscripción / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con Coordinación de Maestría\n0️⃣ Finalizar",
        "options": {"1": "info_fechas", "2": "pagos", "3": "ver_todos_imo", "4": "pre_action_humano_asesoria_mj", "0": "action_salir"}
    },
    "main_mj": {
        "text": "🌟 *Portal de Graduados*\n¡Un honor saludarte, Líder {nombre}! Tu transformación inspira a otros.\n\n¿Desde qué espacio requieres apoyo o eliges servir hoy?\n1️⃣ Enrolar a un nuevo participante\n2️⃣ Ver TODOS mis enrolados y su estatus\n3️⃣ Hablar con Coordinación de Maestría\n4️⃣ Postularme al programa de Aliados\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_enrolar", "2": "ver_todos_imo", "3": "pre_action_humano_soporte_mj", "4": "pre_action_humano_aliados", "0": "main"}
    },
    "info_entrenamientos": {
        "text": "📘 *Crear Poder Sin Límites*\nSomos un centro de entrenamiento de liderazgo y transformación cuántica de alto rendimiento. Nuestra misión es impulsarte a salir del \"modo automático\" y aplicar los principios de la física cuántica para que elijas vivir una vida extraordinaria, asumiendo el 100% de responsabilidad sobre tus resultados.\n\nSelecciona el nivel que estás listo para explorar:\n1️⃣ C1 (Capítulo Uno) - El Descubrimiento\n2️⃣ C2 (Capítulo Dos) - La Experiencia\n3️⃣ MJ (Maestría del Juego) - La Práctica\n4️⃣ Fechas y lugares\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "info_c1", "2": "info_c2", "3": "info_mj", "4": "info_fechas", "9": "volver", "0": "main"}
    },
    "info_c1": {
        "text": "🚀 *C1 (Capítulo Uno) - El Descubrimiento*\nEs la puerta de entrada a tu transformación. Un entrenamiento vivencial de 3 días diseñado para romper paradigmas, observar tus mecanismos de defensa automáticos y confrontar las excusas y límites que te has puesto a ti mismo. Es el momento de darte cuenta de las barreras que frenan tu energía y tus resultados.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_c1", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": "🔥 *C2 (Capítulo Dos) - La Experiencia*\nEl nivel de transformación profunda. 4 días inmersivos de alto riesgo emocional para atravesar de frente las barreras descubiertas en el C1. Diseñado para dar un salto cuántico: dejar de \"sobrevivir\" y elegir rediseñar por completo tu realidad, operando como un creador absoluto desde la acción y el compromiso inquebrantable.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_c2", "9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": "👑 *MJ (Maestría del Juego) - La Práctica*\nDonde el liderazgo se lleva a la cancha real. Un programa continuo de 100 días en tu vida diaria. Integrarás y sostendrás lo aprendido en C1 y C2, forjando la disciplina para crear resultados sostenibles, materializar metas y desarrollar hábitos inquebrantables de liderazgo y enrolamiento continuo.\n\n1️⃣ Hablar con Coordinación para mi registro\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_mj", "9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": "dinamico", 
        "options": {"1": "pre_action_humano_coordinacion", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher / Factura a Coordinación\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_pagos", "9": "volver", "0": "main"}
    }
}

# ══════════════════════════════════════════════════════════════════════════
# 9. PROCESADOR DE ESTADOS (FLUJO CON DOBLE OPT-IN)
# ══════════════════════════════════════════════════════════════════════════
def flujo_principal(telefono, texto):
    try:
        sesion = get_sesion(telefono)
        texto_limpio = str(texto).strip().upper()
        
        if texto_limpio in ["0", "MENU", "MENÚ", "INICIO"] or "perfil" not in sesion:
            perfil = obtener_perfil_crm(telefono)
            if perfil["rol"] == "PROSPECTO" and len(texto.split()) <= 3 and len(texto) > 2 and not texto_limpio.isnumeric():
                perfil["nombre"] = nombre_pila(texto)
            sesion["perfil"] = perfil; set_sesion(telefono, sesion)
        else:
            perfil = sesion.get("perfil")
            
        nombre_mostrar = f"({perfil['rol']}) {perfil.get('nombre', 'Nuevo')}" if perfil.get('nombre') else "NUEVO CONTACTO"

        # Modo Silencio
        if sesion.get("menu_state") == "esperando_humano":
            if texto_limpio not in ["0", "MENU", "MENÚ", "INICIO"]: return

        if sesion.get("menu_state") == "esperando_encuesta":
            if texto_limpio in ["1", "2", "3", "4", "5"]:
                enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟\n_Escribe MENU para reiniciar._", nombre_mostrar, True, "ENCUESTA CSAT")
                borrar_sesion(telefono)
            else: enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_mostrar, True, "ERROR CSAT")
            return

        # 🛡️ DOBLE OPT-IN: Paso 1 - Capturar Motivo
        if sesion.get("menu_state") == "capturando_motivo":
            if texto_limpio not in ["0", "MENU", "MENÚ", "INICIO"]:
                sesion["motivo_temp"] = texto
                sesion["menu_state"] = "confirmando_derivacion"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, f"⚡ Entendido. Te vamos a derivar con Coordinación para tratar exclusivamente el siguiente requerimiento:\n\n💬 _{texto}_\n\n*¿Es correcto?*\n1️⃣ Sí, derivar a Coordinación ahora\n2️⃣ No, cancelar y volver al menú", nombre_mostrar, True, "DOBLE OPT-IN")
            return

        # 🛡️ DOBLE OPT-IN: Paso 2 - Confirmación
        if sesion.get("menu_state") == "confirmando_derivacion":
            if texto_limpio == "1":
                motivo = sesion.get("motivo_temp", "Sin detalle")
                contexto = sesion.get("contexto_derivacion", "GENERAL")
                notificar_coordinadora_interna(telefono, perfil["nombre"], motivo, contexto)
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "¡Excelente! Tu consulta ha sido derivada a Coordinación. Te responderemos por este chat pronto.\n\n_Escribe *0* para volver al menú._", nombre_mostrar, True, "DERIVADO EXITOSO")
            elif texto_limpio == "2":
                prev_state = sesion.get("menu_history", ["main_prospecto"])[-1] if sesion.get("menu_history") else "main_prospecto"
                sesion["menu_state"] = prev_state
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, "Operación cancelada. No se ha notificado a Coordinación. Volviendo al menú...", nombre_mostrar, True, "DERIVACIÓN CANCELADA")
            else:
                enviar_mensaje(telefono, "⚠️ Opción no válida. Responde *1* para derivar o *2* para cancelar.", nombre_mostrar, True, "ERROR OPT-IN")
            return

        try:
            last_time = datetime.strptime(sesion.get("last_interaction", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            ahora_local_naive = ahora_lima().replace(tzinfo=None)
            minutos_inactividad = (ahora_local_naive - last_time).total_seconds() / 60.0
        except Exception: minutos_inactividad = 9999
            
        sesion["last_interaction"] = ahora_lima().strftime("%Y-%m-%d %H:%M:%S")
        
        if texto_limpio == "STOP":
            marcar_stop(telefono); borrar_sesion(telefono)
            enviar_mensaje(telefono, "Has sido dado de baja. No recibirás más mensajes.", nombre_mostrar, True, "SE DIO DE BAJA")
            return

        rol = perfil.get("rol", "PROSPECTO")
        if rol == "IMO": main_key = "main_imo"
        elif rol == "MJ": main_key = "main_mj"
        elif rol == "PX_REZAGADO_C1": main_key = "main_px_rezagado_c1"
        elif rol == "PX_UPSELL_C2": main_key = "main_px_upsell_c2"
        elif rol == "PX_UPSELL_MJ": main_key = "main_px_upsell_mj"
        elif rol == "PX": main_key = "main_px_rezagado_c1"
        else: main_key = "main_prospecto"

        def render_menu(m_key):
            if m_key == "info_fechas":
                return f"📅 *Fechas Disponibles*\n\n🚀 *C1:* {get_fecha_activa('C1')}\n🔥 *C2:* {get_fecha_activa('C2')}\n👑 *MJ (Creación):* {get_fecha_activa('MJ')}\n\n1️⃣ Hablar con Coordinación\n9️⃣ Regresar\n0️⃣ Menú principal"
            txt = MENU_STRUCTURE.get(m_key, MENU_STRUCTURE[main_key])["text"]
            if "{" in txt: txt = txt.format(nombre=perfil.get("nombre", "Líder"), imo=perfil.get("imo_nombre", "tu líder"), pendiente=perfil.get("pendiente", "tu nivel"))
            return txt

        if minutos_inactividad > 30 or "menu_state" not in sesion or texto_limpio in ["0", "MENU", "MENÚ", "INICIO"]:
            sesion["menu_state"] = main_key; sesion["menu_history"] = []; sesion["menu_errors"] = 0; set_sesion(telefono, sesion)
            enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar, True, main_key)
            return

        if texto_limpio in ["9", "VOLVER", "ATRAS", "ATRÁS"]:
            hist = sesion.get("menu_history", [])
            if hist:
                prev = hist.pop()
                sesion["menu_state"] = prev; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                enviar_mensaje(telefono, render_menu(prev), nombre_mostrar, True, prev)
            else:
                sesion["menu_state"] = main_key; set_sesion(telefono, sesion)
                enviar_mensaje(telefono, render_menu(main_key), nombre_mostrar, True, main_key)
            return

        estado_actual = sesion.get("menu_state", main_key)

        if estado_actual in MENU_STRUCTURE:
            siguiente_estado = MENU_STRUCTURE[estado_actual].get("options", {}).get(texto_limpio)
            if siguiente_estado:
                sesion["menu_errors"] = 0
                
                if siguiente_estado == "pre_action_humano_actualizar_numero":
                    sesion["contexto_derivacion"] = "ACTUALIZAR NÚMERO (LÍDER/PARTICIPANTE)"
                    msg = "Para actualizar tu registro corporativo y restaurar tus accesos, por favor indícame en un solo mensaje:\n*¿Cuál es tu Nombre Completo y tu DNI?*"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "PIDIENDO DNI")
                    hist = sesion.get("menu_history", []); hist.append(estado_actual) if not hist or hist[-1] != estado_actual else None
                    sesion["menu_state"] = "capturando_motivo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return

                elif siguiente_estado.startswith("pre_action_humano"):
                    contexto = siguiente_estado.replace("pre_action_humano_", "").upper().replace("_", " ")
                    sesion["contexto_derivacion"] = contexto
                    msg = "Para asignar tu caso de forma correcta, por favor descríbeme en un solo mensaje:\n*¿Cuál es exactamente tu requerimiento o consulta?*"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "PIDIENDO MOTIVO")
                    hist = sesion.get("menu_history", []); hist.append(estado_actual) if not hist or hist[-1] != estado_actual else None
                    sesion["menu_state"] = "capturando_motivo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return

                elif siguiente_estado == "ver_pendientes_imo":
                    lista = buscar_pendientes_imo_csv(telefono)
                    msg = f"📊 *Reporte de Equipo (Rezagados)*\n\n" + "\n".join(lista) + "\n\n_Escribe *0* para volver._" if lista else "¡Felicidades! 🎉 Todos tus participantes se han sentado o no tienes pendientes.\n\n_Escribe *0* para volver._"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "REPORTE PENDIENTES")
                    hist = sesion.get("menu_history", []); hist.append(estado_actual) if not hist or hist[-1] != estado_actual else None
                    sesion["menu_state"] = "ver_pendientes_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return

                elif siguiente_estado == "ver_todos_imo":
                    sentados, no_sentados = reporte_sentados_imo(telefono)
                    msg = f"📊 *Reporte Especial de Comunidad*\n\n✅ *Sentados / Activos:*\n" + ("\n".join(sentados) if sentados else "Ninguno") + "\n\n⏳ *No Sentados / Rezagados:*\n" + ("\n".join(no_sentados) if no_sentados else "Ninguno") + "\n\n_Escribe *0* para volver al menú._"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "REPORTE TODOS ENROLADOS")
                    hist = sesion.get("menu_history", []); hist.append(estado_actual) if not hist or hist[-1] != estado_actual else None
                    sesion["menu_state"] = "ver_todos_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return
                    
                elif siguiente_estado == "action_salir":
                    sesion["menu_state"] = "esperando_encuesta"; set_sesion(telefono, sesion)
                    enviar_mensaje(telefono, "Antes de irte, ¿Cómo calificarías tu experiencia en este chat?\n\nResponde con un número del *1 al 5*:\n1️⃣ = Mala\n5️⃣ = ¡Excelente!", nombre_mostrar, True, "ENCUESTA SALIDA")
                    return
                    
                elif siguiente_estado == "main": siguiente_estado = main_key
                    
                hist = sesion.get("menu_history", [])
                if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                sesion["menu_state"] = siguiente_estado; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                
                if siguiente_estado in MENU_STRUCTURE: enviar_mensaje(telefono, render_menu(siguiente_estado), nombre_mostrar, True, siguiente_estado)
            else:
                if not texto_limpio.isnumeric():
                    sesion["contexto_derivacion"] = "TEXTO LIBRE"
                    enviar_mensaje(telefono, "Para brindarte atención corporativa, por favor dime en un solo mensaje: *¿Qué necesitas consultar o resolver?*", nombre_mostrar, True, "PREGUNTANDO MOTIVO AUTO")
                    sesion["menu_state"] = "capturando_motivo"; set_sesion(telefono, sesion)
                    return
                
                errores = sesion.get("menu_errors", 0) + 1
                sesion["menu_errors"] = errores
                if errores >= 3:
                    sesion["menu_errors"] = 0
                    notificar_coordinadora_interna(telefono, perfil["nombre"], "Usuario atascado en el menú.", "SISTEMA ERROR")
                    enviar_mensaje(telefono, f"Noto que estamos teniendo problemas. He notificado a Coordinación para que te asista.\n\n_Escribe *0* para menú principal._", nombre_mostrar, True, "ERROR_DERIVADO")
                    sesion["menu_state"] = "esperando_humano"
                else:
                    enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado_actual)}", nombre_mostrar, True, "ERROR_MENU")
                set_sesion(telefono, sesion)

    except Exception as e:
        logger.error(f"Error en flujo principal: {e}", exc_info=True)

# ══════════════════════════════════════════════════════════════════════════
# 10. WEBHOOKS Y endpoints DEL PANEL WEB
# ══════════════════════════════════════════════════════════════════════════
# NOTA: El bloque HTML_CHAT se mantiene idéntico a las versiones anteriores, 
# conservando la separación estricta entre Simulador y Nuevo Chat Outbound.

@app.route("/api/mensaje_simulador", methods=["POST"])
def mensaje_simulador():
    data = request.json; tel = data.get("telefono"); texto = data.get("texto")
    if not tel or not texto: return jsonify({"error": "Faltan datos"}), 400
    sesion = get_sesion(tel)
    perfil = sesion.get("perfil", {})
    nombre_mostrar = f"({perfil.get('rol', 'PROSPECTO')}) {perfil.get('nombre', 'Simulado')}" if perfil.get('nombre') else "SIMULACIÓN"
    
    append_historial(tel, nombre_mostrar, texto, "in")
    registrar_en_sheets_smart(tel, nombre_mostrar, texto, "", "SIMULADOR", "", "")
    SessionManager.guardar_backup_absoluto(tel, nombre_mostrar, texto, "IN", "SIMULADOR")
    
    threading.Thread(target=flujo_principal, args=(tel, texto), daemon=True).start()
    return jsonify({"status": "ok"}), 200

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        mode, token, challenge = (request.args.get(k) for k in ["hub.mode","hub.verify_token","hub.challenge"])
        if mode == "subscribe" and token == Config.VERIFY_TOKEN: return challenge, 200
        return "Token invalido", 403

    data = request.get_json(silent=True)
    if not data: return jsonify({"status":"ok"}), 200
    try:
        changes = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
        if "messages" not in changes: return jsonify({"status":"ok"}), 200
        
        msg = changes["messages"][0]
        telefono = msg.get("from")
        tipo = msg.get("type", "")
        
        sesion = get_sesion(telefono)
        perfil = sesion.get("perfil")
        if not perfil: perfil = obtener_perfil_crm(telefono)
        nombre_cached = f"({perfil['rol']}) {perfil['nombre']}" if perfil.get('nombre') else "NUEVO CONTACTO"
        
        if tipo == "text":
            texto = str(msg["text"]["body"]).replace("=", "").replace("+", "").replace("@", "")
            append_historial(telefono, nombre_cached, texto, "in")
            
            if sesion.get("menu_state") not in ["capturando_motivo", "confirmando_derivacion"]:
                SessionManager.guardar_backup_absoluto(telefono, nombre_cached, texto, "IN", "RECIBIDO")
                registrar_en_sheets_smart(telefono, nombre_cached, texto, "", "RECIBIDO", "", "")

            threading.Thread(target=flujo_principal, args=(telefono, texto), daemon=True).start()
            
        elif tipo in ("audio","image","document","video","sticker"):
            append_historial(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "in")
            SessionManager.guardar_backup_absoluto(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "IN", "RECIBIDO")
            registrar_en_sheets_smart(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "", "RECIBIDO", "", "")
            
            # 🛡️ Escudo Anti-Audios en Handoff
            if sesion.get("menu_state") in ["capturando_motivo", "confirmando_derivacion"]:
                WhatsAppAPI.enviar_mensaje(telefono, "Por políticas de registro y rapidez, por favor escríbeme tu consulta *únicamente en texto*. No procesamos audios ni imágenes en esta etapa.", registrar_sheets=True, estado_menu="ERROR_MULTIMEDIA")
            elif sesion.get("menu_state") != "esperando_humano":
                WhatsAppAPI.enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.", registrar_sheets=True, estado_menu="ERROR_MULTIMEDIA")
            
    except Exception as e: logger.error(f"Error Webhook: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
