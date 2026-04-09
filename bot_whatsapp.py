"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
✅ Versión V77: Producción Total (Nodo Cero + Reloj Lima + Panel Real-Time + Dual Sync)
"""

import os, re, json, time, csv, io, random, logging, threading
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
            except Exception as e:
                logger.error(f"Error en backup local: {e}")

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
# 3. GOOGLE SHEETS (ESCRITURA INMEDIATA)
# ══════════════════════════════════════════════════════════════════════════
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
                req_lib.post(url, params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"}, 
                             json={"values": valores}, 
                             headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, timeout=10)
        except Exception as e: logger.error(f"Error Sheets: {e}")

def registrar_en_sheets_inmediato(tel, nom, msg, resp, est="", resp_man="", env_stat=""):
    if str(tel).startswith("SIM_"): return 
    threading.Thread(target=GoogleSheetsAPI.registrar_accion, args=(tel, nom, msg, resp, est, resp_man, env_stat), daemon=False).start()

# ══════════════════════════════════════════════════════════════════════════
# 4. CONECTORES DE WHATSAPP API
# ══════════════════════════════════════════════════════════════════════════
class WhatsAppAPI:
    @staticmethod
    def enviar_mensaje(telefono, texto, nombre_mostrar="", registrar_sheets=True, estado_menu=""):
        if str(telefono).startswith("SIM_"):
            append_historial(telefono, nombre_mostrar, texto, "out")
            registrar_en_sheets_inmediato(telefono, nombre_mostrar, "", texto[:500], estado_menu or "SIMULADOR")
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
                if registrar_sheets:
                    estado_actual = "SISTEMA" if nombre_mostrar == "SISTEMA" else "INTERACTIVO"
                    registrar_en_sheets_inmediato(telefono, nombre_mostrar, "", texto[:500], estado_menu or estado_actual)
                return True
        except: pass
        return False

def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=True, estado_menu="INTERACTIVO"):
    return WhatsAppAPI.enviar_mensaje(telefono, texto, nombre_imo, registrar_sheets, estado_menu)

# ══════════════════════════════════════════════════════════════════════════
# 5. UTILIDADES, CRM OMNICANAL Y RELOJ DINÁMICO
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
    min_len = min(len(t1), len(t2))
    if min_len >= 8 and (t1.endswith(t2) or t2.endswith(t1)): return True
    return False

def nombre_pila(s):
    partes = [p.strip() for p in re.split(r'\s+', s.strip()) if len(p.strip()) > 2]
    return partes[0].title() if partes else s.strip().title()

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
                    if estado in ("PENDIENTE","ENVIADO","") and px_n: px_list.append(px_n)
            wb.close()
            return imo_nombre, px_list
        except: return "", []

def obtener_perfil_crm(telefono):
    perfil = {"rol": "PROSPECTO", "nombre": None, "pendiente": None, "imo_nombre": None, "imo_tel": None}
    es_imo = False
    
    imo_nom, px_list = cargar_px_del_imo(telefono)
    if imo_nom and len(px_list) > 0:
        es_imo = True
        perfil["rol"] = "IMO"
        perfil["nombre"] = imo_nom
        
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
                                
                                si_c1 = (c1_stat == "SI" or c1_stat == "S")
                                si_c2 = (c2_stat == "SI" or c2_stat == "S")
                                si_mj = (mj_stat == "SI" or mj_stat == "S")
                                
                                if not si_c1:
                                    pendiente = "Capítulo 1 (C1)"
                                    rol_temp = "PX_REZAGADO_C1"
                                elif si_c1 and not si_c2:
                                    pendiente = "Capítulo 2 (C2)"
                                    rol_temp = "PX_UPSELL_C2"
                                elif si_c1 and si_c2 and not si_mj:
                                    pendiente = "Maestría (MJ)"
                                    rol_temp = "PX_UPSELL_MJ"
                                elif si_mj:
                                    pendiente = "Ninguno (Maestría iniciada)"
                                    rol_temp = "MJ"
                                else:
                                    pendiente = "Entrenamiento a validar"
                                    rol_temp = "PX"

                                perfil["px_pendiente"] = pendiente
                                perfil["rol_base"] = rol_temp
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
        perfil["rol"] = perfil.get("rol_base", "PX")
        
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
                    if c1_stat != "SI" and c1_stat != "S": falta = "C1"
                    elif c2_stat != "SI" and c2_stat != "S": falta = "C2"

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
                    
                    if mj == "SI" or mj == "S": estatus = "🎓 MJ Iniciado/Graduado"
                    elif c2 == "SI" or c2 == "S": estatus = "🔥 En Proceso (C2)"
                    elif c1 == "SI" or c1 == "S": estatus = "🚀 Inició (C1)"
                    else: estatus = "⏳ Rezagado (Falta C1)"
                    resultados.append(f"• {nombre_completo} - {estatus}")
            return resultados
    except: return []

def reporte_sentados_imo(telefono):
    """🧠 V77: Divide a la comunidad de un IMO en Sentados y No Sentados"""
    todos = buscar_todos_imo_csv(telefono)
    sentados = []
    no_sentados = []
    for r in todos:
        if "Rezagado" in r or "Falta" in r:
            no_sentados.append(r)
        else:
            sentados.append(r)
    return sentados, no_sentados

def marcar_stop(telefono):
    if str(telefono).startswith("SIM_"): return 
    hoy = ahora_lima().strftime("%d/%m/%Y %H:%M")
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

def get_fecha_activa(tipo_evento):
    """🚀 V77: RELOJ DINÁMICO INQUEBRANTABLE (Con Zona Horaria Lima Forzada)"""
    ahora = ahora_lima()
    
    if tipo_evento == "C1":
        # Cutoff: Viernes a las 11:30 AM
        limite_c1 = datetime(2026, 5, 1, 11, 30, tzinfo=TZ_LIMA)
        if ahora < limite_c1: return "Viernes 01 de Mayo de 2026 (Equipo 27)"
        else: return "Viernes 05 de Junio de 2026 (Equipo 28)"
        
    elif tipo_evento == "C2":
        # Cutoff: Jueves a las 15:30 (3:30 PM)
        limite_c2 = datetime(2026, 4, 9, 15, 30, tzinfo=TZ_LIMA)
        if ahora < limite_c2: return "Jueves 09 de Abril de 2026 (Equipo 26)"
        else: return "Jueves 14 de Mayo de 2026 (Equipo 27)"
        
    elif tipo_evento == "MJ":
        # Cutoff: Viernes a las 19:00 (7:00 PM)
        limite_mj = datetime(2026, 4, 17, 19, 0, tzinfo=TZ_LIMA)
        if ahora < limite_mj: return "Viernes 17 de Abril de 2026 (Equipos 24, 25, 26)"
        else: return "Viernes 22 de Mayo de 2026 (Equipos 25, 26, 27)"
        
    return "Fecha a confirmar"

# ══════════════════════════════════════════════════════════════════════════
# 6. ESTRUCTURAS DE MENÚS (V77 - UX NODO CERO)
# ══════════════════════════════════════════════════════════════════════════
COORDINADORAS_CONTACTOS = {"Diana": "51912379744", "Joyce": "51933599903", "Leyla": "51919502385", "Zuley": "51933599864"}

MENU_STRUCTURE = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites Perú*\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Inversión y Métodos de Pago\n3️⃣ Hablar con un Asesor\n0️⃣ Finalizar",
        "options": {"1": "info_entrenamientos", "2": "pagos", "3": "pre_action_humano_asesor", "0": "action_salir"}
    },
    "main_imo": {
        "text": "🌟 *Bienvenido Líder IMO {nombre}*\n\n1️⃣ Ver mis rezagados (Pendientes C1/C2)\n2️⃣ Ver estado de TODOS mis enrolados\n3️⃣ Requerimientos IMO (DNI / Reporte Sentados)\n4️⃣ Hablar con Soporte IMO\n0️⃣ Finalizar",
        "options": {"1": "ver_pendientes_imo", "2": "ver_todos_imo", "3": "pedir_dni_imo", "4": "pre_action_humano_soporte_imo", "0": "action_salir"}
    },
    "main_px_rezagado_c1": {
        "text": "🌟 *Hola {nombre}.*\nTienes pendiente vivir tu *Capítulo 1 (Fase de Descubrimiento)*. ¡Tu transformación te espera!\n\n1️⃣ Confirmar mi asistencia para la próxima fecha\n2️⃣ Ver fechas y horarios del C1\n3️⃣ Solicitar reprogramación a mi coordinadora\n4️⃣ Ver a mis invitados enrolados\n0️⃣ Finalizar",
        "options": {"1": "pre_action_humano_confirma", "2": "info_fechas", "3": "pre_action_humano_reprogramacion", "4": "ver_todos_imo", "0": "action_salir"}
    },
    "main_px_upsell_c2": {
        "text": "🌟 *¡Hola {nombre}! Diste el primer paso en C1.*\nTu siguiente nivel de transformación profunda te espera. Tienes pendiente tu *Capítulo 2 (C2)*.\n\n1️⃣ Información y fechas del Capítulo 2 (C2)\n2️⃣ Confirmar asistencia / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con mi coordinadora\n0️⃣ Finalizar",
        "options": {"1": "info_fechas", "2": "pagos", "3": "ver_todos_imo", "4": "pre_action_humano_asesoria", "0": "action_salir"}
    },
    "main_px_upsell_mj": {
        "text": "🌟 *¡Felicidades por completar tu C2, {nombre}!*\nEl último paso para llevar tu liderazgo a tu familia y finanzas es la *Maestría (MJ)*.\n\n1️⃣ Información y fechas de Maestría (MJ)\n2️⃣ Confirmar inscripción / Inversión\n3️⃣ Ver a mis invitados enrolados\n4️⃣ Hablar con mi coordinadora\n0️⃣ Finalizar",
        "options": {"1": "info_fechas", "2": "pagos", "3": "ver_todos_imo", "4": "pre_action_humano_asesoria", "0": "action_salir"}
    },
    "main_mj": {
        "text": "🌟 *Hola Líder {nombre}*\nVemos que has participado en Maestría. ¿Cuál es tu estatus actual?\n\n1️⃣ Soy Graduado (Aliado) 🎓\n2️⃣ Estoy en proceso (100 Días) ⏳\n3️⃣ Me retiré / Deserté 🛑\n0️⃣ Finalizar",
        "options": {"1": "mj_graduado", "2": "mj_proceso", "3": "mj_deserto", "0": "action_salir"}
    },
    "mj_graduado": {
        "text": "🌟 *¡Un honor saludarte, Graduado/Aliado {nombre}!*\nTu liderazgo inspira a otros. ¿En qué podemos apoyarte hoy?\n\n1️⃣ Enrolar a un nuevo participante\n2️⃣ Ver TODOS mis enrolados y estatus\n3️⃣ Hablar con una coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_enrolar", "2": "ver_todos_imo", "3": "pre_action_humano_soporte", "9": "volver", "0": "main"}
    },
    "mj_proceso": {
        "text": "🌟 *¡Sigue firme en tus 100 días, {nombre}!*\n\n1️⃣ Ver mis enrolados y pendientes\n2️⃣ Registrar un enrolamiento (Mi proceso)\n3️⃣ Soporte con mi coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "ver_todos_imo", "2": "pre_action_humano_registro_enrolado", "3": "pre_action_humano_soporte", "9": "volver", "0": "main"}
    },
    "mj_deserto": {
        "text": "Comprendemos. Cada persona tiene su propio ritmo. Si deseas retomar tu proceso, las puertas están abiertas.\n\n1️⃣ Hablar con una coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_retomar", "9": "volver", "0": "main"}
    },
    "info_entrenamientos": {
        "text": "📘 *Explorar Entrenamientos*\n\n1️⃣ Capítulo 1 (C1)\n2️⃣ Capítulo 2 (C2)\n3️⃣ Maestría (MJ)\n4️⃣ Fechas y lugares\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "info_c1", "2": "info_c2", "3": "info_mj", "4": "info_fechas", "9": "volver", "0": "main"}
    },
    "info_c1": {
        "text": "🚀 *Capítulo 1 (C1)*: Fase de Descubrimiento. 3 días diseñados para romper paradigmas.\n\n1️⃣ Hablar con un asesor\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_c1", "9": "volver", "0": "main"}
    },
    "info_c2": {
        "text": "🔥 *Capítulo 2 (C2)*: Transformación profunda. 4 días inmersivos.\n\n1️⃣ Hablar con un asesor\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_c2", "9": "volver", "0": "main"}
    },
    "info_mj": {
        "text": "👑 *Maestría (MJ)*: Liderazgo y acción. 100 días para crear hábitos inquebrantables.\n\n1️⃣ Hablar con un asesor\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_info_mj", "9": "volver", "0": "main"}
    },
    "info_fechas": {
        "text": "dinamico", 
        "options": {"1": "pre_action_humano_coordinacion", "9": "volver", "0": "main"}
    },
    "pagos": {
        "text": "💳 *Inversión y Pagos*\nBCP a nombre de Creación Cuántica E.I.R.L. (Cuenta Soles: 1934218307060).\n\n1️⃣ Enviar voucher / Factura\n9️⃣ Regresar\n0️⃣ Menú principal",
        "options": {"1": "pre_action_humano_pagos", "9": "volver", "0": "main"}
    }
}

def notificar_coordinadora_interna(prospecto_tel, prospecto_nombre, motivo):
    coord_nombre, coord_tel = random.choice(list(COORDINADORAS_CONTACTOS.items()))
    msg = f"🚨 *NUEVO TICKET ASIGNADO* 🚀\n*Nombre:* {prospecto_nombre or 'No especificado'}\n*Teléfono:* wa.me/{prospecto_tel}\n*Requerimiento:* {motivo}"
    enviar_mensaje(coord_tel, msg, f"COORDINADORA: {coord_nombre}", True, "ALERTA TICKET")
    return coord_nombre

# ══════════════════════════════════════════════════════════════════════════
# 7. PROCESADOR DE ESTADOS (FLUJO ESTRICTO Y FILTRO ANTI-SPAM)
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

        # --- FILTROS DE CAPTURA DE TEXTO ---
        if sesion.get("menu_state") == "esperando_encuesta":
            if texto_limpio in ["1", "2", "3", "4", "5"]:
                enviar_mensaje(telefono, "¡Gracias por tu calificación! 🌟\n_Escribe MENU para reiniciar._", nombre_mostrar, True, "ENCUESTA CSAT")
                borrar_sesion(telefono)
            else: enviar_mensaje(telefono, "Por favor califica con un número del 1 al 5.", nombre_mostrar, True, "ERROR CSAT")
            return

        if sesion.get("menu_state") == "capturando_motivo":
            if texto_limpio not in ["0", "MENU"]:
                motivo = texto
                contexto = sesion.get("contexto_derivacion", "GENERAL")
                c_nom = notificar_coordinadora_interna(telefono, perfil["nombre"], f"[{contexto}] {motivo}")
                enviar_mensaje(telefono, f"¡Excelente! Tu consulta ha sido derivada a nuestra coordinadora *{c_nom}*. Te responderá por este chat pronto.\n\n_Escribe *0* para volver al menú._", nombre_mostrar, True, "DERIVACIÓN EXITOSA")
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return

        if sesion.get("menu_state") == "capturando_dni_imo":
            if texto_limpio not in ["0", "MENU"]:
                dni = texto_limpio
                sentados, no_sentados = reporte_sentados_imo(telefono)
                msg = f"📊 *Reporte Especial IMO (DNI: {dni})*\n\n✅ *Sentados / Activos:*\n"
                msg += "\n".join(sentados) if sentados else "Ninguno"
                msg += "\n\n⏳ *No Sentados / Rezagados:*\n"
                msg += "\n".join(no_sentados) if no_sentados else "Ninguno"
                msg += "\n\n_Escribe *0* para volver al menú._"
                enviar_mensaje(telefono, msg, nombre_mostrar, True, "REPORTE DNI")
                sesion["menu_state"] = "ver_todos_imo" 
                set_sesion(telefono, sesion)
                return

        # --- EVALUACIÓN DE ESTADO ---
        try:
            last_time = datetime.strptime(sesion.get("last_interaction", "2000-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")
            minutos_inactividad = (datetime.now() - last_time).total_seconds() / 60.0
        except: minutos_inactividad = 9999
        sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
                return f"📅 *Fechas Disponibles (Únicas Vigentes)*\n\n🚀 *C1:* {get_fecha_activa('C1')}\n🔥 *C2:* {get_fecha_activa('C2')}\n👑 *MJ:* {get_fecha_activa('MJ')}\n\n1️⃣ Hablar con coordinadora\n9️⃣ Regresar\n0️⃣ Menú principal"
            txt = MENU_STRUCTURE[m_key]["text"]
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
                
                # 🚀 V77: Handoff Universal Dinámico
                if siguiente_estado.startswith("pre_action_humano"):
                    contexto = siguiente_estado.replace("pre_action_humano_", "").upper()
                    if contexto == "PRE_ACTION_HUMANO": contexto = "SOPORTE GENERAL"
                    sesion["contexto_derivacion"] = contexto
                    
                    msg = "Para asignar tu caso de forma correcta y rápida, por favor descríbeme en un solo mensaje:\n*¿Cuál es exactamente tu requerimiento o consulta?*"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "PREGUNTANDO MOTIVO")
                    
                    hist = sesion.get("menu_history", [])
                    if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                    sesion["menu_state"] = "capturando_motivo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return
                
                elif siguiente_estado == "pedir_dni_imo":
                    enviar_mensaje(telefono, "🔒 *Validación IMO*\nPor favor, digita tu número de *DNI* para generar tu reporte de enrolados (Sentados vs. No Sentados).", nombre_mostrar, True, "PIDIENDO DNI")
                    hist = sesion.get("menu_history", [])
                    if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                    sesion["menu_state"] = "capturando_dni_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return

                elif siguiente_estado == "ver_pendientes_imo":
                    lista = buscar_pendientes_imo_csv(telefono)
                    if lista: msg = f"📊 *Reporte de tu Equipo (Rezagados)*\n\n" + "\n".join(lista) + "\n\n_Escribe *0* para volver._"
                    else: msg = "¡Felicidades! 🎉 Todos tus participantes se han sentado o no tienes pendientes.\n\n_Escribe *0* para volver._"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "REPORTE PENDIENTES")
                    hist = sesion.get("menu_history", []); 
                    if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
                    sesion["menu_state"] = "ver_pendientes_imo"; sesion["menu_history"] = hist; set_sesion(telefono, sesion)
                    return

                elif siguiente_estado == "ver_todos_imo":
                    lista_todos = buscar_todos_imo_csv(telefono)
                    if lista_todos: msg = f"📊 *Reporte de Tus Enrolados / Comunidad*\n\n" + "\n".join(lista_todos) + "\n\n_Escribe *0* para volver._"
                    else: msg = "Aún no tienes enrolados registrados a tu nombre en la base.\n\n_Escribe *0* para volver._"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "REPORTE TODOS ENROLADOS")
                    hist = sesion.get("menu_history", [])
                    if estado_actual != main_key and (not hist or hist[-1] != estado_actual): hist.append(estado_actual)
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
                elif siguiente_estado == "action_imo": enviar_mensaje(telefono, f"¡Hola líder! 👋\n\nEstás en el *Portal IMO*. Envíame el estatus de tus participantes y lo validaremos.\n\n_Escribe *0* para volver._", nombre_mostrar, True, "REPORTE MANUAL IMO")
            else:
                if not texto_limpio.isnumeric():
                    sesion["contexto_derivacion"] = "TEXTO LIBRE"
                    msg = "Para brindarte atención humana, por favor dime en un solo mensaje: *¿Qué necesitas consultar o resolver?*"
                    enviar_mensaje(telefono, msg, nombre_mostrar, True, "PREGUNTANDO MOTIVO AUTO")
                    sesion["menu_state"] = "capturando_motivo"
                    set_sesion(telefono, sesion)
                    return
                
                errores = sesion.get("menu_errors", 0) + 1
                sesion["menu_errors"] = errores
                if errores >= 3:
                    sesion["menu_errors"] = 0
                    c_nom = notificar_coordinadora_interna(telefono, perfil["nombre"], "Usuario atascado en el menú.")
                    enviar_mensaje(telefono, f"Noto que estamos teniendo problemas. He notificado a *{c_nom}* para que te asista.\n\n_Escribe *0* para menú principal._", nombre_mostrar, True, "ERROR_DERIVADO")
                    sesion["menu_state"] = "esperando_humano"
                else:
                    enviar_mensaje(telefono, f"⚠️ *Opción no válida*. Responde únicamente con el *número*.\n\n{render_menu(estado_actual)}", nombre_mostrar, True, "ERROR_MENU")
                set_sesion(telefono, sesion)

        elif estado_actual in ["esperando_humano", "esperando_fecha", "ver_todos_imo", "ver_pendientes_imo"]:
            set_sesion(telefono, sesion)

    except Exception as e:
        logger.error(f"Error en flujo principal: {e}", exc_info=True)

# ══════════════════════════════════════════════════════════════════════════
# 8. PANEL WEB (HTML), ENDPOINTS Y SIMULADOR
# ══════════════════════════════════════════════════════════════════════════
HTML_CHAT = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CPSL — Centro de Comunicaciones C1 E27</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f5f4f0;color:#1a1a18;height:100vh;overflow:hidden}
.overlay{position:fixed;inset:0;background:rgba(0,0,0,.45);display:flex;align-items:center;justify-content:center;z-index:900}
.modal{background:#fff;border-radius:12px;padding:28px 32px;width:500px;max-height:90vh;overflow-y:auto}
.modal h2{font-size:16px;font-weight:600;margin-bottom:4px}
.modal .sub{font-size:12px;color:#888780;margin-bottom:20px}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:#5f5e5a;margin-bottom:4px;text-transform:uppercase;letter-spacing:.4px}
.field input,.field textarea{width:100%;padding:8px 10px;font-size:13px;border:.5px solid #b4b2a9;border-radius:8px;background:#fafaf8;color:#1a1a18;outline:none;font-family:'SF Mono',monospace}
.field textarea{resize:vertical;min-height:80px;font-size:11px}
.field input:focus,.field textarea:focus{border-color:#1D9E75;background:#fff}
.field .hint{font-size:11px;color:#888780;margin-top:3px}
.btn-primary{width:100%;padding:10px;background:#1D9E75;color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;margin-top:6px}
.btn-primary:hover{background:#0F6E56}
.modal-note{text-align:center;margin-top:10px;font-size:11px;color:#888780}
.btn-link{background:none;border:none;color:#1D9E75;font-size:11px;cursor:pointer;text-decoration:underline;padding:0}
.app{display:grid;grid-template-columns:300px 1fr;height:100vh}
.sidebar{border-right:.5px solid #d3d1c7;display:flex;flex-direction:column;background:#f5f4f0;min-width:0}
.sb-header{padding:12px 14px 10px;border-bottom:.5px solid #d3d1c7}
.sb-top{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.sb-title{font-size:13px;font-weight:600}
.sync-row{display:flex;align-items:center;gap:4px}
.sync-dot{width:6px;height:6px;border-radius:50%;background:#d3d1c7;transition:background .3s;flex-shrink:0}
.sync-dot.ok{background:#1D9E75}
.sync-dot.busy{background:#BA7517;animation:blink 1s infinite}
.sync-dot.err{background:#A32D2D}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
.sync-text{font-size:10px;color:#888780}
.btn-cfg{font-size:10px;padding:2px 6px;border:.5px solid #d3d1c7;border-radius:6px;background:transparent;color:#888780;cursor:pointer;margin-left:2px}
.btn-cfg:hover{background:#fff}
.search{width:100%;padding:7px 10px;font-size:13px;border:.5px solid #b4b2a9;border-radius:8px;background:#fff;color:#1a1a18;outline:none}
.search:focus{border-color:#1D9E75}
.tabs{display:flex;gap:4px;padding:8px 14px;border-bottom:.5px solid #d3d1c7;flex-wrap:wrap}
.tab{font-size:11px;padding:3px 8px;border-radius:20px;border:.5px solid #d3d1c7;background:transparent;color:#888780;cursor:pointer;white-space:nowrap}
.tab.on{background:#fff;color:#1a1a18;border-color:#888780;font-weight:600}
.stats{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:.5px solid #d3d1c7}
.stat{text-align:center;padding:7px 2px;border-right:.5px solid #d3d1c7}
.stat:last-child{border-right:none}
.stat-n{font-size:15px;font-weight:600}
.stat-l{font-size:10px;color:#888780}
.list{overflow-y:auto;flex:1}
.item{padding:10px 14px;border-bottom:.5px solid #d3d1c7;cursor:pointer;transition:background .1s}
.item:hover{background:#fff}
.item.on{background:#fff;border-left:2px solid #1D9E75}
.item-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:2px}
.item-name{font-size:13px;font-weight:600;color:#1a1a18;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:180px}
.item-time{font-size:10px;color:#888780;flex-shrink:0}
.item-prev{font-size:12px;color:#5f5e5a;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:240px}
.item-bot{display:flex;align-items:center;justify-content:space-between;margin-top:3px}
.dot-unread{width:7px;height:7px;border-radius:50%;background:#1D9E75;flex-shrink:0}
.new-btn{margin:10px 14px;padding:8px;width:calc(100% - 28px);background:transparent;border:.5px dashed #b4b2a9;border-radius:8px;font-size:12px;color:#888780;cursor:pointer;text-align:center}
.new-btn:hover{background:#fff;color:#1a1a18;border-color:#888780}
.badge{display:inline-block;font-size:10px;padding:2px 6px;border-radius:10px;font-weight:600}
.b-pendiente{background:#FAEEDA;color:#854F0B}
.b-confirma{background:#EAF3DE;color:#3B6D11}
.b-noasiste{background:#FCEBEB;color:#A32D2D}
.b-stop{background:#F1EFE8;color:#5F5E5A}
.b-cambio{background:#E6F1FB;color:#185FA5}
.b-externo{background:#EEEDFE;color:#534AB7}
.chat{display:flex;flex-direction:column;height:100vh;background:#fff}
.ch-header{padding:12px 18px;border-bottom:.5px solid #d3d1c7;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}
.ch-left{display:flex;align-items:center;gap:10px}
.avatar{width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;flex-shrink:0}
.av-imo{background:#E1F5EE;color:#0F6E56}
.av-ext{background:#EEEDFE;color:#534AB7}
.ch-name{font-size:14px;font-weight:600;color:#1a1a18}
.ch-sub{font-size:11px;color:#888780;margin-top:1px}
.ch-actions{display:flex;gap:4px;flex-wrap:wrap}
.btn-s{font-size:11px;padding:4px 8px;border-radius:7px;border:.5px solid #b4b2a9;background:transparent;color:#5f5e5a;cursor:pointer;white-space:nowrap}
.btn-s:hover{background:#f5f4f0}
.messages{flex:1;overflow-y:auto;padding:14px 18px;display:flex;flex-direction:column;gap:8px;background:#fafaf8}
.msg{display:flex;flex-direction:column;max-width:76%}
.msg.in{align-self:flex-start}
.msg.out{align-self:flex-end}
.msg-who{font-size:10px;color:#888780;margin-bottom:2px}
.msg.out .msg-who{text-align:right}
.bubble{padding:8px 12px;border-radius:12px;font-size:13px;line-height:1.5;word-break:break-word}
.msg.in .bubble{background:#fff;color:#1a1a18;border:.5px solid #d3d1c7;border-radius:3px 12px 12px 12px}
.msg.out .bubble{background:#1D9E75;color:#fff;border-radius:12px 3px 12px 12px}
.msg.out.pending .bubble{background:#5DCAA5}
.msg-st{font-size:10px;color:#888780;margin-top:2px;text-align:right}
.date-sep{text-align:center;font-size:10px;color:#b4b2a9;padding:2px 0;flex-shrink:0}
.empty{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:#888780;gap:8px;font-size:13px}
.footer{border-top:.5px solid #d3d1c7;padding:9px 14px 11px;background:#fff;flex-shrink:0}
.px-row{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:7px;align-items:center}
.px-lbl{font-size:10px;color:#888780}
.px-chip{font-size:11px;padding:2px 8px;border-radius:20px;border:.5px solid #b4b2a9;color:#5f5e5a;cursor:pointer;background:transparent}
.px-chip:hover{background:#f5f4f0}
.px-chip.on{background:#E1F5EE;color:#0F6E56;border-color:#5DCAA5}
.qr-row{display:flex;gap:4px;flex-wrap:wrap;margin-bottom:7px}
.qr{font-size:11px;padding:3px 8px;border-radius:20px;border:.5px solid #b4b2a9;background:transparent;color:#5f5e5a;cursor:pointer;white-space:nowrap}
.qr:hover{background:#f5f4f0;color:#1a1a18}
.input-row{display:flex;gap:7px;align-items:flex-end}
.tinput{flex:1;padding:8px 11px;font-size:13px;border:.5px solid #b4b2a9;border-radius:8px;background:#f5f4f0;color:#1a1a18;resize:none;outline:none;min-height:36px;max-height:110px;font-family:inherit;line-height:1.4}
.tinput:focus{border-color:#1D9E75;background:#fff}
.send{padding:8px 16px;background:#1D9E75;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;flex-shrink:0}
.send:hover{background:#0F6E56}
.send:disabled{background:#9FE1CB;cursor:not-allowed}
.foot-meta{display:flex;justify-content:space-between;margin-top:3px}
.foot-meta span{font-size:10px;color:#888780}
</style>
</head>
<body>

<div class="overlay" id="ovl-cfg">
  <div class="modal">
    <h2>Configurar conexión</h2>
    <p class="sub">Los datos se guardan solo en tu navegador. No salen de tu PC.</p>
    <div class="field">
      <label>Sheet ID</label>
      <input id="c-sid" placeholder="1NqEgzCkixVhMn3VLhsy_GVWwYBfwLQ1rwdHVcKTRyjo">
    </div>
    <div class="field">
      <label>Nombre de la pestaña</label>
      <input id="c-sname" value="Hoja 1">
    </div>
    <div class="field">
      <label>Credenciales Google — JSON completo</label>
      <textarea id="c-creds" placeholder='{"type":"service_account",...}'></textarea>
    </div>
    <div class="field">
      <label>WA Token</label>
      <input id="c-watok" type="password" placeholder="EAAxxxxxxx">
    </div>
    <div class="field">
      <label>WA Phone Number ID</label>
      <input id="c-wapid" placeholder="1085205258006361">
    </div>
    <button class="btn-primary" onclick="guardarCfg()">Conectar y abrir app</button>
    <p class="modal-note"><button class="btn-link" onclick="usarDemoMode()">Continuar en modo demo</button></p>
  </div>
</div>

<div class="overlay" id="ovl-new" style="display:none">
  <div class="modal" style="width:380px;padding:22px 26px">
    <h2 style="margin-bottom:14px">Nueva conversación</h2>
    <div class="field"><label>Nombre</label><input id="n-nombre" placeholder="Nombre completo"></div>
    <div class="field"><label>Teléfono (con código de país)</label><input id="n-tel" type="tel" placeholder="51987654321"></div>
    <div style="display:flex;gap:8px;margin-top:4px">
      <button style="flex:1;padding:9px;border:.5px solid #b4b2a9;border-radius:8px;background:transparent;font-size:13px;color:#5f5e5a;cursor:pointer" onclick="cerrarNuevo()">Cancelar</button>
      <button style="flex:1;padding:9px;background:#1D9E75;color:#fff;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer" onclick="crearNuevo()">Iniciar</button>
    </div>
  </div>
</div>

<div class="app" id="app" style="display:none">
  <div class="sidebar">
    <div class="sb-header">
      <div class="sb-top">
        <span class="sb-title">Mesa de Control C1 E27</span>
        <div class="sync-row">
          <div class="sync-dot" id="sdot"></div>
          <span class="sync-text" id="stxt">—</span>
          <button class="sim-btn btn-cfg" style="background:#1a73e8; color:white; border:none;" onclick="iniciarSimulador()">🧪 Simular</button>
          <button class="btn-cfg" onclick="abrirCfg()">⚙</button>
        </div>
      </div>
      <input class="search" type="text" id="search" placeholder="Buscar nombre o teléfono…" oninput="renderLista()">
    </div>

    <div class="tabs">
      <button class="tab on" data-tab="todos" onclick="setTab(this)">Todos</button>
      <button class="tab" data-tab="pendiente" onclick="setTab(this)">Pendiente</button>
      <button class="tab" data-tab="confirma" onclick="setTab(this)">Confirma</button>
      <button class="tab" data-tab="no asiste" onclick="setTab(this)">No asiste</button>
      <button class="tab" data-tab="externo" onclick="setTab(this)">Externos</button>
    </div>

    <div class="stats">
      <div class="stat"><div class="stat-n" id="st0">0</div><div class="stat-l">Total</div></div>
      <div class="stat"><div class="stat-n" id="st1" style="color:#1D9E75">0</div><div class="stat-l">Confirman</div></div>
      <div class="stat"><div class="stat-n" id="st2" style="color:#BA7517">0</div><div class="stat-l">Pendiente</div></div>
      <div class="stat"><div class="stat-n" id="st3" style="color:#A32D2D">0</div><div class="stat-l">No asiste</div></div>
    </div>

    <div class="list" id="list"></div>
    <button class="new-btn" onclick="abrirNuevo()">+ Nueva conversación</button>
  </div>

  <div class="chat" id="chat">
    <div class="empty">
      <div style="width:44px;height:44px;border-radius:50%;background:#E1F5EE;display:flex;align-items:center;justify-content:center;font-size:20px">💬</div>
      <span>Selecciona una conversación</span>
      <span style="font-size:11px;color:#b4b2a9">Dual-Sync activo (Tiempo Real) - Hora Perú</span>
    </div>
  </div>
</div>

<script>
const CFG_KEY  = 'cpsl_cfg_v2';
const DEMO_KEY = 'cpsl_demo_v2';

const QR = [
  {l:'Info C1', t:'Hola, aquí tienes la información del Capítulo 1:\\n\\nHotel José Antonio Deluxe\\nCalle Bellavista 133, Miraflores\\n\\nViernes: registro 9:00am, inicio 10:00am\\nSábado: ingreso 9:00am, inicio 10:00am\\nDomingo: inicio 9:00am, cierre 9:00pm\\n\\nComunicaciones Crear Poder Sin Límites Perú'},
  {l:'Confirmar', t:'Hola, gracias por informarnos. Confirmación registrada.\\n\\nLos esperamos en el Hotel José Antonio Deluxe. Mesa de registro a las 9:00am.\\n\\nComunicaciones Crear Poder Sin Límites Perú'},
  {l:'No asiste', t:'Hola, recibido. La inscripción sigue activa para el siguiente equipo inmediato.\\n\\nComunicaciones Crear Poder Sin Límites Perú'},
  {l:'Cambio nombre', t:'Hola, los cambios de nombre se gestionan con tu coordinadora antes del miércoles previo hasta las 6:00pm.\\n\\nComunicaciones Crear Poder Sin Límites Perú'}
];

let CFG = {}; let DEMO = false; let convs = []; let curTel = null; let filtro = 'todos';
let syncing = false; let syncTimer = null; let rowMap = {}; let _tok = null; let _tokExp = 0;

let audioNotif = new Audio('https://assets.mixkit.co/active_storage/sfx/2354/2354-preview.mp3');

function esc(s){ return String(s).split('&').join('&amp;').split('<').join('&lt;').split('>').join('&gt;').split('"').join('&quot;').split("'").join('&#39;'); }
function nl2br(s){ return esc(s).split('\\n').join('<br>'); }
function ini(n){ const p=n.trim().split(' '); return ((p[0]||'')[0]+(p[1]||'')[0]||'').toUpperCase(); }
function hora(){ return new Date().toLocaleTimeString('es-PE',{hour:'2-digit',minute:'2-digit', timeZone: 'America/Lima'}); }
function fecha(){ return new Date().toLocaleString('es-PE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit', timeZone: 'America/Lima'}); }

function badgeClass(estado, ext){
  if(ext) return 'b-externo';
  const e = (estado||'').toLowerCase().split(' ').join('');
  return {confirma:'b-confirma',pendiente:'b-pendiente',noasiste:'b-noasiste',stop:'b-stop',cambio:'b-cambio'}[e] || 'b-pendiente';
}

function setSyncStatus(tipo, txt){
  const d = document.getElementById('sdot'); const s = document.getElementById('stxt');
  if(!d) return; d.className = 'sync-dot ' + tipo; s.textContent = txt;
}
function setFootStatus(msg){ const el = document.getElementById('fstatus'); if(el) el.textContent = msg; }

function cargarCfg(){
  try { CFG = JSON.parse(localStorage.getItem(CFG_KEY)||'{}'); } catch(e){ CFG={}; }
  if(CFG.sid){ document.getElementById('c-sid').value = CFG.sid; }
  if(CFG.sname){ document.getElementById('c-sname').value = CFG.sname; }
  if(CFG.watok){ document.getElementById('c-watok').value = CFG.watok; }
  if(CFG.wapid){ document.getElementById('c-wapid').value = CFG.wapid; }
}

function guardarCfg(){
  const sid   = document.getElementById('c-sid').value.trim();
  const sname = document.getElementById('c-sname').value.trim()||'Hoja 1';
  const creds = document.getElementById('c-creds').value.trim();
  const watok = document.getElementById('c-watok').value.trim();
  const wapid = document.getElementById('c-wapid').value.trim();

  if(!sid)  { alert('El Sheet ID es obligatorio.'); return; }
  if(!creds){ alert('Las credenciales JSON son obligatorias.'); return; }

  try{
    const c = JSON.parse(creds);
    if(!c.private_key||!c.client_email) throw new Error('Faltan campos');
  } catch(e){
    alert('El JSON de credenciales no es válido: '+e.message); return;
  }

  CFG = {sid, sname, creds, watok, wapid};
  const forStorage = {sid, sname, watok, wapid};
  localStorage.setItem(CFG_KEY, JSON.stringify(forStorage));
  sessionStorage.setItem('cpsl_creds', creds);

  DEMO = false;
  document.getElementById('ovl-cfg').style.display='none';
  document.getElementById('app').style.display='grid';
  iniciar();
}

function abrirCfg(){
  document.getElementById('ovl-cfg').style.display='flex';
  document.getElementById('app').style.display='none';
  if(syncTimer){ clearInterval(syncTimer); syncTimer=null; }
}

function usarDemoMode(){
  DEMO = true; CFG = {sid:'demo', sname:'Hoja 1', creds:'', watok:'', wapid:''};
  document.getElementById('ovl-cfg').style.display='none';
  document.getElementById('app').style.display='grid';
  cargarDemoData(); iniciarUI();
}

function cargarDemoData(){
  convs = [];
}

async function getToken(){
  if(_tok && Date.now() < _tokExp - 60000) return _tok;
  if(DEMO) return null;

  const credsStr = CFG.creds || sessionStorage.getItem('cpsl_creds') || '';
  if(!credsStr) return null;

  let creds;
  try{ creds = JSON.parse(credsStr); } catch(e){ setSyncStatus('err','JSON inválido'); return null; }

  try{
    const now = Math.floor(Date.now()/1000);
    const b64u = function(s) {
        let res = btoa(s);
        res = res.split('+').join('-');
        res = res.split('/').join('_');
        res = res.split('=').join('');
        return res;
    };
    const enc = function(s) {
        return b64u(unescape(encodeURIComponent(JSON.stringify(s))));
    };

    const hdr = enc({alg:'RS256',typ:'JWT'});
    const pld = enc({iss:creds.client_email, scope:'https://www.googleapis.com/auth/spreadsheets', aud:'https://oauth2.googleapis.com/token', iat:now, exp:now+3600});

    let pemBody = creds.private_key;
    pemBody = pemBody.split('-----BEGIN PRIVATE KEY-----').join('');
    pemBody = pemBody.split('-----END PRIVATE KEY-----').join('');
    pemBody = pemBody.split(String.fromCharCode(10)).join('');
    pemBody = pemBody.split(String.fromCharCode(13)).join('');
    pemBody = pemBody.split(' ').join('');

    const keyBuf = Uint8Array.from(atob(pemBody), c=>c.charCodeAt(0)).buffer;
    const cryptoKey = await crypto.subtle.importKey('pkcs8', keyBuf, {name:'RSASSA-PKCS1-v1_5',hash:'SHA-256'}, false, ['sign']);
    const sigBuf = await crypto.subtle.sign('RSASSA-PKCS1-v1_5', cryptoKey, new TextEncoder().encode(hdr + '.' + pld));
    
    let sig = String.fromCharCode(...new Uint8Array(sigBuf));
    sig = b64u(sig);
    
    const jwt = hdr + '.' + pld + '.' + sig;

    const r = await fetch('https://oauth2.googleapis.com/token',{ 
        method:'POST', 
        headers:{'Content-Type':'application/x-www-form-urlencoded'}, 
        body: 'grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Ajwt-bearer&assertion=' + jwt 
    });
    if(!r.ok) throw new Error('Token HTTP '+r.status);
    const d = await r.json();
    if(!d.access_token) throw new Error(d.error_description||'Sin token');
    _tok = d.access_token;
    _tokExp = Date.now() + (d.expires_in||3600)*1000;
    return _tok;
  } catch(e){
    setSyncStatus('err','Auth: '+e.message);
    console.error('JWT error:',e);
    return null;
  }
}

async function sheetFetch(url, opts, retries=2){
  for(let i=0; i<=retries; i++){
    try{
      const r = await fetch(url, opts);
      if(r.status===429||r.status===503){ if(i<retries){ await new Promise(res=>setTimeout(res,1500*(i+1))); continue; } throw new Error('Rate limit'); }
      return r;
    } catch(e){ if(i===retries) throw e; await new Promise(res=>setTimeout(res,1000)); }
  }
}

const rng    = () => encodeURIComponent((CFG.sname||'Hoja 1')+'!A:H');
const shBase = () => `https://sheets.googleapis.com/v4/spreadsheets/${CFG.sid}/values/${rng()}`;

async function leerSheet(){
  const tok = await getToken();
  if(!tok) return null;
  const r = await sheetFetch(shBase(), {headers:{Authorization:`Bearer ${tok}`}});
  if(!r||!r.ok){ setSyncStatus('err','Error leyendo Sheet ('+r?.status+')'); return null; }
  const data = await r.json();
  return data.values || [];
}

async function escribirCelda(fila, col, valor){
  const tok = await getToken();
  if(!tok) return false;
  const colLetter = String.fromCharCode(64+col);
  const rango = encodeURIComponent(`${CFG.sname||'Hoja 1'}!${colLetter}${fila}`);
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${CFG.sid}/values/${rango}?valueInputOption=USER_ENTERED`;
  const r = await sheetFetch(url,{ method:'PUT', headers:{Authorization:`Bearer ${tok}`,'Content-Type':'application/json'}, body:JSON.stringify({values:[[valor]]}) });
  return r && r.ok;
}

async function appendFila(vals){
  const tok = await getToken();
  if(!tok) return false;
  const url = `https://sheets.googleapis.com/v4/spreadsheets/${CFG.sid}/values/${rng()}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS`;
  const r = await sheetFetch(url,{ method:'POST', headers:{Authorization:`Bearer ${tok}`,'Content-Type':'application/json'}, body:JSON.stringify({values:[vals]}) });
  return r && r.ok;
}

async function enviarWA(tel, texto){
  const watok = CFG.watok || '';
  const wapid = CFG.wapid || '';
  if(!watok||!wapid) return {ok:false, err:'Sin credenciales WA'};
  try{
    const r = await fetch(`https://graph.facebook.com/v19.0/${wapid}/messages`,{ method:'POST', headers:{Authorization:`Bearer ${watok}`,'Content-Type':'application/json'}, body:JSON.stringify({messaging_product:'whatsapp',to:String(tel),type:'text',text:{body:texto,preview_url:false}}) });
    const d = await r.json();
    if(!r.ok) return {ok:false, err:(d.error?.message||'Error '+r.status)};
    return {ok:true};
  } catch(e){ return {ok:false, err:e.message}; }
}

async function sincronizarMensajesInstantaneos() {
    try {
        let res = await fetch('/api/historial');
        let data = await res.json();
        let cambios = false;

        for(let m of data) {
            let tel = m.telefono;
            let c = convs.find(x => x.tel === tel);
            if (!c) {
                c = {tel: tel, nombre: m.nombre || '+' + tel, estado: 'pendiente', ext: true, unread: false, rowNum: null, px: [], msgs: []};
                convs.push(c);
                cambios = true;
            }
            
            let ya = c.msgs.some(x => x.texto === m.texto);
            if (!ya) {
                let dir = m.tipo === 'in' ? 'in' : 'out';
                c.msgs.push({dir: dir, texto: m.texto, h: m.hora, st: dir === 'out' ? 'Enviado' : '', tipo: dir, row: 999999});
                if (dir === 'in' && curTel !== tel) {
                    c.unread = true;
                    document.title = "🔴 Nuevo Mensaje - CPSL";
                    try{ audioNotif.play(); }catch(e){}
                }
                cambios = true;
            }
        }

        if (cambios) {
            renderLista();
            if (curTel) actualizarMensajes();
        }
    } catch (e) {}
}

async function sincronizarSheets(){
  if(syncing||DEMO) return;
  syncing = true;
  setSyncStatus('busy','Sincronizando Sheets…');
  try{
    const rows = await leerSheet();
    if(!rows){ syncing=false; return; }

    let cambios = false;
    const ahora = hora();

    rows.forEach((row, i) => {
      if(i===0) return;
      const tel    = (row[1]||'').toString().trim();
      const nombre = (row[2]||'').trim();
      const estado = (row[5]||'pendiente').toLowerCase();
      if(!tel) return;

      rowMap[tel] = i+1;
      let c = convs.find(x=>x.tel===tel);
      if(!c){
        c = {tel, nombre:nombre||'+'+tel, estado, ext:!nombre, unread:false, rowNum:i+1, px:[], msgs:[]};
        convs.push(c); cambios=true;
      }
      if(nombre && c.nombre==='+'+tel){ c.nombre=nombre; cambios=true; }
      if(estado && c.estado!==estado){ c.estado=estado; cambios=true; }
    });

    if(cambios){ renderStats(); renderLista(); if(curTel) actualizarMensajes(); }
    setSyncStatus('ok', hora());
  } catch(e){
    setSyncStatus('err','Sync: '+e.message);
  } finally{ syncing=false; }
}

function renderStats(){
  document.getElementById('st0').textContent = convs.length;
  document.getElementById('st1').textContent = convs.filter(c=>c.estado==='confirma').length;
  document.getElementById('st2').textContent = convs.filter(c=>c.estado==='pendiente').length;
  document.getElementById('st3').textContent = convs.filter(c=>c.estado==='no asiste'||c.estado==='stop').length;
}

function renderLista(){
  const q = (document.getElementById('search')||{value:''}).value.toLowerCase();
  const lista = convs.filter(c=>{
    const mq = !q || c.nombre.toLowerCase().includes(q) || c.tel.includes(q);
    const mt = filtro==='todos' ||(filtro==='externo'&&c.ext) ||(!c.ext&&c.estado===filtro);
    return mq && mt;
  }).sort((a,b)=>(b.unread-a.unread)||((b.msgs[b.msgs.length-1]?.h||'')>(a.msgs[a.msgs.length-1]?.h||'')?1:-1));

  const el = document.getElementById('list');
  if(!el) return;
  if(!lista.length){ el.innerHTML='<div style="padding:18px;text-align:center;font-size:12px;color:#888780">Sin resultados</div>'; return; }

  el.innerHTML = lista.map(c=>{
    const last = c.msgs[c.msgs.length-1];
    const prev = last ? last.texto.slice(0,44)+(last.texto.length>44?'…':'') : '—';
    const bc   = badgeClass(c.estado, c.ext);
    const elbl = c.ext ? 'externo' : c.estado;
    return '<div class="item' + (curTel===c.tel?' on':'') + '" onclick="selConv(\\'' + c.tel + '\\')">' +
      '<div class="item-top"><span class="item-name">' + esc(c.nombre.split(' ').slice(0,3).join(' ')) + '</span><span class="item-time">' + esc(last?.h||'') + '</span></div>' +
      '<div class="item-prev">' + esc(prev) + '</div>' +
      '<div class="item-bot"><span class="badge ' + bc + '">' + esc(elbl) + '</span><div style="display:flex;align-items:center;gap:4px"><span style="font-size:10px;color:#b4b2a9">+' + esc(c.tel) + '</span>' + (c.unread?'<div class="dot-unread"></div>':'') + '</div></div>' +
    '</div>';
  }).join('');
}

function setTab(el){
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('on'));
  el.classList.add('on');
  filtro = el.dataset.tab;
  renderLista();
}

function selConv(tel){ 
    curTel = tel; 
    const c = convs.find(x=>x.tel===tel); 
    if(c) c.unread=false; 
    document.title = "CPSL — Panel"; 
    renderLista(); 
    renderChat(); 
}

function renderChat(){
  const c = convs.find(x=>x.tel===curTel);
  if(!c) return;
  const av = c.ext?'av-ext':'av-imo';
  const bc = badgeClass(c.estado, c.ext);
  const el = c.ext?'externo / no es IMO de campaña':c.estado;

  document.getElementById('chat').innerHTML = 
    '<div class="ch-header">' +
      '<div class="ch-left">' +
        '<div class="avatar ' + av + '">' + esc(ini(c.nombre)) + '</div>' +
        '<div><div class="ch-name">' + esc(c.nombre) + '</div><div class="ch-sub">+' + esc(c.tel) + ' &nbsp;·&nbsp; <span class="badge ' + bc + '">' + esc(el) + '</span></div></div>' +
      '</div>' +
      '<div class="ch-actions">' +
        '<button class="btn-s" onclick="setEstado(\\'confirma\\')">✓ Confirma</button>' +
        '<button class="btn-s" onclick="setEstado(\\'pendiente\\')">⏳ Pendiente</button>' +
        '<button class="btn-s" onclick="setEstado(\\'no asiste\\')">✗ No asiste</button>' +
        '<button class="btn-s" onclick="setEstado(\\'cambio\\')">↔ Cambio</button>' +
        '<button class="btn-s" onclick="setEstado(\\'stop\\')">— Stop</button>' +
      '</div>' +
    '</div>' +
    '<div class="messages" id="msgs"></div>' +
    '<div class="footer">' +
      (c.px.length?'<div class="px-row"><span class="px-lbl">Px:</span>'+c.px.map(p=>'<button class="px-chip" onclick="togglePx(this,\\''+p+'\\')">'+esc(p)+'</button>').join('')+'</div>':'') +
      '<div class="qr-row">' + QR.map((r,i)=>'<button class="qr" onclick="usarQR('+i+')">'+esc(r.l)+'</button>').join('') + '</div>' +
      '<div class="input-row">' +
        '<textarea class="tinput" id="tinput" placeholder="Escribe tu respuesta… (Enter = enviar | Shift+Enter = nueva línea)" onkeydown="handleKey(event)" oninput="onInput(this)"></textarea>' +
        '<button class="send" style="background:#534AB7; padding:8px;" onclick="enviarMedia()" title="Enviar Imagen (En desarrollo)">📎</button>' +
        '<button class="send" id="sbtn" onclick="enviar()">Enviar</button>' +
      '</div>' +
      '<div class="foot-meta"><span id="fchars">0 caracteres</span><span id="fstatus"></span></div>' +
    '</div>';

  poblarMensajes(c); scrollFin();
  const ti = document.getElementById('tinput'); if(ti) ti.focus();
}

function enviarMedia() {
    alert("🚀 Opción 'Enviar Imagen' habilitada. (Integración de Media de la API de Meta en proceso para la siguiente versión).");
}

function actualizarMensajes(){
  const c = convs.find(x=>x.tel===curTel);
  if(!c) return;
  const el = document.getElementById('msgs');
  if(!el) return;
  poblarMensajes(c);
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
  if(atBottom) scrollFin();
}

function poblarMensajes(c){
  const el = document.getElementById('msgs');
  if(!el) return;
  if(!c.msgs.length){ el.innerHTML='<div style="text-align:center;font-size:12px;color:#b4b2a9;padding:20px">Sin mensajes registrados</div>'; return; }
  el.innerHTML = c.msgs.map(m=>{
    const quien = m.dir==='in' ? esc(c.nombre.split(' ').slice(0,2).join(' ')) : 'Tu';
    const st = m.dir==='out' ? '<div class="msg-st">' + esc(m.st||'Enviado') + '</div>' : '';
    return '<div class="msg ' + (m.dir==='in'?'in':'out') + (m.pending?' pending':'') + '"><div class="msg-who">' + quien + ' · ' + esc(m.h) + '</div><div class="bubble">' + nl2br(m.texto) + '</div>' + st + '</div>';
  }).join('');
}

function scrollFin(){ setTimeout(()=>{ const e=document.getElementById('msgs'); if(e) e.scrollTop=e.scrollHeight; },50); }

function onInput(el){
  el.style.height='auto'; el.style.height=Math.min(el.scrollHeight,110)+'px';
  const fc=document.getElementById('fchars'); if(fc) fc.textContent=el.value.length+' caracteres';
}
function handleKey(e){ if(e.key==='Enter'&&!e.shiftKey){ e.preventDefault(); enviar(); } }

async function enviar(){
  const ti = document.getElementById('tinput');
  const sb = document.getElementById('sbtn');
  const texto = ti ? ti.value.trim() : '';
  if(!texto||!curTel) return;

  sb.disabled = true;
  const h = hora();
  const c = convs.find(x=>x.tel===curTel);
  if(!c){ sb.disabled=false; return; }

  const mObj = {dir:'out', texto, h, st:'Enviando…', pending:true, tipo:'man', row: 999999};
  c.msgs.push(mObj);

  ti.value=''; ti.style.height='auto';
  const fc=document.getElementById('fchars'); if(fc) fc.textContent='0 caracteres';

  actualizarMensajes(); scrollFin(); setFootStatus('Enviando…');

  let waOk = false;
  if(CFG.watok&&CFG.wapid){
    const res = await enviarWA(curTel, texto);
    waOk = res.ok;
    setFootStatus(waOk ? 'Enviado por WhatsApp' : '⚠ WA: '+res.err+' — guardando en Sheet');
  } else { setFootStatus('Sin token WA — guardando en Sheet para reenvío del bot'); }

  if(!DEMO){
    const ok = await appendFila([fecha(), curTel, c.nombre, '', '', 'RESPUESTA MANUAL', texto, waOk ? 'ENVIADO' : 'ERROR WA']);
    if(ok){ 
        setFootStatus('✓ Registrado en Sheets'); 
        setTimeout(()=>{ sincronizarSheets(); }, 1000); 
    } else {
        setFootStatus('⚠ Error guardando en Sheet');
    }
  } else { setFootStatus('Modo demo — no se guarda en Sheet'); }

  mObj.pending = false;
  mObj.st = waOk ? 'Enviado' : (DEMO ? 'Demo' : 'En cola');
  actualizarMensajes(); renderLista(); sb.disabled = false;
}

async function setEstado(estado){
  const c = convs.find(x=>x.tel===curTel);
  if(!c) return;
  c.estado = estado;
  if(!DEMO){ const rn = rowMap[curTel]; if(rn) await escribirCelda(rn, 6, estado); }
  renderChat(); renderLista(); renderStats();
}

function usarQR(idx){ const ti = document.getElementById('tinput'); if(!ti) return; ti.value = QR[idx].t; onInput(ti); ti.focus(); }

function togglePx(btn, px){ 
    btn.classList.toggle('on'); 
    const ti = document.getElementById('tinput'); 
    if(!ti) return; 
    if(btn.classList.contains('on')){ 
        ti.value += (ti.value&&!ti.value.endsWith(String.fromCharCode(10))?' ':'')+px; 
        onInput(ti); 
        ti.focus(); 
    } 
}

function iniciarSimulador() {
    let num = prompt("Ingresa el número a simular:\\nEj: 51999888777");
    if (!num) return;
    num = num.split('').filter(c => c >= '0' && c <= '9').join('');
    let simTel = "SIM_" + num;
    curTel = simTel;
    
    fetch('/api/mensaje_simulador', { 
        method: 'POST', headers: {'Content-Type': 'application/json'}, 
        body: JSON.stringify({telefono: simTel, texto: "MENU"}) 
    }).then(() => {
        setTimeout(sincronizarSheets, 1500);
    });
}

function abrirNuevo(){ document.getElementById('ovl-new').style.display='flex'; }
function cerrarNuevo(){ document.getElementById('ovl-new').style.display='none'; }
async function crearNuevo(){
  const nombre = document.getElementById('n-nombre').value.trim();
  const rawTel = document.getElementById('n-tel').value.trim();
  const tel = rawTel.split('').filter(c => c >= '0' && c <= '9').join('');
  if(!nombre||!tel){ alert('Nombre y teléfono son obligatorios.'); return; }
  const existe = convs.find(c=>c.tel===tel);
  if(existe){ cerrarNuevo(); selConv(tel); return; }
  const c = {tel, nombre, estado:'pendiente', ext:true, unread:false, rowNum:null, px:[], msgs:[]};
  convs.push(c);
  if(!DEMO){ const ok = await appendFila([fecha(),tel,nombre,'','','pendiente','','']); if(ok) setTimeout(sincronizarSheets, 800); }
  document.getElementById('n-nombre').value=''; document.getElementById('n-tel').value='';
  cerrarNuevo(); renderStats(); renderLista(); selConv(tel);
}

function iniciarUI(){ renderStats(); renderLista(); }
async function iniciar(){ 
    setSyncStatus('busy','Conectando a Sheets…'); 
    await sincronizarSheets(); 
    iniciarUI(); 
    
    setInterval(sincronizarMensajesInstantaneos, 2500); 
    if(syncTimer) clearInterval(syncTimer); 
    syncTimer = setInterval(sincronizarSheets, 8000); 
}

cargarCfg();
const savedCreds = sessionStorage.getItem('cpsl_creds');
const savedCfg   = localStorage.getItem(CFG_KEY);
if(savedCreds && savedCfg){
  try{
    const sc = JSON.parse(savedCfg);
    CFG = {...sc, creds: savedCreds};
    document.getElementById('ovl-cfg').style.display='none';
    document.getElementById('app').style.display='grid';
    iniciar();
  } catch(e){ }
}
</script>
</body>
</html>"""

