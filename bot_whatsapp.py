"""
Bot WhatsApp — Crear Poder Sin Límites Perú
V108: Torre de Control — Sistema Integral de Gestión Cuántica
Sede Lima

Pilares:
  1. CRM: identifica PX / IMO-Graduado / Nuevo por teléfono
  2. Enrutamiento inteligente: CC asignado o reparto equitativo
  3. Menús segmentados por perfil
  4. Protocolo de perfilamiento para nuevos contactos
  5. Notificaciones automáticas a CC al confirmar / solicitar aliado
  6. Make.com webhook (Google Sheets espejo)
  7. Panel premium tipo WhatsApp (panel_chat.html externo)
  8. Fixes críticos: STOP global, daemon=False, caché CSV, FileLock timeout
"""

import os, json, csv, time, random, logging, threading
from flask import Flask, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TorreControl")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN
# ══════════════════════════════════════════════════════════════
TZ_LIMA   = timezone(timedelta(hours=-5))
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = "/data" if os.path.exists("/data") else BASE_DIR

def ahora_lima():
    return datetime.now(TZ_LIMA)

# Staff de coordinadoras — base de asignación
STAFF = {
    "jmarin":   {"nombre": "Joyce Marín",   "tel": "51933599903"},
    "lpasquel": {"nombre": "Leyla Pasquel", "tel": "51919502385"},
    "zurteaga": {"nombre": "Zuley Urteaga", "tel": "51933599864"},
    "dmoscoso": {"nombre": "Diana Moscoso", "tel": "51912379744"},
    "lvalencia":{"nombre": "Linid Valencia","tel": "51912379686"},
}
GERENTE_TEL = "51912379744"  # Diana — receptor de alertas críticas

# Contadores de carga activa por coordinadora (en memoria, se resetea al reiniciar)
_carga_cc = {k: 0 for k in STAFF}
_carga_lock = threading.Lock()

def cc_menos_cargado():
    """Devuelve la key del staff con menos casos activos."""
    with _carga_lock:
        return min(_carga_cc, key=_carga_cc.get)

def incrementar_carga(staff_key):
    with _carga_lock:
        if staff_key in _carga_cc:
            _carga_cc[staff_key] += 1

def decrementar_carga(staff_key):
    with _carga_lock:
        if staff_key in _carga_cc and _carga_cc[staff_key] > 0:
            _carga_cc[staff_key] -= 1

class Config:
    TOKEN        = os.environ.get("WA_TOKEN", "")
    PHONE_ID     = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")

    # CSVs — el principal viene de GitHub (Asignacion C1)
    CSV_ASIGNACION = os.path.join(BASE_DIR, "Asignacion_C1.xlsx - Hoja1.csv")
    CSV_PROSPECTOS = os.path.join(BASE_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")

    # Persistencia
    SESSIONS_PATH  = os.path.join(DATA_DIR, "sesiones.json")
    SESSIONS_SIM   = os.path.join(DATA_DIR, "sesiones_sim.json")
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    LOCK_TIMEOUT   = 5

    # Make.com → Google Sheets
    URL_SHEETS = "https://hook.us2.make.com/ii4ut5wjlg1khsaes20coa7cgiom13n6"

    # Fechas activas C1 E27
    C1_E27_FECHA   = "Viernes 1, Sábado 2 y Domingo 3 de mayo de 2026"
    C1_E27_LUGAR   = "Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores"
    C1_E27_REGISTRO= "Viernes 1 de Mayo a las 9:00am (obligatorio)"

FECHAS_TEXTO = (
    "📅 *Próximas Fechas 2026 — Sede Lima*\n\n"
    f"🚀 *C1 Equipo 27:* {Config.C1_E27_FECHA}\n"
    f"   📍 {Config.C1_E27_LUGAR}\n\n"
    "🔥 *C2 Equipo 27:* Jueves 14 de Mayo\n"
    "👑 *MJ Inducción:*  Viernes 17 de Abril (activo)"
)

# ══════════════════════════════════════════════════════════════
# 2. CACHÉ CSV CON MTIME
# ══════════════════════════════════════════════════════════════
_cache: dict = {}      # {"path": (mtime, rows)}
_cache_lock  = threading.Lock()

def get_csv_rows(path):
    """Lee CSV con caché inteligente — solo recarga si el archivo cambió."""
    if not os.path.exists(path):
        return []
    try:
        mtime = os.path.getmtime(path)
        with _cache_lock:
            if path in _cache and _cache[path][0] == mtime:
                return _cache[path][1]
            with open(path, "r", encoding="utf-8-sig") as f:
                primera = f.readline()
                delim   = ";" if primera.count(";") > primera.count(",") else ","
                f.seek(0)
                rows = list(csv.DictReader(f, delimiter=delim))
            _cache[path] = (mtime, rows)
            logger.info(f"CSV recargado: {os.path.basename(path)} — {len(rows)} filas")
            return rows
    except Exception as e:
        logger.error(f"CSV cache error {path}: {e}")
        return []

# ══════════════════════════════════════════════════════════════
# 3. SESIONES Y HISTORIAL
# ══════════════════════════════════════════════════════════════
def _spath(tel):
    return Config.SESSIONS_SIM if str(tel).startswith("SIM_") else Config.SESSIONS_PATH

def get_sesion(tel):
    path = _spath(tel)
    try:
        with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f).get(str(tel), {})
    except FileLockTimeout:
        logger.warning(f"Lock timeout get_sesion {tel}")
    except Exception as e:
        logger.error(f"get_sesion {tel}: {e}")
    return {}

