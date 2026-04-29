import os, re, json, time, csv, base64, random, logging, threading, queue
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from dotenv import load_dotenv
from ia_chain import ia_detect_intent_cc, bucar_caso_por_nombre
from ia_multimodelo import ia_clasificar, ia_respuesta_px, ia_respuesta_imo, ia_respuesta_nuevo, guardar_feedback, estado_ias
from filelock import FileLock, Timeout as FileLockTimeout
from crm_bridge import push_report_crm, push_gestion_individual, push_report_jose, kpi_consolidado_whatsapp

# Cargar variables de entorno desde .env
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CPSL")

# Configurar logging a archivo para debug remoto
log_path = os.path.join("/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__)), "bot.log")
fh = logging.FileHandler(log_path)
fh.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(fh)
logger.setLevel(logging.INFO)
logger.info("Bot iniciado - Logger configurado")

app = Flask(__name__)

# =============================================
# ZONA HORARIA
# =============================================
TZ_LIMA = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

# =============================================
# CALENDARIO DE ENTRENAMIENTOS LIMA
# =============================================
def en_entrenamiento():
    """Verifica si estamos en fechas de entrenamiento según el json del calendario."""
    try:
        tz = timezone(timedelta(hours=-5))
        hoy = datetime.now(tz).strftime("%Y-%m-%d")
        cal_path = "/data/calendario_entrenamientos.json" if os.path.exists("/data") else "calendario_entrenamientos.json"
        if os.path.exists(cal_path):
            with open(cal_path, "r", encoding="utf-8") as f:
                eventos = json.load(f)
                for ev in eventos:
                    if ev["inicio"] <= hoy <= ev["fin"]:
                        return ev["nombre"]
    except Exception as e:
        pass
    return None

def ahora():
    return datetime.now(TZ_LIMA)

# =============================================
# STAFF COORDINADORAS
# =============================================
STAFF = {
    "dmoscoso": {"nombre": "Diana Moscoso", "tel": "51912379744"},
    "jmarin": {"nombre": "Joyce Marín", "tel": "51933599903"},
    "lpasquel": {"nombre": "Leyla Pasquel", "tel": "51919502385"},
    "zurteaga": {"nombre": "Zuley Urteaga", "tel": "51933599864"},
    "lvalencia": {"nombre": "Linid Valencia", "tel": "51912379686"},
}
_carga = {k: 0 for k in STAFF}
_carga_lk = threading.Lock()

def cc_libre():
    with _carga_lk:
        return min(_carga, key=_carga.get)

def cc_add(k):
    with _carga_lk:
        if k in _carga:
            _carga[k] += 1

_CC_POR_EQUIPO = {
    "EQUIPO 26": "dmoscoso",
    "EQUIPO 25": "jmarin",
    "EQUIPO 24": "zurteaga",
    "EQUIPO 23": "zurteaga",
    "EQUIPO 22": "jmarin",
    "EQUIPO 21": "jmarin",
    "EQUIPO 20": "jmarin",
    "EQUIPO 19": "dmoscoso",
    "EQUIPO 18": "dmoscoso",
    "EQUIPO 17": "dmoscoso",
    "EQUIPO 16": "dmoscoso",
    "EQUIPO 15": "dmoscoso",
    "EQUIPO 14": "dmoscoso",
}

def cc_por_equipo(equipo):
    return _CC_POR_EQUIPO.get(str(equipo).strip().upper(), cc_libre())

# =============================================
# CONFIGURACIÓN
# =============================================
class Cfg:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VER_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    SHEET_ID = os.environ.get("SHEET_ID", "")
    CREDS = os.environ.get("GOOGLE_CREDENTIALS", "")
    SHEET_TAB = os.environ.get("SHEET_TAB", "Hoja 1")
    LOCK_T = 5
    CSV = os.path.join(BASE_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")
    S_REAL = os.path.join(DATA_DIR, "sesiones.json")
    S_SIM = os.path.join(DATA_DIR, "sesiones_sim.json")
    HIST = os.path.join(DATA_DIR, "historial_chat.json")
    HIST_ALT = os.path.join(DATA_DIR, "historial.json")
    FECHA = "Viernes 1, Sábado 2 y Domingo 3 de mayo de 2026"
    LUGAR = "Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores"
    REGISTRO = "Viernes 1 de mayo a las 9:00am (obligatorio)"

FECHAS_MSG = (
    "*Próximas Fechas — Sede Lima 2026*\n\n"
    f"*C1 Equipo 27:* {Cfg.FECHA}\n"
    f"*{Cfg.LUGAR}*\n\n"
    "*C2 Equipo 27:* Jueves 14 de mayo\n"
    "*MJ Inducción:* Viernes 17 de abril"
)

# =============================================
# CACHÉ CSV
# =============================================
_csv_cache = None
_csv_mtime = 0.0
_csv_lk = threading.Lock()

def _get_rows():
    global _csv_cache, _csv_mtime
    if not os.path.exists(Cfg.CSV):
        logger.warning(f"CSV no encontrado: {Cfg.CSV}")
        return []
    try:
        mt = os.path.getmtime(Cfg.CSV)
        with _csv_lk:
            if _csv_cache is not None and mt == _csv_mtime:
                return _csv_cache
        with open(Cfg.CSV, encoding="utf-8-sig") as f:
            first = f.readline()
            delim = ";" if first.count(";") > first.count(",") else ","
            f.seek(0)
            rows = list(csv.DictReader(f, delimiter=delim))
            with _csv_lk:
                _csv_cache, _csv_mtime = rows, mt
            logger.info(f"CSV cargado: {len(rows)} filas")
            return rows
    except Exception as e:
        logger.error(f"CSV error: {e}")
        return []

# =============================================
# GRADUADOS
# =============================================
_GRADUADOS_IDX = {}

def _cargar_graduados():
    global _GRADUADOS_IDX
    try:
        import openpyxl as _opx
        _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "GRADUADOS_LIMA.xlsx")
        if not os.path.exists(_p):
            return
        _wb = _opx.load_workbook(_p, data_only=True, read_only=True)
        if "GRADUADOS" in _wb.sheetnames:
            for _r in _wb["GRADUADOS"].iter_rows(min_row=2, values_only=True):
                if _r[0]:
                    _n = re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", str(_r[0]).upper())).strip()
                    _GRADUADOS_IDX[_n] = {"graduado": True, "rango": "GRADUADO", "equipo": str(_r[1] or "")}
        if "ALIADOS C1E27" in _wb.sheetnames:
            for _r in _wb["ALIADOS C1E27"].iter_rows(min_row=3, values_only=True):
                if _r[0] and str(_r[0]).strip() not in ("CREADOR CUANTICO", ""):
                    _n = re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", str(_r[0]).upper())).strip()
                    if _n not in _GRADUADOS_IDX:
                        _GRADUADOS_IDX[_n] = {"graduado": True, "rango": "GRADUADO_E27"}
        _wb.close()
        logger.info(f"Graduados cargados: {len(_GRADUADOS_IDX)}")
    except Exception as _e:
        logger.warning(f"graduados: {_e}")

_cargar_graduados()

# =============================================
# NORMALIZACIÓN
# =============================================
def _d(s):
    return re.sub(r'\D', '', str(s or ""))

def n9(t):
    return _d(t)[-9:]

def formatear_nombre_empatia(texto, solo_nombre=False):
    if not texto:
        return ""
    texto = str(texto).strip()
    if ";" in texto:
        partes = [p.strip() for p in texto.split(";")]
        if len(partes) >= 2:
            nom, ape = partes[1], partes[0]
            if solo_nombre:
                return nom.split()[0].title()
            return f"{nom.title()} {ape.title()}"
    tokens = [t for t in texto.split() if len(t) > 1]
    if not tokens:
        return texto.title()
    if len(tokens) >= 3:
        nombres = " ".join(tokens[2:])
        apellidos = " ".join(tokens[:2])
        if solo_nombre:
            return tokens[2].title()
        return f"{nombres.title()} {apellidos.title()}"
    if len(tokens) == 2:
        if solo_nombre:
            return tokens[1].title()
        return f"{tokens[1].title()} {tokens[0].title()}"
    return tokens[0].title()

def np(s):
    return formatear_nombre_empatia(s, solo_nombre=True)

# =============================================
# PERFIL CRM
# =============================================
def perfil_crm(tel):
    t9 = n9(tel)
    rows = _get_rows()
    p = {
        "tipo": "NUEVO",
        "nombre": None,
        "apellido": "",
        "nombre_full": "",
        "equipo": "",
        "imo_nombre": "",
        "imo_tel": "",
        "staff_key": None,
        "staff_tel": None,
        "staff_nom": None,
        "pendientes": [],
    }
    px_row = None
    imo_rows = []
    for r in rows:
        if n9(r.get("Teléfono", "")) == t9:
            px_row = r
        if n9(r.get("Tel. IMO", "")) == t9 and n9(r.get("Tel. IMO", "")):
            imo_rows.append(r)
    if imo_rows:
        p["tipo"] = "IMO"
        p["nombre"] = np(imo_rows[0].get("IMO", ""))
        p["imo_nombre"] = formatear_nombre_empatia(imo_rows[0].get("IMO", ""))
        p["pendientes"] = [
            f"{formatear_nombre_empatia(f\"{r.get('Apellido','')} {r.get('Nombre','')}\")} ({r.get('Equipo','')})"
            for r in imo_rows
        ]
    elif px_row:
        p["tipo"] = "PX"
        p["nombre"] = np(px_row.get("Nombre", ""))
        p["apellido"] = px_row.get("Apellido", "").strip().title()
        p["nombre_full"] = f"{p['nombre']} {p['apellido']}".strip()
        p["equipo"] = px_row.get("Equipo", "")
        p["imo_nombre"] = px_row.get("IMO", "").strip()
        p["imo_tel"] = _d(px_row.get("Tel. IMO", ""))
    if p["tipo"] == "PX":
        k = cc_por_equipo(p.get("equipo", ""))
    elif p["tipo"] == "IMO":
        equipos = [r.get("Equipo", "") for r in imo_rows] if imo_rows else []
        import re as _re2
        nums = [int(m.group()) for eq in equipos for m in [_re2.search(r"\d+", eq)] if m]
        eq_top = f"EQUIPO {max(nums)}" if nums else ""
        k = cc_por_equipo(eq_top)
    else:
        k = cc_libre()
    p["staff_key"] = k
    p["staff_tel"] = STAFF[k]["tel"]
    p["staff_nom"] = STAFF[k]["nombre"]
    cc_add(k)
    nom_norm = re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", f"{p.get('nombre','')} {p.get('apellido','')}".upper())).strip()
    grad_info = _GRADUADOS_IDX.get(nom_norm, {})
    if not grad_info:
        partes = nom_norm.split()
        if len(partes) >= 2:
            clave = " ".join(partes[:-2])
            grad_info = next((v for n, v in _GRADUADOS_IDX.items() if n.startswith(clave)), {})
    p["graduado"] = grad_info.get("graduado", False)
    p["rango"] = grad_info.get("rango", "")
    return p

# =============================================
# SESIONES
# =============================================
def _sp(tel):
    return Cfg.S_SIM if str(tel).startswith("SIM_") else Cfg.S_REAL

def get_s(tel):
    path = _sp(tel)
    try:
        with FileLock(path + ".lock", timeout=Cfg.LOCK_T):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f).get(str(tel), {})
    except FileLockTimeout:
        logger.warning(f"lock get {tel}")
    except Exception as e:
        logger.error(f"get_s {e}")
    return {}

