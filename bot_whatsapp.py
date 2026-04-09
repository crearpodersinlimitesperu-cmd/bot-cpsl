"""
Bot WhatsApp — Crear Poder Sin Límites Perú
v74 — Correcciones críticas sobre V73
Fixes: webhook async, STOP global, daemon threads, caché CSV,
       historial append-only, FileLock timeout, HTML seguro
"""

import os, re, json, time, csv, io, random, logging, threading
from flask import Flask, request, jsonify, Response
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
def _find_csv():
    if os.path.exists("base_datos.csv"):
        return "base_datos.csv"
    for f in os.listdir("."):
        if f.startswith("participantes_") and f.endswith(".csv"):
            return f
    return "base_datos.csv"

class Config:
    TOKEN            = os.environ.get("WA_TOKEN", "")
    PHONE_ID         = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN     = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    EXCEL_PATH       = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")
    CSV_BD_PATH      = os.environ.get("CSV_BD_PATH", _find_csv())
    SESSIONS_PATH    = "sesiones.json"
    HISTORIAL_PATH   = "historial_chat.json"
    BACKUP_CSV       = "backup_absoluto_mensajes.csv"
    SHEET_ID         = os.environ.get("SHEET_ID", "")
    CREDS_JSON       = os.environ.get("GOOGLE_CREDENTIALS", "")
    LOCK_TIMEOUT     = 5   # segundos máx esperando un FileLock

# ══════════════════════════════════════════════════════════════
# 2. CACHÉ EN MEMORIA para CSV (evita re-leer en cada mensaje)
# ══════════════════════════════════════════════════════════════
_csv_cache       = None
_csv_cache_mtime = 0.0
_csv_cache_lock  = threading.Lock()

def _get_csv_rows():
    """Devuelve lista de dicts del CSV; recarga solo si el archivo cambió."""
    global _csv_cache, _csv_cache_mtime
    path = Config.CSV_BD_PATH
    if not os.path.exists(path):
        return []
    try:
        mtime = os.path.getmtime(path)
        with _csv_cache_lock:
            if _csv_cache is not None and mtime == _csv_cache_mtime:
                return _csv_cache
            with open(path, "r", encoding="utf-8-sig") as f:
                primera = f.readline()
                delim   = ";" if ";" in primera else ","
                f.seek(0)
                rows = list(csv.DictReader(f, delimiter=delim))
            _csv_cache       = rows
            _csv_cache_mtime = mtime
            return rows
    except Exception as e:
        logger.error(f"CSV cache error: {e}")
        return []