def set_sesion(tel, data):
    path = _spath(tel)
    try:
        with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
            all_s = {}
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    all_s = json.load(f)
            all_s[str(tel)] = data
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_s, f, ensure_ascii=False, indent=2)
    except FileLockTimeout:
        logger.warning(f"Lock timeout set_sesion {tel}")
    except Exception as e:
        logger.error(f"set_sesion {tel}: {e}")

def borrar_sesion(tel):
    path = _spath(tel)
    try:
        with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    all_s = json.load(f)
                all_s.pop(str(tel), None)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(all_s, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def append_historial(tel, nombre, texto, tipo):
    path = Config.HISTORIAL_PATH
    try:
        with FileLock(path + ".lock", timeout=Config.LOCK_TIMEOUT):
            h = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    h = json.load(f)
            h.append({
                "telefono": str(tel),
                "nombre":   nombre or "Desconocido",
                "texto":    texto,
                "tipo":     tipo,
                "hora":     ahora_lima().strftime("%d/%m %H:%M"),
            })
            if len(h) > 5000:
                h = h[-5000:]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"historial error: {e}")

# ══════════════════════════════════════════════════════════════
# 4. CRM — IDENTIFICACIÓN DE PERFILES
# ══════════════════════════════════════════════════════════════
def _norm9(t):
    """Últimos 9 dígitos del teléfono para comparación."""
    return re_solo_digitos(str(t))[-9:]

import re as _re
def re_solo_digitos(s):
    return _re.sub(r'\D', '', str(s))

def nombre_pila(s):
    partes = [p for p in str(s).strip().split() if len(p) > 2]
    return partes[0].title() if partes else str(s).strip().title()

def obtener_perfil_crm(tel):
    """
    Perfil completo del contacto cruzando ambos CSVs.
    Retorna dict con:
      tipo: IMO_GRADUADO | IMO | PX | NUEVO
      nombre, dni, nombre_completo
      staff_key, staff_tel, staff_nom  (coordinadora asignada)
      pendientes_c1: lista de nombres completos (para IMOs)
      es_graduado_mj: bool
    """
    tel9 = _norm9(tel)

    perfil = {
        "tipo":           "NUEVO",
        "nombre":         None,
        "nombre_completo":"",
        "dni":            "",
        "staff_key":      None,
        "staff_tel":      None,
        "staff_nom":      None,
        "pendientes_c1":  [],
        "es_graduado_mj": False,
        "imo_nombre":     "",
    }

    # ── CSV ASIGNACION (fuente principal) ─────────────────────
    rows_asig = get_csv_rows(Config.CSV_ASIGNACION)
    pendientes_set = set()

    for row in rows_asig:
        tel_px  = _norm9(row.get("TelefonoMovil", ""))
        tel_imo = _norm9(row.get("IdentificacionIMO", ""))  # puede ser DNI o tel
        nombre  = str(row.get("NombreCompleto","")).strip()
        apellido= str(row.get("ApellidoCompleto","")).strip()
        usuario = str(row.get("Usuario Registro","")).strip().lower()
        dni     = str(row.get("Identificación","")).strip()
        nombre_c= f"{nombre} {apellido}".strip()

        # Es PX
        if tel_px and tel_px == tel9:
            perfil["tipo"]           = "PX"
            perfil["nombre"]         = nombre_pila(nombre)
            perfil["nombre_completo"]= nombre_c
            perfil["dni"]            = dni
            if usuario in STAFF:
                perfil["staff_key"] = usuario
                perfil["staff_tel"] = STAFF[usuario]["tel"]
                perfil["staff_nom"] = STAFF[usuario]["nombre"]

        # Es IMO — buscar por teléfono en Tel.IMO del CSV prospectos
    # ── CSV PROSPECTOS (fuente secundaria para IMOs) ──────────
    rows_px = get_csv_rows(Config.CSV_PROSPECTOS)
    for row in rows_px:
        tel_imo_raw = re_solo_digitos(str(row.get("Tel. IMO","")))[-9:]
        if tel_imo_raw and tel_imo_raw == tel9:
            # Es IMO
            if perfil["tipo"] not in ("IMO","IMO_GRADUADO"):
                perfil["tipo"]       = "IMO"
                perfil["nombre"]     = nombre_pila(row.get("IMO",""))
                perfil["imo_nombre"] = str(row.get("IMO","")).strip()
            # Agregar enrolado pendiente
            nom_px  = str(row.get("Nombre","")).strip()
            ape_px  = str(row.get("Apellido","")).strip()
            eq_px   = str(row.get("Equipo","")).strip()
            nombre_px_c = f"{nom_px} {ape_px}".strip().title()
            if nombre_px_c and nombre_px_c not in pendientes_set:
                pendientes_set.add(nombre_px_c)
                perfil["pendientes_c1"].append(f"• {nombre_px_c} ({eq_px})")

    # ── Si no tiene staff asignado → reparto equitativo ──────
    if perfil["tipo"] in ("IMO","IMO_GRADUADO","PX") and not perfil["staff_key"]:
        key = cc_menos_cargado()
        perfil["staff_key"] = key
        perfil["staff_tel"] = STAFF[key]["tel"]
        perfil["staff_nom"] = STAFF[key]["nombre"]

    return perfil