def set_s(tel, data):
    path = _sp(tel)
    try:
        with FileLock(path + ".lock", timeout=Cfg.LOCK_T):
            d = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
            d[str(tel)] = data
            with open(path, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
    except FileLockTimeout:
        logger.warning(f"lock set {tel}")
    except Exception as e:
        logger.error(f"set_s {e}")

def del_s(tel):
    path = _sp(tel)
    try:
        with FileLock(path + ".lock", timeout=Cfg.LOCK_T):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    d = json.load(f)
                d.pop(str(tel), None)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def add_hist(tel, nom, txt, tipo):
    path = Cfg.HIST
    try:
        with FileLock(path + ".lock", timeout=Cfg.LOCK_T):
            h = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    h = json.load(f)
            h.append({"telefono": str(tel), "nombre": nom or "?", "texto": txt,
                      "tipo": tipo, "hora": ahora().strftime("%d/%m %H:%M")})
            if len(h) > 5000:
                h = h[-5000:]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"hist {e}")

# =============================================
# NOTIFICACIÓN CC
# =============================================
def notif_cc(p, motivo, extra=""):
    tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]
    nom_cc = p.get("staff_nom") or "Coordinación"
    nom_full = p.get("nombre_full") or ""
    nom_pila = p.get("nombre") or ""
    nom_px = nom_full if nom_full and len(nom_full.split()) > 1 else nom_pila or "Sin nombre"
    tel_px = p.get("_tel", "")
    tipo = p.get("tipo", "")
    equipo = p.get("equipo", "")
    pend_n = len(p.get("pendientes", []))
    if tipo == "IMO":
        ctx = f"IMO | {pend_n} enrolados pendientes C1*"
        if equipo:
            ctx += f" | {equipo}"
    elif tipo == "PX":
        ctx = f"Creador C1 E27 ({equipo})*"
        imo_n = p.get("imo_nombre", "")
        if imo_n:
            ctx += f"\n*Su IMO:* {imo_n}"
    else:
        ctx = "*Nuevo contacto*"
    logger.info(f"notif_cc INICIO → {nom_cc} tel={tel_cc} | px={nom_px} {motivo[:40]}")
    if not tel_cc:
        logger.critical("notif_cc: tel_cc VACÍO — revisar STAFF y cc_por_equipo")
        return nom_cc
    if not Cfg.TOKEN:
        logger.critical("notif_cc: WA_TOKEN VACÍO — derivación no enviada")
        return nom_cc
    exito = wa(tel_cc,
        f"*CASO DERIVADO — CPSL Lima*\n"
        f"_{ahora().strftime('%d/%m/%Y %H:%M')}_ \n\n"
        f"*Nombre:* {nom_px}\n"
        f"*WhatsApp:* wa.me/{tel_px}\n"
        f"*{ctx}*\n\n"
        f"*Asunto:* {motivo}"
        + (f"\n*Detalle:* {extra}" if extra else "")
        + f"\n\n¿Atendiste este caso?\n"
        + f"1 Sí, resuelto\n2 En gestión\n3 Necesito apoyo",
        f"SIS>{nom_cc}"
    )
    if not exito:
        logger.error(f"notif_cc: wa() falló enviando a {tel_cc}")
    else:
        try:
            s_cc = get_s(tel_cc) or {}
            s_cc["caso_followup"] = str(tel_px)
            s_cc["modo"] = "CC"
            s_cc["st_cc"] = "MAIN"
            set_s(tel_cc, s_cc)
        except:
            pass
    return nom_cc