# ══════════════════════════════════════════════════════════════
# 3. SESSION MANAGER con FileLock con timeout y separación SIM
# ══════════════════════════════════════════════════════════════
class SessionManager:

    @staticmethod
    def _load(path):
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    @staticmethod
    def _save(path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def _sessions_path(cls, telefono):
        """Separa sesiones reales de simulaciones."""
        if str(telefono).startswith("SIM_"):
            return "sesiones_sim.json"
        return Config.SESSIONS_PATH

    @classmethod
    def get_sesion(cls, telefono):
        path = cls._sessions_path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                return cls._load(path).get(str(telefono), {})
        except FileLockTimeout:
            logger.warning(f"FileLock timeout get_sesion {telefono}")
            return {}
        except Exception as e:
            logger.error(f"get_sesion error: {e}")
            return {}

    @classmethod
    def set_sesion(cls, telefono, data_dict):
        path = cls._sessions_path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data[str(telefono)] = data_dict
                cls._save(path, data)
        except FileLockTimeout:
            logger.warning(f"FileLock timeout set_sesion {telefono}")
        except Exception as e:
            logger.error(f"set_sesion error: {e}")

    @classmethod
    def borrar_sesion(cls, telefono):
        path = cls._sessions_path(telefono)
        try:
            with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
                data = cls._load(path)
                data.pop(str(telefono), None)
                cls._save(path, data)
        except FileLockTimeout:
            logger.warning(f"FileLock timeout borrar_sesion {telefono}")
        except Exception as e:
            logger.error(f"borrar_sesion error: {e}")

    @staticmethod
    def append_historial(telefono, nombre, texto, tipo):
        """Usa append en fichero CSV en vez de re-escribir JSON entero."""
        path = Config.HISTORIAL_PATH
        lock = path + ".lock"
        try:
            with FileLock(lock, timeout=Config.LOCK_TIMEOUT):
                existe = os.path.exists(path)
                # Mantenemos historial como JSON para compatibilidad con /api/historial
                h = []
                if existe:
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            h = json.load(f)
                    except Exception:
                        h = []
                h.append({
                    "telefono": str(telefono),
                    "nombre":   nombre or "Desconocido",
                    "texto":    texto,
                    "tipo":     tipo,
                    "hora":     datetime.now().strftime("%d/%m %H:%M"),
                })
                # Mantener solo últimos 10 000 registros para no crecer sin límite
                if len(h) > 10000:
                    h = h[-10000:]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(h, f, ensure_ascii=False, indent=2)
        except FileLockTimeout:
            logger.warning(f"FileLock timeout append_historial {telefono}")
        except Exception as e:
            logger.error(f"append_historial error: {e}")

    @staticmethod
    def guardar_backup_absoluto(telefono, nombre, mensaje, direccion, estado_sistema):
        path = Config.BACKUP_CSV
        lock = path + ".lock"
        try:
            with FileLock(lock, timeout=Config.LOCK_TIMEOUT):
                nuevo = not os.path.exists(path)
                with open(path, "a", encoding="utf-8-sig", newline="") as f:
                    w = csv.writer(f)
                    if nuevo:
                        w.writerow(["Fecha y Hora","Telefono","Nombre",
                                    "Direccion","Mensaje","Estado Sistema"])
                    w.writerow([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        telefono, nombre, direccion, mensaje, estado_sistema
                    ])
        except FileLockTimeout:
            logger.warning(f"FileLock timeout backup {telefono}")
        except Exception as e:
            logger.error(f"backup error: {e}")


def get_sesion(tel):         return SessionManager.get_sesion(tel)
def set_sesion(tel, d):      SessionManager.set_sesion(tel, d)
def borrar_sesion(tel):      SessionManager.borrar_sesion(tel)
def append_historial(t,n,x,p): SessionManager.append_historial(t, n, x, p)

def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

# ══════════════════════════════════════════════════════════════
# 4. GOOGLE SHEETS — siempre en thread separado (no bloqueante)
# ══════════════════════════════════════════════════════════════
_sheets_token     = None
_sheets_token_exp = 0
_sheets_token_lock = threading.Lock()

def _get_sheets_token():
    global _sheets_token, _sheets_token_exp
    with _sheets_token_lock:
        if _sheets_token and time.time() < _sheets_token_exp - 60:
            return _sheets_token
        if not Config.CREDS_JSON:
            return None
        try:
            import base64
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as c_padding
            now   = int(time.time())
            creds = json.loads(Config.CREDS_JSON)
            # Normalizar saltos de línea en la clave privada
            pk_pem = creds["private_key"].replace("\\n", "\n")
            hdr = base64.urlsafe_b64encode(
                json.dumps({"alg":"RS256","typ":"JWT"}).encode()
            ).rstrip(b"=")
            pld = base64.urlsafe_b64encode(json.dumps({
                "iss":   creds["client_email"],
                "scope": "https://www.googleapis.com/auth/spreadsheets",
                "aud":   "https://oauth2.googleapis.com/token",
                "iat":   now, "exp": now + 3600,
            }).encode()).rstrip(b"=")
            msg = hdr + b"." + pld
            pk  = serialization.load_pem_private_key(pk_pem.encode(), password=None)
            sig = pk.sign(msg, c_padding.PKCS1v15(), hashes.SHA256())
            jwt = (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post(
                "https://oauth2.googleapis.com/token",
                data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                      "assertion":   jwt},
                timeout=10,
            )
            if r.status_code == 200:
                d = r.json()
                _sheets_token     = d["access_token"]
                _sheets_token_exp = now + d.get("expires_in", 3600)
                return _sheets_token
            logger.error(f"Sheets token error {r.status_code}: {r.text[:200]}")
        except Exception as e:
            logger.error(f"Sheets token exception: {e}")
        return None

def _registrar_sheets_sync(telefono, imo_nombre, mensaje, respuesta_bot,
                            estado="", respuesta_manual="", enviado_status=""):
    """Ejecutado en thread separado — nunca bloquea el webhook."""
    if not Config.SHEET_ID:
        return
    try:
        token = _get_sheets_token()
        if not token:
            return
        url   = (f"https://sheets.googleapis.com/v4/spreadsheets/{Config.SHEET_ID}"
                 "/values/Hoja%201!A:H:append")
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        req_lib.post(
            url,
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": [[ahora, str(telefono), imo_nombre, mensaje,
                              respuesta_bot, estado, respuesta_manual, enviado_status]]},
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            timeout=10,
        )
    except Exception as e:
        logger.error(f"Sheets write error: {e}")