# ══════════════════════════════════════════════════════════════
# 5. ENVÍO WA Y NOTIFICACIONES
# ══════════════════════════════════════════════════════════════
def enviar_wa(tel, texto, nombre_log="BOT"):
    if str(tel).startswith("SIM_"):
        append_historial(tel, nombre_log, texto, "out")
        return True
    try:
        r = req_lib.post(
            f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages",
            json={
                "messaging_product": "whatsapp",
                "to":   str(tel),
                "type": "text",
                "text": {"body": texto, "preview_url": False},
            },
            headers={"Authorization": f"Bearer {Config.TOKEN}",
                     "Content-Type":  "application/json"},
            timeout=10,
        )
        append_historial(tel, nombre_log, texto, "out")
        if r.status_code != 200:
            logger.error(f"WA {r.status_code}: {r.text[:150]}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"WA exception: {e}")
        return False

def notificar_cc(perfil, motivo, extra=""):
    """Notifica a la coordinadora asignada del perfil."""
    tel_cc  = perfil.get("staff_tel") or STAFF[cc_menos_cargado()]["tel"]
    nom_cc  = perfil.get("staff_nom") or "Coordinación"
    nom_px  = perfil.get("nombre_completo") or perfil.get("nombre") or "Sin nombre"
    tel_px  = perfil.get("_tel_origen", "")
    msg = (
        f"🚨 *TORRE DE CONTROL — CPSL Lima*\n"
        f"*Contacto:* {nom_px}\n"
        f"*Tel:* wa.me/{tel_px}\n"
        f"*DNI:* {perfil.get('dni','S/D')}\n"
        f"*Motivo:* {motivo}"
        + (f"\n*Detalle:* {extra}" if extra else "")
    )
    threading.Thread(
        target=enviar_wa,
        args=(tel_cc, msg, f"SISTEMA→{nom_cc}"),
        daemon=False
    ).start()
    incrementar_carga(perfil.get("staff_key") or cc_menos_cargado())
    return nom_cc

def enviar_make(data: dict):
    """Envía registro a Make.com → Google Sheets (no bloqueante)."""
    if not Config.URL_SHEETS:
        return
    def _post():
        try:
            req_lib.post(Config.URL_SHEETS, json=data, timeout=10)
        except Exception as e:
            logger.error(f"Make.com error: {e}")
    threading.Thread(target=_post, daemon=True).start()

# ══════════════════════════════════════════════════════════════
# 6. FLUJO PRINCIPAL
# ══════════════════════════════════════════════════════════════
STOP_WORDS  = {"STOP","BAJA","DETENER","ALTO","NO MAS MENSAJES","STOPBAJA"}
RESET_WORDS = {"HOLA","BUENAS","MENU","MENÚ","0","INICIO","START","HI","HELLO"}

def flujo_principal(tel, texto):
    try:
        txt_up = str(texto).strip().upper()

        # ── STOP siempre primero ──────────────────────────────
        if txt_up in STOP_WORDS:
            borrar_sesion(tel)
            enviar_wa(tel,
                "Has sido dado de baja. No recibirás más mensajes.\n\n"
                "*Crear Poder Sin Límites Perú*",
                "SISTEMA"
            )
            enviar_make({"telefono": tel, "evento": "STOP", "hora": ahora_lima().isoformat()})
            return

        sesion = get_sesion(tel)

        # ── Reset ─────────────────────────────────────────────
        if not sesion or txt_up in RESET_WORDS:
            perfil = obtener_perfil_crm(tel)
            perfil["_tel_origen"] = tel
            sesion = {"perfil": perfil, "state": "MAIN", "sub": None}
            set_sesion(tel, sesion)
            _enviar_menu_main(tel, perfil)
            return

        perfil = sesion.get("perfil", {})
        perfil["_tel_origen"] = tel
        state  = sesion.get("state", "MAIN")
        sub    = sesion.get("sub")
        tipo   = perfil.get("tipo", "NUEVO")
        nombre = perfil.get("nombre") or "Líder"

        # ── Volver siempre disponible ─────────────────────────
        if txt_up in {"9","VOLVER","BACK"}:
            sesion["state"] = "MAIN"
            sesion["sub"]   = None
            set_sesion(tel, sesion)
            _enviar_menu_main(tel, perfil)
            return

        # ── Estado DERIVADO: reenviar mensajes a la CC ────────
        if state == "DERIVADO":
            tel_cc = perfil.get("staff_tel") or STAFF[cc_menos_cargado()]["tel"]
            nom_cc = perfil.get("staff_nom") or "Coordinación"
            nom_px = perfil.get("nombre_completo") or nombre
            enviar_wa(tel_cc,
                f"💬 *Mensaje de {nom_px}* (wa.me/{tel}):\n\n{texto}",
                f"RELAY→{nom_cc}"
            )
            enviar_wa(tel,
                "✅ Tu mensaje fue entregado a tu coordinadora. Te responderán pronto.\n"
                "_Escribe *0* para volver al menú._",
                nombre
            )
            return

        # ── Rutear por tipo ───────────────────────────────────
        if tipo in ("IMO","IMO_GRADUADO"):
            _flujo_imo(tel, txt_up, texto, sesion, perfil)
        elif tipo == "PX":
            _flujo_px(tel, txt_up, texto, sesion, perfil)
        else:
            _flujo_nuevo(tel, txt_up, texto, sesion, perfil)

    except Exception as e:
        logger.error(f"flujo_principal {tel}: {e}", exc_info=True)


def _enviar_menu_main(tel, perfil):
    tipo   = perfil.get("tipo","NUEVO")
    nombre = perfil.get("nombre") or "Líder"

    if tipo in ("IMO","IMO_GRADUADO"):
        n_pend = len(perfil.get("pendientes_c1",[]))
        es_grad = perfil.get("es_graduado_mj", False)
        nivel   = "Graduado MJ 🎓" if es_grad else "Líder IMO 👑"
        alerta  = f"\n⚠️ Tienes *{n_pend}* enrolado{'s' if n_pend!=1 else ''} pendiente{'s' if n_pend!=1 else ''} de C1." if n_pend else "\n✅ Todos tus enrolados están al día."
        msg = (
            f"🌟 *Torre de Control — {nivel}*\n"
            f"Hola *{nombre}*{alerta}\n\n"
            f"1️⃣ Ver mis enrolados pendientes de C1\n"
            f"2️⃣ Ver TODOS mis enrolados\n"
            f"3️⃣ Solicitar ser Aliado C1 E27\n"
            f"4️⃣ Fechas próximas activas\n"
            f"5️⃣ Hablar con Coordinación\n"
            f"0️⃣ Salir\n\n"
            f"_Responde STOP para darte de baja._"
        )

    elif tipo == "PX":
        nom_cc = perfil.get("staff_nom","Coordinación")
        msg = (
            f"🌟 *Hola {nombre}!*\n"
            f"Bienvenido al portal de Crear Poder Sin Límites Perú.\n"
            f"Tu coordinadora: *{nom_cc}*\n\n"
            f"1️⃣ Confirmar asistencia al C1 Equipo 27\n"
            f"2️⃣ Ver fechas y logística\n"
            f"3️⃣ Inversión y pagos\n"
            f"4️⃣ Tengo una pregunta / Coordinación\n"
            f"0️⃣ Salir\n\n"
            f"_Responde STOP para darte de baja._"
        )

    else:  # NUEVO
        msg = (
            f"🌟 *Bienvenido a Crear Poder Sin Límites Perú*\n"
            f"Canal Corporativo Oficial — Sede Lima.\n\n"
            f"Para darte la mejor atención necesito conocerte:\n\n"
            f"1️⃣ Ya he participado en un entrenamiento (cambié de número)\n"
            f"2️⃣ Soy nuevo — quiero información\n"
            f"0️⃣ Salir\n\n"
            f"_Responde STOP para darte de baja._"
        )

    enviar_wa(tel, msg, nombre)


# ── FLUJO IMO ─────────────────────────────────────────────────
def _flujo_imo(tel, txt_up, texto, sesion, perfil):
    nombre  = perfil.get("nombre") or "Líder"
    nom_cc  = perfil.get("staff_nom") or "Coordinación"
    pend    = perfil.get("pendientes_c1",[])
    state   = sesion.get("state","MAIN")

    if state == "MAIN":
        if txt_up == "1":
            if pend:
                lista = "\n".join(pend[:20])
                if len(pend) > 20: lista += f"\n_...y {len(pend)-20} más_"
                msg = (
                    f"⏳ *Pendientes de C1 — Equipo 27*\n"
                    f"📅 {Config.C1_E27_FECHA}\n"
                    f"📍 {Config.C1_E27_LUGAR}\n\n"
                    f"{lista}\n\n"
                    f"¿Cómo avanzan tus gestiones?\n"
                    f"1️⃣ Uno o más confirman\n"
                    f"2️⃣ Sigo gestionando\n"
                    f"3️⃣ Necesito apoyo de Coordinación\n"
                    f"9️⃣ Volver"
                )
                sesion["state"] = "IMO_PENDIENTES"
            else:
                msg = "🎉 ¡Todos tus enrolados ya se sentaron! Felicitaciones.\n\n9️⃣ Volver"
            set_sesion(tel, sesion)
            enviar_wa(tel, msg, nombre)

        elif txt_up == "2":
            rows_px = get_csv_rows(Config.CSV_PROSPECTOS)
            tel9    = re_solo_digitos(tel)[-9:]
            todos   = []
            for r in rows_px:
                t_imo = re_solo_digitos(str(r.get("Tel. IMO","")))[-9:]
                if t_imo == tel9:
                    n  = f"{r.get('Nombre','').strip()} {r.get('Apellido','').strip()}".title()
                    eq = r.get("Equipo","")
                    c1 = str(r.get("C1","")).strip().upper()
                    st = "✅ Sentado" if c1 == "SI" else "⏳ Pendiente"
                    todos.append(f"• {n} ({eq}) — {st}")
            if todos:
                lista = "\n".join(todos[:25])
                if len(todos) > 25: lista += f"\n_...y {len(todos)-25} más_"
                msg = f"📋 *Todos tus enrolados:*\n\n{lista}\n\n9️⃣ Volver"
            else:
                msg = "Sin registros vinculados a tu número en el sistema.\n\n9️⃣ Volver"
            enviar_wa(tel, msg, nombre)

        elif txt_up == "3":
            # Solicitar ser Aliado C1 E27
            nom_cc_notif = notificar_cc(perfil,
                "Solicita ser Aliado para C1 E27",
                f"IMO: {perfil.get('imo_nombre',nombre)} — {len(pend)} pendientes"
            )
            enviar_wa(tel,
                f"✅ Solicitud registrada.\n\n"
                f"Tu coordinadora *{nom_cc_notif}* te escribirá para confirmar tu rol como Aliado en el C1 Equipo 27.\n\n"
                f"*Crea Poder Sin Límites Perú* 💪\n\n9️⃣ Volver",
                nombre
            )
            enviar_make({
                "telefono": tel, "nombre": nombre,
                "dni": perfil.get("dni",""),
                "evento": "SOLICITUD_ALIADO_C1E27",
                "staff": nom_cc_notif,
                "hora":  ahora_lima().isoformat()
            })

        elif txt_up == "4":
            enviar_wa(tel, FECHAS_TEXTO + "\n\n9️⃣ Volver", nombre)

        elif txt_up == "5":
            nom_cc_notif = notificar_cc(perfil, "IMO solicita atención directa de Coordinación")
            sesion["state"] = "DERIVADO"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Derivado a *{nom_cc_notif}*. Te atenderán aquí mismo.\n"
                f"Puedes escribir tu consulta directamente y llegará a tu coordinadora.",
                nombre
            )

        elif txt_up == "0":
            borrar_sesion(tel)
            enviar_wa(tel, "Hasta pronto. Escribe HOLA para reiniciar. 🌟", nombre)
        else:
            _enviar_menu_main(tel, perfil)

    elif state == "IMO_PENDIENTES":
        if txt_up == "1":
            sesion["state"] = "IMO_CAPTURANDO_CONF"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                "¡Excelente! ✅\nEscribe el nombre de quien confirma (uno por mensaje). "
                "Lo registraremos y avisaremos a Coordinación.\n\n_Escribe 9 para volver._",
                nombre
            )
        elif txt_up == "2":
            sesion["state"] = "MAIN"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                "Perfecto. Tu acompañamiento es lo que hace posible la decisión de tu gente. 💪\n\n"
                "Cuando tengas confirmaciones escríbenos. 9️⃣ Volver / 0️⃣ Menú",
                nombre
            )
        elif txt_up == "3":
            nom_cc_notif = notificar_cc(perfil,
                "IMO necesita apoyo para gestionar pendientes C1 E27",
                f"{len(pend)} pendientes"
            )
            sesion["state"] = "DERIVADO"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Derivado. *{nom_cc_notif}* te apoyará directamente.",
                nombre
            )
        else:
            sesion["state"] = "MAIN"
            set_sesion(tel, sesion)
            _enviar_menu_main(tel, perfil)

    elif state == "IMO_CAPTURANDO_CONF":
        # Captura nombre del PX que confirma
        nom_cc_notif = notificar_cc(perfil,
            f"IMO reporta CONFIRMACIÓN de enrolado",
            f"Nombre confirmado: '{texto}'"
        )
        enviar_make({
            "telefono": tel, "nombre": nombre,
            "dni": perfil.get("dni",""),
            "evento": "IMO_CONFIRMA_ENROLADO",
            "detalle": texto,
            "staff": nom_cc_notif,
            "hora":  ahora_lima().isoformat()
        })
        enviar_wa(tel,
            f"✅ *{texto}* registrado como confirmado.\n"
            f"Coordinación ({nom_cc_notif}) lo procesará en el sistema.\n\n"
            f"¿Tienes otra confirmación? Escribe el nombre o *9* para volver.",
            nombre
        )