@app.route("/chat", methods=["GET"])
def panel_chat(): return HTML_CHAT

@app.route("/api/historial", methods=["GET"])
def api_historial(): return jsonify(get_historial()), 200

@app.route("/api/descargar_respaldo", methods=["GET"])
def descargar_respaldo():
    if os.path.exists(Config.BACKUP_ABSOLUTO_CSV):
        with open(Config.BACKUP_ABSOLUTO_CSV, "r", encoding="utf-8-sig") as f: data = f.read()
    else: data = "Fecha y Hora,Telefono,Nombre,Direccion (In/Out),Mensaje,Estado Sistema\nSin datos aun"
    return Response(data, mimetype="text/csv", headers={"Content-Disposition":f"attachment;filename=Backup_Absoluto_V77.csv"})

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    data = request.json; tel = data.get("telefono"); msg = data.get("mensaje")
    if tel and msg:
        sesion = get_sesion(tel)
        perfil = sesion.get("perfil")
        if not perfil: perfil = obtener_perfil_crm(tel)
        nombre_mostrar = f"({perfil['rol']}) {perfil['nombre']}" if perfil['nombre'] else "NUEVO CONTACTO"
        WhatsAppAPI.enviar_mensaje(tel, msg, nombre_mostrar, registrar_sheets=True, estado_menu="MANUAL_PANEL")
        return jsonify({"status": "ok"}), 200
    return jsonify({"error": "Faltan datos"}), 400