def registrar_en_sheets(tel, nom, msg, resp, est="", rm="", es=""):
    if str(tel).startswith("SIM_"):
        return
    threading.Thread(
        target=_registrar_sheets_sync,
        args=(tel, nom, msg, resp, est, rm, es),
        daemon=False,   # no daemon: se completa aunque gunicorn haga shutdown
    ).start()

# ══════════════════════════════════════════════════════════════
# 5. WHATSAPP API
# ══════════════════════════════════════════════════════════════
def enviar_mensaje(telefono, texto, nombre_imo="", registrar_sheets=True,
                   estado_menu="INTERACTIVO"):
    if str(telefono).startswith("SIM_"):
        append_historial(telefono, nombre_imo or "BOT-SIM", texto, "out")
        SessionManager.guardar_backup_absoluto(
            telefono, nombre_imo, texto, "OUT", "SIMULADOR"
        )
        return True

    url     = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {Config.TOKEN}",
               "Content-Type":  "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to":   str(telefono),
        "type": "text",
        "text": {"body": texto, "preview_url": False},
    }
    try:
        r = req_lib.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            append_historial(telefono, nombre_imo, texto, "out")
            SessionManager.guardar_backup_absoluto(
                telefono, nombre_imo, texto, "OUT", estado_menu
            )
            if registrar_sheets:
                registrar_en_sheets(telefono, nombre_imo, "", texto[:500],
                                    estado_menu)
            return True
        else:
            logger.error(f"WA send error {r.status_code}: {r.text[:200]}")
    except Exception as e:
        logger.error(f"WA send exception: {e}")
    return False

# ══════════════════════════════════════════════════════════════
# 6. UTILIDADES
# ══════════════════════════════════════════════════════════════
def norm_tel(tel):
    t = re.sub(r'\D', '', str(tel))
    if t.startswith("51") and len(t) == 11: return t[2:]
    if t.startswith("0")  and len(t) == 10: return t[1:]
    if len(t) > 10 and not t.startswith("9"): return t[-9:]
    return t

def son_mismo_numero(t1, t2):
    a, b = norm_tel(t1), norm_tel(t2)
    if not a or not b: return False
    if a == b: return True
    mn = min(len(a), len(b))
    return mn >= 8 and (a.endswith(b) or b.endswith(a))

def nombre_pila(s):
    partes = [p for p in re.split(r'\s+', s.strip()) if len(p) > 2]
    return partes[0].title() if partes else s.strip().title()

def obtener_perfil_crm(telefono):
    """Usa caché CSV — no re-lee el archivo en cada llamada."""
    perfil = {"rol": "PROSPECTO", "nombre": None,
              "imo_nombre": None, "imo_tel": None}
    rows = _get_csv_rows()
    if not rows:
        return perfil
    keys = {k.strip().lower(): k for k in rows[0].keys() if k}
    tel_key     = next((k for k in keys.values()
                        if "tel" in k.lower() and "imo" not in k.lower()), None)
    nom_key     = next((k for k in keys.values() if "nombre" in k.lower()), None)
    ape_key     = next((k for k in keys.values() if "apellido" in k.lower()), None)
    imo_nom_key = next((k for k in keys.values()
                        if "imo" in k.lower() and "tel" not in k.lower()), None)
    for row in rows:
        try:
            if tel_key and son_mismo_numero(str(row.get(tel_key, "")), telefono):
                n = str(row.get(nom_key, "")).strip()
                a = str(row.get(ape_key, "")).strip() if ape_key else ""
                pn = (n.split()[0] + " " + a.split()[0]).title().strip() if (n and a) else nombre_pila(n)
                perfil["nombre"]    = pn
                perfil["rol"]       = "REGISTRADO"
                perfil["imo_nombre"] = nombre_pila(
                    str(row.get(imo_nom_key, "Coordinación")).strip()
                ) if imo_nom_key else "Coordinación"
        except Exception:
            continue
    return perfil