# ── FLUJO PX ──────────────────────────────────────────────────
def _flujo_px(tel, txt_up, texto, sesion, perfil):
    nombre  = perfil.get("nombre") or "Líder"
    nom_cc  = perfil.get("staff_nom") or "Coordinación"
    state   = sesion.get("state","MAIN")

    if state == "MAIN":
        if txt_up == "1":
            # Confirmar asistencia C1 E27
            nom_cc_notif = notificar_cc(perfil,
                "PX CONFIRMA asistencia C1 E27",
                f"DNI: {perfil.get('dni','S/D')}"
            )
            enviar_make({
                "telefono": tel,
                "nombre":   perfil.get("nombre_completo") or nombre,
                "dni":      perfil.get("dni",""),
                "evento":   "PX_CONFIRMA_C1E27",
                "staff":    nom_cc_notif,
                "hora":     ahora_lima().isoformat()
            })
            enviar_wa(tel,
                f"¡Confirmado {nombre}! ✅\n\n"
                f"📍 *{Config.C1_E27_LUGAR}*\n"
                f"🗓 {Config.C1_E27_FECHA}\n"
                f"⏰ Registro: {Config.C1_E27_REGISTRO}\n\n"
                f"Ropa cómoda y botella de agua. Bloquea tu agenda los 3 días.\n\n"
                f"Tu coordinadora *{nom_cc_notif}* recibirá tu confirmación ahora mismo. 💪\n\n"
                f"_Escribe 0 para volver al menú._",
                nombre
            )

        elif txt_up == "2":
            enviar_wa(tel, FECHAS_TEXTO + "\n\n9️⃣ Volver", nombre)

        elif txt_up == "3":
            enviar_wa(tel,
                "💳 *Inversión y Pagos*\n\n"
                "BCP — Cuenta Soles:\n"
                "*1934218307060*\n"
                "A nombre de: Creación Cuántica E.I.R.L.\n\n"
                "1️⃣ Enviar voucher a Coordinación\n9️⃣ Volver",
                nombre
            )
            sesion["state"] = "PX_PAGOS"
            set_sesion(tel, sesion)

        elif txt_up == "4":
            nom_cc_notif = notificar_cc(perfil, "PX solicita atención directa")
            sesion["state"] = "DERIVADO"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Derivando con *{nom_cc_notif}*. "
                f"Puedes escribir tu consulta y llegará directamente a tu coordinadora.",
                nombre
            )

        elif txt_up == "0":
            borrar_sesion(tel)
            enviar_wa(tel, "Hasta pronto. Escribe HOLA para reiniciar. 🌟", nombre)
        else:
            _enviar_menu_main(tel, perfil)

    elif state == "PX_PAGOS":
        if txt_up == "1":
            nom_cc_notif = notificar_cc(perfil, "PX envía voucher de pago")
            sesion["state"] = "DERIVADO"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Enviando a tu coordinadora *{nom_cc_notif}*. "
                f"Por favor adjunta el voucher en el siguiente mensaje.",
                nombre
            )
        else:
            sesion["state"] = "MAIN"
            set_sesion(tel, sesion)
            _enviar_menu_main(tel, perfil)