# =============================================
# ENVÍO WHATSAPP
# =============================================
def wa(tel, txt, log="BOT"):
    if str(tel).startswith("SIM_"):
        add_hist(tel, log, txt, "out")
        return True
    if not Cfg.TOKEN:
        logger.critical("wa(): WA_TOKEN vacio — renovar en Render")
        return False
    try:
        url = f"https://graph.facebook.com/v19.0/{Cfg.PHONE_ID}/messages"
        headers = {
            "Authorization": f"Bearer {Cfg.TOKEN}",
            "Content-Type": "application/json"
        }
        data = {
            "messaging_product": "whatsapp",
            "to": tel,
            "type": "text",
            "text": {"body": txt}
        }
        r = req_lib.post(url, headers=headers, json=data, timeout=10)
        if r.status_code == 200:
            add_hist(tel, log, txt, "out")
            return True
        else:
            logger.error(f"wa error {tel}: {r.status_code} {r.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"wa exception {tel}: {e}")
        return False

# =============================================
# REGISTRO GOOGLE SHEETS
# =============================================
_q = queue.Queue()
_stok = None
_stok_exp = 0
_stok_lk = threading.Lock()

def _sheets_tok():
    global _stok, _stok_exp
    with _stok_lk:
        if _stok and time.time() < _stok_exp - 60:
            return _stok
        if not Cfg.CREDS:
            return None
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now = int(time.time())
            creds = json.loads(Cfg.CREDS)
            pem = creds["private_key"].replace("\\n", "\n")
            hdr = base64.urlsafe_b64encode(json.dumps({"alg": "RS256", "typ": "JWT"}).encode()).rstrip(b"=")
            pld = base64.urlsafe_b64encode(json.dumps({
                "iss": creds["client_email"],
                "scope": "https://www.googleapis.com/auth/spreadsheets",
                "aud": "https://oauth2.googleapis.com/token",
                "iat": now,
                "exp": now + 3600
            }).encode()).rstrip(b"=")
            msg_b = hdr + b"." + pld
            pk = serialization.load_pem_private_key(pem.encode(), password=None)
            sig = pk.sign(msg_b, cp.PKCS1v15(), hashes.SHA256())
            jwt = (msg_b + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token",
                             data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt},
                             timeout=10)
            if r.status_code == 200:
                d = r.json()
                _stok = d["access_token"]
                _stok_exp = now + d.get("expires_in", 3600)
                return _stok
            logger.error(f"sheets tok {r.status_code}")
        except Exception as e:
            logger.error(f"sheets tok err {e}")
        return None