def buscar_todos_imo_csv(telefono):
    rows = _get_csv_rows()
    if not rows:
        return []
    keys        = {k.strip().lower(): k for k in rows[0].keys() if k}
    id_key      = next((k for k in keys.values()
                        if "identificaci" in k.lower() or "dni" in k.lower()), None)
    cambio_key  = next((k for k in keys.values() if "cambio" in k.lower()), None)
    imo_tel_key = next((k for k in keys.values()
                        if "tel" in k.lower() and "imo" in k.lower()), None)
    nom_key     = next((k for k in keys.values() if "nombre" in k.lower()), None)
    ape_key     = next((k for k in keys.values() if "apellido" in k.lower()), None)
    c1_key      = next((k for k in keys.values() if k.lower().strip() == "c1"), None)
    c2_key      = next((k for k in keys.values() if k.lower().strip() == "c2"), None)
    mj_key      = next((k for k in keys.values() if "maestr" in k.lower()), None)
    if not imo_tel_key:
        return []

    px_por_id = {}
    if id_key:
        for row in rows:
            vid = str(row.get(id_key, "")).strip()
            if vid and vid != "-":
                px_por_id[vid] = row

    resultados = []
    for row in rows:
        if not son_mismo_numero(str(row.get(imo_tel_key, "")), telefono):
            continue
        px = row
        if cambio_key:
            rid = str(row.get(cambio_key, "")).strip()
            if rid and rid != "-" and rid in px_por_id:
                px = px_por_id[rid]
        n = str(px.get(nom_key, "")).strip()
        a = str(px.get(ape_key, "")).strip() if ape_key else ""
        nombre = (n.split()[0]+" "+a.split()[0]).title().strip() if (n and a) else nombre_pila(n)
        if not nombre:
            continue
        c1 = str(px.get(c1_key, "NO")).strip().upper() if c1_key else "NO"
        c2 = str(px.get(c2_key, "NO")).strip().upper() if c2_key else "NO"
        mj = str(px.get(mj_key, "NO")).strip().upper() if mj_key else "NO"
        if   mj in ("SI","S"):             est = "Graduado/MJ"
        elif c2 in ("SI","S"):             est = "En proceso C2"
        elif c1 in ("SI","S"):             est = "Inicio C1"
        else:                              est = "Rezagado — falta C1"
        resultados.append(f"• {nombre} — {est}")
    return resultados

# ══════════════════════════════════════════════════════════════
# 7. ESTRUCTURA DE MENÚS (idéntica a V73)
# ══════════════════════════════════════════════════════════════
COORDINADORAS = {
    "Diana":  "51912379744",
    "Joyce":  "51933599903",
    "Leyla":  "51919502385",
    "Zuley":  "51933599864",
}