# ── FLUJO NUEVO ───────────────────────────────────────────────
def _flujo_nuevo(tel, txt_up, texto, sesion, perfil):
    state = sesion.get("state","MAIN")

    if state == "MAIN":
        if txt_up == "1":
            # Cambió de número — perfilamiento
            sesion["state"] = "NUEVO_CAMBIO_NUM"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                "Entendido. Para encontrar tu registro necesito:\n\n"
                "*¿Cuál es tu nombre completo y DNI?*\n"
                "(Escríbelos en un solo mensaje, ejemplo: Juan Pérez 12345678)\n\n"
                "_Escribe 9 para volver._",
                "SISTEMA"
            )

        elif txt_up == "2":
            sesion["state"] = "NUEVO_INFO"
            set_sesion(tel, sesion)
            enviar_wa(tel,
                "🌟 *Crear Poder Sin Límites Perú*\n\n"
                "Somos un centro de entrenamiento de liderazgo y transformación "
                "de alto rendimiento. Te ayudamos a salir del modo automático "
                "y crear resultados extraordinarios en tu vida.\n\n"
                "1️⃣ Información del Capítulo 1 (C1)\n"
                "2️⃣ Ver fechas 2026\n"
                "3️⃣ Inversión\n"
                "4️⃣ Hablar con Coordinación\n"
                "9️⃣ Volver",
                "SISTEMA"
            )

        elif txt_up == "0":
            borrar_sesion(tel)
            enviar_wa(tel, "Hasta pronto. Escribe HOLA cuando quieras. 🌟", "SISTEMA")
        else:
            _enviar_menu_main(tel, perfil)

    elif state == "NUEVO_CAMBIO_NUM":
        # Buscar en CSV por nombre/DNI
        texto_clean = texto.strip()
        # Notificar a Coordinación para que verifique manualmente
        key = cc_menos_cargado()
        tel_cc = STAFF[key]["tel"]
        nom_cc = STAFF[key]["nombre"]
        incrementar_carga(key)
        enviar_wa(tel_cc,
            f"🔍 *VERIFICACIÓN DE IDENTIDAD*\n"
            f"Tel: wa.me/{tel}\n"
            f"Dato proporcionado: '{texto_clean}'\n"
            f"Buscar en sistema y actualizar registro.",
            f"SISTEMA→{nom_cc}"
        )
        sesion["state"] = "DERIVADO"
        perfil["staff_key"] = key
        perfil["staff_tel"] = tel_cc
        perfil["staff_nom"] = nom_cc
        sesion["perfil"] = perfil
        set_sesion(tel, sesion)
        enviar_wa(tel,
            f"✅ Recibido. Hemos enviado tu información a Coordinación ({nom_cc}) "
            f"para actualizar tu registro. Te responderán pronto por aquí.",
            "SISTEMA"
        )
        enviar_make({
            "telefono": tel, "nombre": texto_clean,
            "evento": "NUEVO_CAMBIO_NUMERO",
            "staff": nom_cc, "hora": ahora_lima().isoformat()
        })

    elif state == "NUEVO_INFO":
        if txt_up == "1":
            enviar_wa(tel,
                "🚀 *Capítulo 1 — El Descubrimiento*\n\n"
                "3 días vivenciales para observar los mecanismos automáticos "
                "que frenan tus resultados. No es una conferencia — es una "
                "experiencia de transformación profunda.\n\n"
                f"*Próxima fecha:* {Config.C1_E27_FECHA}\n"
                f"*Lugar:* {Config.C1_E27_LUGAR}\n\n"
                "1️⃣ Quiero inscribirme\n9️⃣ Volver",
                "SISTEMA"
            )
            sesion["state"] = "NUEVO_INFO_C1"
            set_sesion(tel, sesion)
        elif txt_up == "2":
            enviar_wa(tel, FECHAS_TEXTO + "\n\n9️⃣ Volver", "SISTEMA")
        elif txt_up == "3":
            enviar_wa(tel,
                "💳 *Inversión*\n\n"
                "El costo del Capítulo 1 es confidencial y personalizado. "
                "Tu coordinadora te dará todos los detalles.\n\n"
                "1️⃣ Contactar Coordinación\n9️⃣ Volver",
                "SISTEMA"
            )
            sesion["state"] = "NUEVO_INFO_INV"
            set_sesion(tel, sesion)
        elif txt_up == "4":
            key    = cc_menos_cargado()
            tel_cc = STAFF[key]["tel"]
            nom_cc = STAFF[key]["nombre"]
            incrementar_carga(key)
            enviar_wa(tel_cc,
                f"🆕 *NUEVO PROSPECTO*\nTel: wa.me/{tel}\nSolicita información general.",
                f"SISTEMA→{nom_cc}"
            )
            sesion["state"] = "DERIVADO"
            perfil["staff_key"] = key
            perfil["staff_tel"] = tel_cc
            perfil["staff_nom"] = nom_cc
            sesion["perfil"] = perfil
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Derivado a Coordinación ({nom_cc}). Te escribirán pronto.",
                "SISTEMA"
            )
        elif txt_up == "9":
            sesion["state"] = "MAIN"
            set_sesion(tel, sesion)
            _enviar_menu_main(tel, perfil)

    elif state in ("NUEVO_INFO_C1","NUEVO_INFO_INV"):
        if txt_up == "1":
            key    = cc_menos_cargado()
            tel_cc = STAFF[key]["tel"]
            nom_cc = STAFF[key]["nombre"]
            incrementar_carga(key)
            enviar_wa(tel_cc,
                f"🆕 *NUEVO PROSPECTO INTERESADO*\nTel: wa.me/{tel}\n"
                f"Interés: {'C1' if state == 'NUEVO_INFO_C1' else 'Inversión'}",
                f"SISTEMA→{nom_cc}"
            )
            sesion["state"] = "DERIVADO"
            perfil["staff_key"] = key
            perfil["staff_tel"] = tel_cc
            perfil["staff_nom"] = nom_cc
            sesion["perfil"] = perfil
            set_sesion(tel, sesion)
            enviar_wa(tel,
                f"✅ Coordinación ({nom_cc}) te escribirá en breve. 🌟",
                "SISTEMA"
            )
        elif txt_up == "9":
            sesion["state"] = "NUEVO_INFO"
            set_sesion(tel, sesion)
            # Re-enviar menú info
            enviar_wa(tel,
                "1️⃣ Info C1\n2️⃣ Fechas\n3️⃣ Inversión\n4️⃣ Coordinación\n9️⃣ Volver",
                "SISTEMA"
            )