def _wsheets():
    while True:
        try:
            t = _q.get()
            if Cfg.SHEET_ID:
                tok = _sheets_tok()
                if tok:
                    tab = Cfg.SHEET_TAB.replace(" ", "%20")
                    req_lib.post(
                        f"https://sheets.googleapis.com/v4/spreadsheets/{Cfg.SHEET_ID}/values/{tab}!A:K:append",
                        params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
                        json={"values": [[
                            ahora().strftime("%d/%m/%Y %H:%M:%S"),
                            t.get("dir", ""), str(t.get("tel", "")),
                            t.get("nom", ""), t.get("tipo", ""),
                            t.get("staff", ""), t.get("msg", "")[:500],
                            t.get("evento", ""), t.get("estado", ""),
                        ]]},
                        headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
                        timeout=10
                    )
                    time.sleep(0.8)
        except Exception as e:
            logger.error(f"wsheets {e}")
        finally:
            _q.task_done()

threading.Thread(target=_wsheets, daemon=False, name="wsheets").start()

def reg(tel, nom, tipo, msg, evento, estado="", dir_="IN", staff=""):
    if str(tel).startswith("SIM_"):
        return
    if not Cfg.SHEET_ID:
        return
    _q.put({"tel": tel, "nom": nom, "tipo": tipo, "msg": msg,
            "evento": evento, "estado": estado, "dir": dir_, "staff": staff})

# =============================================
# PLANTILLAS Y PATRONES
# =============================================
STOP_W = {"STOP", "BAJA", "DETENER", "NO MAS"}
RESET_W = {"HOLA", "MENU", "MENÚ", "0", "INICIO", "START", "HI"}

_NEG_PATTERNS = [
    "NO QUIERO", "NO DESEO", "NO PUEDO", "NO ME INTERESA", "DEVUELVAN",
    "NO VOY", "NO ASIST", "IMPOSIBLE", "NO ESTOY INTERESADO", "OCUPADO",
    "DE VIAJE", "POR SALUD", "DELICAD", "NO ESTÁ EN MIS PLANES",
    "OTRA ACTIVIDAD", "TENGO OTRO", "FERIADO", "TRABAJO ESE",
]

_AUTORESPONDER = [
    "GRACIAS POR COMUNICARTE CON", "FUERA DEL HORARIO",
    "TE RESPONDEREMOS TAN PRONTO", "HORARIO DISPONIBLE",
    "MENSAJE AUTOMÁTICO", "NUESTRO HORARIO"
]

def _es_autoresponder(txt):
    return any(p in txt for p in _AUTORESPONDER)

def _detectar_negativa(txt):
    return any(p in txt for p in _NEG_PATTERNS)

def _limpiar_input(txt):
    limpio = re.sub(r'[^\w\s]', '', txt).strip()
    if limpio in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
        return limpio
    return txt

# =============================================
# FLUJOS COORDINADORAS (VERSIÓN SIMPLIFICADA)
# =============================================
_CC_TELS = {
    "51912379744": {"key": "dmoscoso", "nombre": "Diana", "nombre_full": "Diana Moscoso"},
    "51933599903": {"key": "jmarin", "nombre": "Joyce", "nombre_full": "Joyce Marín"},
    "51933599864": {"key": "zurteaga", "nombre": "Zuley", "nombre_full": "Zuley Urteaga"},
    "51919502385": {"key": "lpasquel", "nombre": "Leyla", "nombre_full": "Leyla Pasquel"},
    "51912379686": {"key": "lvalencia", "nombre": "Linid", "nombre_full": "Linid Valencia"},
}