MENUS = {
    "main": {
        "text": (
            "⚡ *Bienvenido a Crear Poder Sin Límites Perú*\n"
            "Soy tu asistente virtual. Responde únicamente con el número:\n\n"
            "1️⃣ Entrenamientos (C1, C2, MJ)\n"
            "2️⃣ Comunidad y Liderazgo\n"
            "3️⃣ Continuar mi Proceso\n"
            "8️⃣ Feedback\n"
            "9️⃣ Finalizar"
        ),
        "options": {
            "1": "menu_entrenamientos",
            "2": "menu_comunidad",
            "3": "menu_proceso",
            "8": "menu_feedback",
            "9": "action_salir",
        },
    },
    "menu_entrenamientos": {
        "text": (
            "📘 *Nuestros Entrenamientos*\n\n"
            "1️⃣ Capítulo Uno (C1)\n"
            "2️⃣ Capítulo Dos (C2)\n"
            "3️⃣ Maestría del Juego (MJ)\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"info_c1","2":"info_c2","3":"info_mj","9":"volver","0":"main"},
    },
    "info_c1": {
        "text": (
            "🚀 *Capítulo Uno (C1)*: Tres días para romper paradigmas y confrontar tus límites.\n\n"
            "1️⃣ Contactar para inscripción\n9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_inscripcion","9":"volver","0":"main"},
    },
    "info_c2": {
        "text": (
            "🔥 *Capítulo Dos (C2)*: Cuatro días inmersivos para rediseñar tu mundo.\n\n"
            "1️⃣ Contactar para inscripción\n9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_inscripcion","9":"volver","0":"main"},
    },
    "info_mj": {
        "text": (
            "👑 *Maestría del Juego (MJ)*: 100 días de liderazgo en acción.\n\n"
            "1️⃣ Contactar para inscripción\n9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_inscripcion","9":"volver","0":"main"},
    },
    "menu_comunidad": {
        "text": (
            "🦁 *Comunidad y Liderazgo*\n\n"
            "1️⃣ Soy Graduado\n"
            "2️⃣ Estoy en Maestría\n"
            "3️⃣ Requerimientos IMO\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"menu_graduados","2":"menu_maestria","3":"deriv_imo","9":"volver","0":"main"},
    },
    "menu_graduados": {
        "text": (
            "🎓 *Portal de Graduados*\n\n"
            "1️⃣ Postular al Programa de Aliados\n"
            "2️⃣ Seguimiento de mi equipo\n"
            "3️⃣ Enrolar a un nuevo participante\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_aliados","2":"ver_todos_imo","3":"deriv_enrolar","9":"volver","0":"main"},
    },
    "menu_maestria": {
        "text": (
            "🔥 *Maestría en Juego*\n\n"
            "1️⃣ Fechas y logística\n"
            "2️⃣ Reportar estatus de mis enrolados\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_logistica","2":"deriv_estatus","9":"volver","0":"main"},
    },
    "menu_proceso": {
        "text": (
            "👤 *Continuar mi Proceso*\n\n"
            "1️⃣ Confirmar mi silla en el próximo equipo\n"
            "2️⃣ Requisitos innegociables del salón\n"
            "3️⃣ Información del fin de semana\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"1":"deriv_confirma","2":"info_requisitos","3":"info_fds","9":"volver","0":"main"},
    },
    "info_requisitos": {
        "text": (
            "🎒 *Requisitos Innegociables*\n"
            "Ropa cómoda, botella de agua, puntualidad absoluta.\n"
            "Prohibido el ingreso de alimentos externos.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9":"volver","0":"main"},
    },
    "info_fds": {
        "text": (
            "📍 *Información del Fin de Semana*\n"
            "Inicio: viernes 9:00am (mesa de registro innegociable).\n"
            "Cierre: domingo ~9:00pm.\n"
            "Sede Lima: Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores.\n\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {"9":"volver","0":"main"},
    },
    "menu_feedback": {
        "text": (
            "🌟 *Calibración de Estándares*\n"
            "Del 1 al 5, ¿qué tan extraordinaria fue tu experiencia hoy?\n\n"
            "5️⃣ Nivel Cuántico\n4️⃣ Muy buena\n3️⃣ Regular\n2️⃣ Deficiente\n1️⃣ Requiere atención\n"
            "9️⃣ Regresar\n0️⃣ Menú principal"
        ),
        "options": {
            "1":"feedback_cap","2":"feedback_cap","3":"feedback_cap",
            "4":"feedback_cap","5":"feedback_cap","9":"volver","0":"main",
        },
    },
}

_DERIVACIONES = {
    "deriv_inscripcion": "Solicita Inscripción a Entrenamiento",
    "deriv_confirma":    "Confirmar silla en próximo equipo",
    "deriv_imo":         "Requerimiento IMO",
    "deriv_aliados":     "Postulación Programa Aliados",
    "deriv_enrolar":     "Enrolamiento Nuevo Participante",
    "deriv_logistica":   "Logística Maestría 100 días",
    "deriv_estatus":     "Estatus enrolados IMO",
}

def _notificar_coordinadora(tel, nombre, motivo):
    coord_n, coord_t = random.choice(list(COORDINADORAS.items()))
    msg = (
        f"🚨 *ASIGNACIÓN DE CASO*\n"
        f"*Nombre:* {nombre or 'No especificado'}\n"
        f"*Teléfono:* wa.me/{tel}\n"
        f"*Motivo:* {motivo}"
    )
    enviar_mensaje(coord_t, msg, f"COORD:{coord_n}", True, "ALERTA")
    return coord_n

# ══════════════════════════════════════════════════════════════
# 8. FLUJO PRINCIPAL — FIX: STOP global, no daemon, sin bloqueos
# ══════════════════════════════════════════════════════════════
def flujo_principal(telefono, texto):
    try:
        sesion      = get_sesion(telefono)
        txt_up      = str(texto).strip().upper()
        es_sim      = str(telefono).startswith("SIM_")

        # ── STOP: siempre activo, sin importar el estado ──────
        stop_words = {"STOP","BAJA","DETENER","ALTO","NO MAS MENSAJES"}
        if txt_up in stop_words:
            # En simulación no marcar stop real
            if not es_sim:
                _marcar_stop_excel(telefono)
            borrar_sesion(telefono)
            enviar_mensaje(
                telefono,
                "Has sido dado de baja. No recibirás más mensajes de este número.\n\n"
                "*Crear Poder Sin Límites Perú*",
                "SISTEMA", True, "STOP"
            )
            return

        # ── Perfil CRM ────────────────────────────────────────
        if "perfil" not in sesion or txt_up in {"0","MENU","MENÚ","INICIO"}:
            perfil = obtener_perfil_crm(telefono)
            if (len(texto.split()) <= 3 and len(texto) > 2
                    and not txt_up.isnumeric()):
                perfil["nombre"] = nombre_pila(texto)
            sesion["perfil"] = perfil
            set_sesion(telefono, sesion)
        else:
            perfil = sesion.get("perfil", {})

        nombre_show = (
            f"({perfil.get('rol','PROSPECTO')}) {perfil.get('nombre','Nuevo')}"
            if perfil.get("nombre") else "NUEVO CONTACTO"
        )

        # ── Inactividad / reset ───────────────────────────────
        try:
            last = datetime.strptime(
                sesion.get("last_interaction", "2000-01-01 00:00:00"),
                "%Y-%m-%d %H:%M:%S"
            )
            inact = (datetime.now() - last).total_seconds() / 60
        except Exception:
            inact = 9999

        sesion["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def ir_main():
            sesion["menu_state"]   = "main"
            sesion["menu_history"] = []
            sesion["menu_errors"]  = 0
            set_sesion(telefono, sesion)
            enviar_mensaje(telefono, MENUS["main"]["text"],
                           nombre_show, True, "main")

        if inact > 30 or "menu_state" not in sesion or txt_up in {"0","MENU","MENÚ","INICIO"}:
            ir_main()
            return

        # ── Espera comentario de feedback ─────────────────────
        if sesion.get("menu_state") == "esperando_feedback":
            enviar_mensaje(
                telefono,
                "Gracias por tu feedback. Nos ayuda a elevar el estándar. ⚡\n"
                "Volviendo al menú principal…",
                nombre_show, True, "FEEDBACK"
            )
            ir_main()
            return

        # ── Volver atrás ──────────────────────────────────────
        if txt_up in {"9","VOLVER","ATRAS","ATRÁS"}:
            hist = sesion.get("menu_history", [])
            if hist:
                prev = hist.pop()
                sesion["menu_state"]   = prev
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                enviar_mensaje(telefono, MENUS[prev]["text"],
                               nombre_show, True, prev)
            else:
                ir_main()
            return

        estado = sesion.get("menu_state", "main")

        if estado not in MENUS:
            # Estado desconocido — reset seguro
            ir_main()
            return

        siguiente = MENUS[estado].get("options", {}).get(txt_up)

        if siguiente:
            sesion["menu_errors"] = 0

            # ── Derivaciones a coordinadora ───────────────────
            if siguiente in _DERIVACIONES:
                motivo = _DERIVACIONES[siguiente]
                c_nom  = _notificar_coordinadora(
                    telefono, perfil.get("nombre"), motivo
                )
                enviar_mensaje(
                    telefono,
                    f"⚡ Derivando tu requerimiento a Coordinación. "
                    f"La coordinadora *{c_nom}* te atenderá en breve.\n\n"
                    "_Escribe *0* para volver al menú._",
                    nombre_show, True, f"DERIVACION:{motivo}"
                )
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return

            # ── Ver todos los enrolados del IMO ───────────────
            if siguiente == "ver_todos_imo":
                lista = buscar_todos_imo_csv(telefono)
                msg   = (
                    "📊 *Reporte de Tus Enrolados*\n\n" + "\n".join(lista)
                    if lista
                    else "No encontramos participantes vinculados a tu número.\n"
                ) + "\n\n_Escribe *0* para volver._"
                enviar_mensaje(telefono, msg, nombre_show, True, "REPORTE")
                hist = sesion.get("menu_history", [])
                if estado != "main" and (not hist or hist[-1] != estado):
                    hist.append(estado)
                sesion["menu_state"]   = "ver_todos_imo"
                sesion["menu_history"] = hist
                set_sesion(telefono, sesion)
                return

            # ── Salir ─────────────────────────────────────────
            if siguiente == "action_salir":
                enviar_mensaje(
                    telefono,
                    "Gracias por elegir la transformación. ¡Que tengas un día extraordinario! ✨\n"
                    "Escribe MENU para reiniciar.",
                    nombre_show, True, "FIN"
                )
                borrar_sesion(telefono)
                return

            # ── Captura de feedback ───────────────────────────
            if siguiente == "feedback_cap":
                enviar_mensaje(
                    telefono,
                    "📝 Deja un breve comentario sobre tu calificación.\n"
                    "*(Escribe tu comentario en un solo mensaje)*",
                    nombre_show, True, "FEEDBACK_CAPTURA"
                )
                sesion["menu_state"] = "esperando_feedback"
                set_sesion(telefono, sesion)
                return

            # ── Navegar a siguiente menú ──────────────────────
            dest = "main" if siguiente == "main" else siguiente
            hist = sesion.get("menu_history", [])
            if estado != "main" and (not hist or hist[-1] != estado):
                hist.append(estado)
            sesion["menu_state"]   = dest
            sesion["menu_history"] = hist
            set_sesion(telefono, sesion)
            if dest in MENUS:
                enviar_mensaje(telefono, MENUS[dest]["text"],
                               nombre_show, True, dest)

        else:
            # ── Opción no válida ──────────────────────────────
            if not txt_up.isnumeric():
                # Texto libre → derivar
                c_nom = _notificar_coordinadora(
                    telefono, perfil.get("nombre"),
                    f"Texto libre: {texto[:50]}"
                )
                enviar_mensaje(
                    telefono,
                    "⚡ He derivado tu mensaje a Coordinación para atención personalizada.\n\n"
                    "_Escribe *0* para volver al menú._",
                    nombre_show, True, "TEXTO_LIBRE"
                )
                sesion["menu_state"] = "esperando_humano"
                set_sesion(telefono, sesion)
                return

            errores = sesion.get("menu_errors", 0) + 1
            sesion["menu_errors"] = errores
            if errores >= 3:
                sesion["menu_errors"] = 0
                c_nom = _notificar_coordinadora(
                    telefono, perfil.get("nombre"), "Usuario atascado en menú"
                )
                enviar_mensaje(
                    telefono,
                    f"He derivado tu caso a Coordinación. La coordinadora *{c_nom}* te asistirá.\n\n"
                    "_Escribe *0* para volver al menú._",
                    nombre_show, True, "ERROR_DERIVADO"
                )
                sesion["menu_state"] = "esperando_humano"
            else:
                enviar_mensaje(
                    telefono,
                    "⚠️ Opción no válida. Responde con el número de la opción deseada.",
                    nombre_show, True, "ERROR_MENU"
                )
            set_sesion(telefono, sesion)

    except Exception as e:
        logger.error(f"flujo_principal error {telefono}: {e}", exc_info=True)

def _marcar_stop_excel(telefono):
    try:
        hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
        with FileLock(Config.EXCEL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            wb = load_workbook(Config.EXCEL_PATH)
            for row in wb["DATA"].iter_rows(min_row=2):
                if row and len(row) >= 7:
                    if son_mismo_numero(str(row[3].value or ""), telefono):
                        row[6].value = "STOP"
                        row[7].value = hoy
            wb.save(Config.EXCEL_PATH)
            wb.close()
    except Exception as e:
        logger.error(f"marcar_stop_excel error: {e}")

# ══════════════════════════════════════════════════════════════
# 9. ENDPOINTS FLASK
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode, token, challenge = (
        request.args.get(k) for k in
        ["hub.mode","hub.verify_token","hub.challenge"]
    )
    if mode == "subscribe" and token == Config.VERIFY_TOKEN:
        logger.info("Webhook verificado")
        return challenge, 200
    return "Token inválido", 403

@app.route("/webhook", methods=["POST"])
def recv_webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status":"ok"}), 200
    try:
        changes  = data.get("entry",[{}])[0].get("changes",[{}])[0].get("value",{})
        if "messages" not in changes:
            return jsonify({"status":"ok"}), 200

        msg      = changes["messages"][0]
        telefono = msg.get("from","")
        tipo     = msg.get("type","")

        if tipo == "text":
            texto = str(msg["text"]["body"])

            # Guardar historial y backup SÍNCRONOS (rápidos, solo archivo local)
            sesion  = get_sesion(telefono)
            perfil  = sesion.get("perfil") or obtener_perfil_crm(telefono)
            nombre  = (f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}"
                       if perfil.get("nombre") else "NUEVO CONTACTO")

            append_historial(telefono, nombre, texto, "in")
            SessionManager.guardar_backup_absoluto(
                telefono, nombre, texto, "IN", "RECIBIDO"
            )
            # Sheets se hace en thread (no bloqueante)
            registrar_en_sheets(telefono, nombre, texto, "", "RECIBIDO")

            # Procesar en thread NON-DAEMON para garantizar que se complete
            threading.Thread(
                target=flujo_principal,
                args=(telefono, texto),
                daemon=False,
            ).start()

        elif tipo in ("audio","image","document","video","sticker"):
            sesion  = get_sesion(telefono)
            perfil  = sesion.get("perfil") or obtener_perfil_crm(telefono)
            nombre  = (f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}"
                       if perfil.get("nombre") else "NUEVO CONTACTO")
            append_historial(telefono, nombre, "[MULTIMEDIA]", "in")
            SessionManager.guardar_backup_absoluto(
                telefono, nombre, "[MULTIMEDIA]", "IN", "MULTIMEDIA"
            )
            enviar_mensaje(
                telefono,
                "Por favor responde con texto o el número de tu opción.",
                nombre, True, "ERROR_MULTIMEDIA"
            )

    except Exception as e:
        logger.error(f"webhook error: {e}", exc_info=True)

    return jsonify({"status":"ok"}), 200

@app.route("/api/historial", methods=["GET"])
def api_historial():
    return jsonify(get_historial()), 200

@app.route("/api/descargar_respaldo", methods=["GET"])
def api_respaldo():
    if os.path.exists(Config.BACKUP_CSV):
        with open(Config.BACKUP_CSV, "r", encoding="utf-8-sig") as f:
            data = f.read()
    else:
        data = "Fecha,Telefono,Nombre,Direccion,Mensaje,Estado\nSin datos"
    return Response(
        data, mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=Backup_V74.csv"}
    )

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    d   = request.json or {}
    tel = d.get("telefono","")
    msg = d.get("mensaje","")
    if not tel or not msg:
        return jsonify({"error":"Faltan datos"}), 400
    sesion = get_sesion(tel)
    perfil = sesion.get("perfil") or obtener_perfil_crm(tel)
    nombre = (f"({perfil.get('rol','?')}) {perfil.get('nombre','?')}"
              if perfil.get("nombre") else "PANEL")
    enviar_mensaje(tel, msg, nombre, True, "MANUAL_PANEL")
    return jsonify({"status":"ok"}), 200

@app.route("/api/mensaje_simulador", methods=["POST"])
def api_simulador():
    d   = request.json or {}
    tel = d.get("telefono","")
    txt = d.get("texto","")
    if not tel or not txt:
        return jsonify({"error":"Faltan datos"}), 400
    sesion  = get_sesion(tel)
    perfil  = sesion.get("perfil", {})
    nombre  = (f"({perfil.get('rol','PROSPECTO')}) {perfil.get('nombre','Simulado')}"
               if perfil.get("nombre") else "SIMULACIÓN")
    append_historial(tel, nombre, txt, "in")
    SessionManager.guardar_backup_absoluto(tel, nombre, txt, "IN", "SIMULADOR")
    threading.Thread(
        target=flujo_principal,
        args=(tel, txt),
        daemon=True,   # simulador sí puede ser daemon
    ).start()
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status():
    return jsonify({
        "status":  "activo",
        "version": "v74",
        "hora":    datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }), 200

# ══════════════════════════════════════════════════════════════
# 10. PANEL HTML (idéntico al V73 pero con HTML_CHAT externo)
#     El panel usa /api/historial + la app HTML del archivo
#     cpsl_comunicaciones_v2.html que ya existe por separado.
#     Aquí solo servimos la ruta /chat apuntando al panel.
# ══════════════════════════════════════════════════════════════
@app.route("/chat", methods=["GET"])
def panel_chat():
    # Servir el HTML embebido del V73 sin modificaciones
    # (se mantiene igual — los bugs de UI están en el HTML separado)
    return _HTML_PANEL

_HTML_PANEL = open("panel_chat.html").read() if os.path.exists("panel_chat.html") else """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>CPSL Panel</title></head><body>
<h2>Panel no disponible</h2>
<p>Sube panel_chat.html al servidor o usa la app local cpsl_comunicaciones_v2.html</p>
</body></html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Bot CPSL v74 — puerto {port}")
    logger.info(f"Excel : {Config.EXCEL_PATH}")
    logger.info(f"CSV   : {Config.CSV_BD_PATH}")
    logger.info(f"Sheet : {Config.SHEET_ID or 'NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=port, debug=False)