# ══════════════════════════════════════════════════════════════
# 7. ENDPOINTS FLASK
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode      = request.args.get("hub.mode")
    token     = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == Config.VERIFY_TOKEN:
        logger.info("Webhook verificado OK")
        return challenge, 200
    return "Token inválido", 403

@app.route("/webhook", methods=["POST"])
def recv_webhook():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status":"ok"}), 200
    try:
        changes  = data["entry"][0]["changes"][0]["value"]
        if "messages" not in changes:
            return jsonify({"status":"ok"}), 200
        msg      = changes["messages"][0]
        tel      = msg.get("from","")
        tipo_msg = msg.get("type","")

        if tipo_msg == "text":
            texto = str(msg["text"]["body"])
            append_historial(tel, "ENTRADA", texto, "in")
            enviar_make({
                "telefono": tel,
                "mensaje":  texto,
                "evento":   "MENSAJE_ENTRANTE",
                "hora":     ahora_lima().isoformat()
            })
            threading.Thread(
                target=flujo_principal,
                args=(tel, texto),
                daemon=False,
                name=f"flujo-{tel[-4:]}",
            ).start()

        elif tipo_msg in ("audio","image","document","video","sticker"):
            append_historial(tel, "ENTRADA", f"[{tipo_msg.upper()}]", "in")
            enviar_wa(tel,
                "Por favor responde con texto o el número de tu opción. "
                "No procesamos archivos en este canal.",
                "SISTEMA"
            )
    except Exception as e:
        logger.error(f"webhook error: {e}", exc_info=True)
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH,"r",encoding="utf-8") as f:
                return jsonify(json.load(f)), 200
    except Exception:
        pass
    return jsonify([]), 200