def _menu_cc(tel_cc, nom):
    wa(tel_cc,
        f"*TORRE DE CONTROL — CPSL Lima*\n"
        f"Hola {nom}!\n\n"
        f"1 Reporte de llamadas del día\n"
        f"2 Registrar confirmación de PX\n"
        f"3 Reportar devolución\n"
        f"4 Ver mis casos derivados\n"
        f"0 Salir\n\n"
        f"*Tip:* Puedes simplemente escribirme qué hiciste.\n"
        f"_Ej: 'Resolví el caso de Bertha' o 'Le escribí a Juan'_",
        f"SIS>{nom}")

def _flujo_cc(tel, up, texto, cc_info):
    nom = cc_info["nombre"]
    nom_full = cc_info["nombre_full"]
    cc_key = cc_info["key"]
    s = get_s(tel) or {}
    st = s.get("st_cc", "MAIN")
    if up in RESET_W:
        s = {"modo": "CC", "cc_key": cc_key, "st_cc": "MAIN"}
        set_s(tel, s)
        _menu_cc(tel, nom)
        return
    if st == "MAIN":
        if up == "1":
            s["st_cc"] = "ESPERANDO_REPORTE"
            set_s(tel, s)
            wa(tel, f"Escribe tu reporte en formato libre.\n\n_Escribe 0 para cancelar_", f"SIS>{nom}")
        elif up == "2":
            s["st_cc"] = "ESPERANDO_CONFIRMACION"
            set_s(tel, s)
            wa(tel, f"Escribe el nombre del PX que confirmó asistencia.\n\n_Escribe 0 para cancelar_", f"SIS>{nom}")
        elif up == "3":
            s["st_cc"] = "ESPERANDO_DEVOLUCION"
            set_s(tel, s)
            wa(tel, f"Escribe los datos de devolución.\n\n_Escribe 0 para cancelar_", f"SIS>{nom}")
        elif up == "4":
            wa(tel, f"Consulta tus casos en el panel web.\n\n0 Menú", f"SIS>{nom}")
        elif up == "0":
            del_s(tel)
            wa(tel, "Hasta pronto. Escribe HOLA para volver.", "SIS")
        else:
            _menu_cc(tel, nom)
    elif st in ("ESPERANDO_REPORTE", "ESPERANDO_CONFIRMACION", "ESPERANDO_DEVOLUCION"):
        if up == "0":
            s["st_cc"] = "MAIN"
            set_s(tel, s)
            _menu_cc(tel, nom)
        else:
            evento = "REPORTE_CC" if st == "ESPERANDO_REPORTE" else ("CONFIRMA_CC" if st == "ESPERANDO_CONFIRMACION" else "DEVOLUCION_CC")
            reg(tel, nom_full, "", texto, evento, dir_="IN", staff=nom_full)
            add_hist(tel, f"CC/{nom}", texto, "in")
            wa(tel, f"Registrado correctamente.\n\n0 Menú", f"SIS>{nom}")
            s["st_cc"] = "MAIN"
            set_s(tel, s)

# =============================================
# FLUJOS PRINCIPALES
# =============================================
def _menu_main(tel, p):
    tipo = p.get("tipo", "NUEVO")
    nom = p.get("nombre") or "Líder"
    if tipo == "IMO":
        n = len(p.get("pendientes", []))
        al = f"\n⚠️ Tienes {n} enrolado(s) pendiente(s) de C1." if n else "\n⚠️ Todos tus enrolados al día."
        wa(tel,
            f"⚠️ *Hola {nom}* — Portal IMO{al}\n\n"
            f"1 Ver mis pendientes de C1\n"
            f"2 Ver TODOS mis enrolados\n"
            f"3 Solicitar ser Aliado C1 E27\n"
            f"4 Fechas activas\n"
            f"5 Hablar con Coordinación\n"
            f"0 Salir\n\n"
            f"_STOP para darte de baja._", nom)
    elif tipo == "PX":
        nom_cc = p.get("staff_nom", "Coordinación")
        wa(tel,
            f"*Hola {nom}!*\n"
            f"Tu coordinadora: *{nom_cc}*\n\n"
            f"1 Confirmar asistencia al C1 Equipo 27\n"
            f"2 Fechas y logística\n"
            f"3 Inversión y pagos\n"
            f"4 Hablar con mi coordinadora\n"
            f"0 Salir\n\n"
            f"_STOP para darte de baja_", nom)
    else:
        wa(tel,
            f"*Bienvenido a Crear Poder Sin Límites Perú!*\n"
            f"Canal Corporativo Oficial — Sede Lima.\n\n"
            f"1 Ya participé antes (cambié de número)\n"
            f"2 Soy nuevo — quiero información\n"
            f"0 Salir\n\n"
            f"_STOP para darte de baja_", "Sistema")