@app.route("/api/mensaje_simulador", methods=["POST"])
def mensaje_simulador():
    data = request.json; tel = data.get("telefono"); texto = data.get("texto")
    if not tel or not texto: return jsonify({"error": "Faltan datos"}), 400
    sesion = get_sesion(tel)
    perfil = sesion.get("perfil", {})
    nombre_mostrar = f"({perfil.get('rol', 'PROSPECTO')}) {perfil.get('nombre', 'Simulado')}" if perfil.get('nombre') else "SIMULACIÓN"
    
    append_historial(tel, nombre_mostrar, texto, "in")
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
        
        if tipo == "text":
            texto = str(msg["text"]["body"]).replace("=", "").replace("+", "").replace("@", "")
            sesion = get_sesion(telefono)
            perfil = sesion.get("perfil")
            if not perfil: perfil = obtener_perfil_crm(telefono)
            nombre_cached = f"({perfil['rol']}) {perfil['nombre']}" if perfil.get('nombre') else "NUEVO CONTACTO"
            
            append_historial(telefono, nombre_cached, texto, "in")
            registrar_en_sheets_inmediato(telefono, nombre_cached, texto, "", "RECIBIDO", "", "")
            SessionManager.guardar_backup_absoluto(telefono, nombre_cached, texto, "IN", "RECIBIDO")

            threading.Thread(target=flujo_principal, args=(telefono, texto), daemon=True).start()
            
        elif tipo in ("audio","image","document","video","sticker"):
            sesion = get_sesion(telefono)
            perfil = sesion.get("perfil")
            if not perfil: perfil = obtener_perfil_crm(telefono)
            nombre_cached = f"({perfil['rol']}) {perfil['nombre']}" if perfil.get('nombre') else "NUEVO CONTACTO"
            
            append_historial(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "in")
            registrar_en_sheets_inmediato(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "", "RECIBIDO", "", "")
            SessionManager.guardar_backup_absoluto(telefono, nombre_cached, "[MULTIMEDIA RECIBIDO]", "IN", "ERROR_MULTIMEDIA")
            
            WhatsAppAPI.enviar_mensaje(telefono, "Comprendido. Por favor responde con texto o el número de la opción deseada para poder apoyarte.", registrar_sheets=True, estado_menu="ERROR_MULTIMEDIA")
            
    except Exception as e: logger.error(f"Error Webhook: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