@app.route("/api/historial/<tel>")
def api_historial_tel(tel):
    """Historial filtrado por teléfono — para el panel por persona."""
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH,"r",encoding="utf-8") as f:
                h = json.load(f)
            filtrado = [m for m in h if str(m.get("telefono","")) == str(tel)]
            return jsonify(filtrado), 200
    except Exception:
        pass
    return jsonify([]), 200

@app.route("/api/carga_coordinadoras")
def api_carga():
    """Estado de carga de coordinadoras para el dashboard."""
    resultado = {}
    for key, datos in STAFF.items():
        resultado[key] = {
            "nombre": datos["nombre"],
            "casos_activos": _carga_cc.get(key, 0),
            "tel": datos["tel"],
        }
    return jsonify(resultado), 200

@app.route("/api/enviar", methods=["POST"])
def api_enviar():
    """Envío manual desde el panel — Nuevo Chat real."""
    d   = request.json or {}
    tel = d.get("telefono","").strip()
    msg = d.get("mensaje","").strip()
    if not tel or not msg:
        return jsonify({"error":"Faltan datos"}), 400
    enviar_wa(tel, msg, "PANEL")
    enviar_make({
        "telefono": tel, "mensaje": msg,
        "evento": "ENVIO_MANUAL_PANEL",
        "hora":   ahora_lima().isoformat()
    })
    return jsonify({"status":"ok"}), 200