def _imo(tel, up, texto, s, p):
    nom = p.get("nombre", "Líder")
    pend = p.get("pendientes", [])
    st = s.get("st", "MAIN")
    if st == "MAIN":
        if up == "1":
            if pend:
                lista = "\n".join(pend[:20])
                wa(tel, f"*Pendientes de C1:*\n\n{lista}\n\n0 Volver", nom)
            else:
                wa(tel, "✓ ¡Todos tus enrolados ya se sentaron! Felicitaciones.\n\n0 Volver", nom)
        elif up == "2":
            wa(tel, "Consulta tus enrolados en el panel web.\n\n0 Volver", nom)
        elif up == "3":
            nom_cc = notif_cc(p, "Solicita ser Aliado C1 E27", f"IMO: {p.get('imo_nombre', nom)}")
            wa(tel, f"Solicitud registrada.\n\n0 Volver", nom)
        elif up == "4":
            wa(tel, FECHAS_MSG + "\n\n0 Volver", nom)
        elif up == "5":
            nom_cc = notif_cc(p, "IMO solicita atención directa")
            s["st"] = "DER"
            set_s(tel, s)
            wa(tel, f"Derivado a {nom_cc}. Puedes escribirle directamente aquí.", nom)
        elif up == "0":
            del_s(tel)
            wa(tel, "Hasta pronto. Escribe HOLA para volver.", nom)
        else:
            _menu_main(tel, p)

def _px(tel, up, texto, s, p):
    nom = p.get("nombre", "Líder")
    nom_cc = p.get("staff_nom", "Coordinación")
    st = s.get("st", "MAIN")
    if st == "MAIN":
        if up == "1":
            nom_cc2 = notif_cc(p, "PX CONFIRMA asistencia C1 E27")
            reg(tel, p.get("nombre_full", nom), "PX", "Confirma C1 E27", "CONFIRMA", dir_="SYS", staff=nom_cc2)
            wa(tel,
                f"✓ Confirmado {nom}! ✓\n\n"
                f"*{Cfg.LUGAR}*\n"
                f"{Cfg.FECHA}\n"
                f"{Cfg.REGISTRO}\n\n"
                f"Tu coordinadora {nom_cc2} recibirá tu confirmación.",
                nom)
            del_s(tel)
        elif up == "2":
            wa(tel, FECHAS_MSG + "\n\n0 Volver", nom)
        elif up == "3":
            wa(tel, "*Inversión y Pagos*\n\nBCP — Creación Cuántica E.I.R.L.\nCuenta Soles: *1934218307060*\n\n0 Volver", nom)
        elif up == "4":
            nom_cc2 = notif_cc(p, "PX solicita atención directa")
            s["st"] = "DER"
            set_s(tel, s)
            wa(tel, f"Te derivo con {nom_cc2}. Escribe tu consulta aquí.", nom)
        elif up == "0":
            del_s(tel)
            wa(tel, "Hasta pronto. Escribe HOLA para volver.", nom)
        else:
            _menu_main(tel, p)
    elif st == "DER":
        tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]
        nom_cc = p.get("staff_nom", "Coord")
        wa(tel_cc, f"*Mensaje de {p.get('nombre_full', p.get('nombre', ''))}*\nTel: wa.me/{tel}\n\n{texto}", f"RELAY>{nom_cc}")
        wa(tel, "✓ Mensaje entregado a tu coordinadora.\n_Escribe 0 para volver al menú_", p.get("nombre", ""))
        s["st"] = "MAIN"
        set_s(tel, s)

def _nuevo(tel, up, texto, s, p):
    st = s.get("st", "MAIN")
    if st == "MAIN":
        if up == "1":
            s["st"] = "NVO_NUM"
            set_s(tel, s)
            wa(tel, "Escríbeme tu *Nombre completo y DNI* en un solo mensaje.\n_Ej: Juan Pérez 12345678_\n\n9 Volver", "Sistema")
        elif up == "2":
            s["st"] = "NVO_INFO"
            set_s(tel, s)
            wa(tel, "*Crear Poder Sin Límites Perú*\n\nEntrenamientos de liderazgo de alto rendimiento.\n\n1 Info C1\n2 Fechas 2026\n3 Inversión\n4 Contactar Coordinación\n9 Volver", "Sistema")
        elif up == "0":
            del_s(tel)
            wa(tel, "Hasta pronto. Escribe HOLA cuando quieras.", "Sistema")
        else:
            _menu_main(tel, p)
    elif st == "NVO_NUM":
        if up == "9":
            s["st"] = "MAIN"
            set_s(tel, s)
            _menu_main(tel, p)
        else:
            k = cc_libre()
            cc_add(k)
            tel_cc = STAFF[k]["tel"]
            nom_cc = STAFF[k]["nombre"]
            wa(tel_cc, f"*VERIFICACION DE IDENTIDAD*\nTel: wa.me/{tel}\nDato: '{texto}'\nBuscar en sistema.", "SIS")
            p["staff_key"] = k
            p["staff_tel"] = tel_cc
            p["staff_nom"] = nom_cc
            s["p"] = p
            s["st"] = "DER"
            set_s(tel, s)
            wa(tel, f"Datos enviados a Coordinación ({nom_cc}). Te responderán pronto.", "Sistema")
            reg(tel, texto, "NUEVO", texto, "CAMBIO_NUM", dir_="SYS", staff=nom_cc)
    elif st == "NVO_INFO":
        if up == "1":
            wa(tel, f"*Capítulo 1 — El Descubrimiento*\n\n3 días vivenciales.\n*Próxima fecha:* {Cfg.FECHA}\n\n1 Inscribirme\n9 Volver", "Sistema")
            s["st"] = "NVO_C1"
            set_s(tel, s)
        elif up == "2":
            wa(tel, FECHAS_MSG + "\n\n9 Volver", "Sistema")
        elif up == "3":
            wa(tel, "*Inversión*\n\nEl costo es personalizado. Tu coordinadora te dará detalles.\n\n1 Contactar Coordinación\n9 Volver", "Sistema")
            s["st"] = "NVO_INV"
            set_s(tel, s)
        elif up == "4":
            k = cc_libre()
            cc_add(k)
            tel_cc = STAFF[k]["tel"]
            nom_cc = STAFF[k]["nombre"]
            wa(tel_cc, f"*NUEVO PROSPECTO*\nTel: wa.me/{tel}", "SIS")
            p["staff_key"] = k
            p["staff_tel"] = tel_cc
            p["staff_nom"] = nom_cc
            s["p"] = p
            s["st"] = "DER"
            set_s(tel, s)
            wa(tel, f"Derivado a Coordinación ({nom_cc}). Te escribirán pronto.", "Sistema")
        elif up == "9":
            s["st"] = "MAIN"
            set_s(tel, s)
            _menu_main(tel, p)
    elif st in ("NVO_C1", "NVO_INV"):
        if up == "1":
            k = cc_libre()
            cc_add(k)
            tel_cc = STAFF[k]["tel"]
            nom_cc = STAFF[k]["nombre"]
            wa(tel_cc, f"*NUEVO PROSPECTO INTERESADO*\nTel: wa.me/{tel}\nInterés: {'C1' if st == 'NVO_C1' else 'Inversion'}", "SIS")
            p["staff_key"] = k
            p["staff_tel"] = tel_cc
            p["staff_nom"] = nom_cc
            s["p"] = p
            s["st"] = "DER"
            set_s(tel, s)
            wa(tel, f"Coordinación ({nom_cc}) te escribirá en breve.", "Sistema")
        elif up == "9":
            s["st"] = "NVO_INFO"
            set_s(tel, s)
            wa(tel, "1 Info C1\n2 Fechas\n3 Inversion\n4 Coordinación\n9 Volver", "Sistema")
    elif st == "DER":
        tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]
        nom_cc = p.get("staff_nom", "Coord")
        wa(tel_cc, f"*Nuevo mensaje de {p.get('nombre', 'Prospecto')}*\nTel: wa.me/{tel}\n\n{texto}", f"RELAY>{nom_cc}")
        wa(tel, "✓ Mensaje entregado.\n_Escribe 0 para volver_", "Sistema")
        s["st"] = "MAIN"
        set_s(tel, s)

# =============================================
# FLUJO PRINCIPAL
# =============================================
def flujo(tel, texto):
    try:
        up = texto.strip().upper()
        up_clean = _limpiar_input(up)
        if up_clean != up and up_clean in ('0','1','2','3','4','5','6','7','8','9'):
            up = up_clean
        if _es_autoresponder(up):
            logger.info(f"[AUTO-RESP] Ignorado de {tel}: {texto[:60]}")
            return
        if up in STOP_W:
            del_s(tel)
            wa(tel, "Has sido dado de baja. Escribe HOLA para reiniciar.\n\n*Crear Poder Sin Límites Perú*", "SIS")
            reg(tel, "", "", "STOP", "STOP", dir_="SYS")
            return
        s = get_s(tel)
        if tel in _CC_TELS:
            _flujo_cc(tel, up, texto, _CC_TELS[tel])
            return
        if not s or up in RESET_W:
            p = perfil_crm(tel)
            p["_tel"] = tel
            s = {"p": p, "st": "MAIN"}
            set_s(tel, s)
            _menu_main(tel, p)
            return
        p = s.get("p", {})
        p["_tel"] = tel
        if p.get("tipo") != "NUEVO" and not p.get("staff_tel"):
            equipo = p.get("equipo", "")
            k = cc_por_equipo(equipo) if equipo else cc_libre()
            p["staff_key"] = k
            p["staff_tel"] = STAFF[k]["tel"]
            p["staff_nom"] = STAFF[k]["nombre"]
            s["p"] = p
            set_s(tel, s)
        if up in {"9", "VOLVER", "REGRESAR", "ATRAS", "ATRÁS"}:
            s["st"] = "MAIN"
            set_s(tel, s)
            _menu_main(tel, p)
            return
        evento_actual = en_entrenamiento()
        if evento_actual and not s.get("notificado_entrenamiento"):
            wa(tel, f"▲ *Aviso automático:*\nActualmente todo el equipo se encuentra en el entrenamiento presencial *{evento_actual}*.\n\n_Nuestro tiempo de respuesta será mayor al habitual._ ▲", "SIS")
            s["notificado_entrenamiento"] = True
            set_s(tel, s)
        if _detectar_negativa(up) and p.get("tipo") in ("PX", "IMO"):
            nom_full = p.get("nombre_full") or p.get("nombre", "")
            nom_cc = notif_cc(p, f"PX expresa NEGATIVA/NO ASISTE", f"Mensaje: {texto[:150]}")
            reg(tel, nom_full, p.get("tipo", ""), texto[:100], "NEGATIVA", dir_="SYS", staff=nom_cc)
            wa(tel, f"Entendido. Tu mensaje ha sido enviado a tu coordinadora {nom_cc}.\n\n_STOP para darte de baja._", p.get("nombre", ""))
            del_s(tel)
            return
        tipo = p.get("tipo", "NUEVO")
        if tipo == "IMO":
            _imo(tel, up, texto, s, p)
        elif tipo == "PX":
            _px(tel, up, texto, s, p)
        else:
            _nuevo(tel, up, texto, s, p)
    except Exception as e:
        logger.error(f"flujo {tel}: {e}", exc_info=True)