@app.route("/api/mensaje_simulador", methods=["POST"])
def api_simulador():
    d   = request.json or {}
    tel = d.get("telefono","")
    txt = d.get("texto","")
    if not tel or not txt:
        return jsonify({"error":"Faltan datos"}), 400
    append_historial(tel, "SIMULACIÓN", txt, "in")
    threading.Thread(
        target=flujo_principal,
        args=(tel, txt),
        daemon=True,
        name=f"sim-{tel[-4:]}",
    ).start()
    return jsonify({"status":"ok"}), 200

@app.route("/status")
def status():
    return jsonify({
        "status":  "activo",
        "version": "v108",
        "sede":    "Lima",
        "hora":    ahora_lima().strftime("%d/%m/%Y %H:%M:%S"),
        "csv_asignacion": len(get_csv_rows(Config.CSV_ASIGNACION)),
        "csv_prospectos": len(get_csv_rows(Config.CSV_PROSPECTOS)),
        "carga_cc": {k: v for k,v in _carga_cc.items()},
        "c1_e27":  Config.C1_E27_FECHA,
    }), 200

@app.route("/chat")
def panel():
    try:
        with open(os.path.join(BASE_DIR, "panel_chat.html"), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h2>Panel no disponible — sube panel_chat.html</h2>", 200

if __name__ == "__main__":
    logger.info("🚀 Torre de Control V108 — CPSL Lima")
    logger.info(f"   CSV Asignación : {Config.CSV_ASIGNACION}")
    logger.info(f"   CSV Prospectos : {Config.CSV_PROSPECTOS}")
    logger.info(f"   Make.com       : {Config.URL_SHEETS}")
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        debug=False
    )