# =============================================
# ENDPOINTS WEBHOOK
# =============================================
@app.route("/")
def index():
    return "<h1>Bot CPSL IA — Torre de Control Activa</h1><p>API Endpoint: /webhook</p>"

@app.route("/webhook", methods=["GET"])
def wh_get():
    if request.args.get("hub.verify_token") == Cfg.VER_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "error", 403

@app.route("/webhook", methods=["POST"])
def wh_post():
    d = request.get_json(silent=True)
    if not d:
        return jsonify({"status": "ok"}), 200
    try:
        chg = d["entry"][0]["changes"][0]["value"]
        if "messages" not in chg:
            return jsonify({"status": "ok"}), 200
        msg = chg["messages"][0]
        tel = msg.get("from", "")
        tipo = msg.get("type", "")
        if tipo == "text":
            txt = str(msg["text"]["body"])
            s_wh = get_s(tel)
            p_wh = s_wh.get("p") or perfil_crm(tel)
            nom_d = (p_wh.get("nombre_full") or p_wh.get("imo_nombre") or p_wh.get("nombre") or tel)
            nom_h = f"({p_wh.get('tipo','?')}) {nom_d}"
            add_hist(tel, nom_h, txt, "in")
            reg(tel, p_wh.get("nombre", ""), p_wh.get("tipo", ""), txt, "MSG_IN", staff=p_wh.get("staff_nom", ""))
            threading.Thread(target=flujo, args=(tel, txt), daemon=False, name=f"{tel[-4:]}").start()
        else:
            wa(tel, "Por favor responde con texto o el número de tu opción.", "SIS")
    except Exception as e:
        logger.error(f"wh {e}", exc_info=True)
    return jsonify({"status": "ok"}), 200

# =============================================
# KEEPALIVE LOOP
# =============================================
def _keepalive_loop():
    INTERVALO = 23 * 3600
    import time as _t
    _t.sleep(3600)
    while True:
        try:
            CCS_KEEPALIVE = [
                ("51912379744", "Diana"),
                ("51933599903", "Joyce"),
                ("51933599864", "Zuley"),
            ]
            for tel_cc, nom in CCS_KEEPALIVE:
                wa(tel_cc, f"Hola {nom} — CPSL Lima al día.\nEstamos disponibles. Escribe *HOLA* si necesitas algo.", "KEEPALIVE")
                _t.sleep(3)
            logger.info(f"Keepalive completado — {ahora().strftime('%d/%m/%Y %H:%M')}")
        except Exception as e:
            logger.error(f"keepalive_loop: {e}")
        _t.sleep(INTERVALO)

threading.Thread(target=_keepalive_loop, daemon=True, name="keepalive").start()
logger.info("Keepalive loop activo — ciclo 23h")

# =============================================
# SCHEDULER IMO
# =============================================
def _scheduler_imos():
    import time as _time
    while True:
        try:
            hora = ahora().strftime("%H:%M")
            if hora == "07:30":
                logger.info("[IMO-SCHED] Enviando mensajes principales a IMOs...")
            elif hora == "10:00":
                logger.info("[RECORDATORIOS] Enviando recordatorios a IMOs...")
        except Exception as e:
            logger.error(f"[IMO-SCHED] Error: {e}")
        _time.sleep(60)

_scheduler_started = False
_scheduler_lock = threading.Lock()

@app.before_request
def start_background_tasks_once():
    global _scheduler_started
    if not _scheduler_started:
        with _scheduler_lock:
            if not _scheduler_started:
                logger.info("Iniciando tareas de fondo (Scheduler IMO)...")
                threading.Thread(target=_scheduler_imos, daemon=True, name="imo_scheduler").start()
                _scheduler_started = True

# =============================================
# SYNC CREARPSL
# =============================================
try:
    from sync_crearpsl import iniciar_thread as iniciar_sync_crearpsl
    iniciar_sync_crearpsl()
    logger.info("Sync CrearPSL iniciado — cada 30 min")
except Exception as e:
    logger.warning(f"Sync CrearPSL no inició: {e}")

# =============================================
# MAIN
# =============================================
if __name__ == "__main__":
    logger.info("CPSL Torre de Control V112 + IMO Tracking")
    logger.info(f"CSV: {Cfg.CSV}")
    logger.info(f"CSV existe: {os.path.exists(Cfg.CSV)}")
    logger.info(f"Filas: {len(_get_rows())}")
    logger.info(f"Sheet: {Cfg.SHEET_ID or 'NO CONFIG'}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=False)
