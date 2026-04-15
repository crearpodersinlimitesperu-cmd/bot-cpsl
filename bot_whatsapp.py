"""
Bot WhatsApp — Crear Poder Sin Límites Perú
V109: Routing correcto desde un solo CSV
      PX  → identificado por columna Teléfono
      IMO → identificado por columna Tel. IMO
      NUEVO → no está en ninguna de las dos
      Prioridad: si es IMO Y PX → IMO gana
"""

import os, re, json, time, csv, base64, random, logging, threading, queue
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CPSL")
app    = Flask(__name__)

# ── ZONA HORARIA ─────────────────────────────────────────────
TZ_LIMA  = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR
def ahora(): return datetime.now(TZ_LIMA)

# ── STAFF ────────────────────────────────────────────────────
STAFF = {
    "dmoscoso":  {"nombre": "Diana Moscoso",  "tel": "51912379744"},
    "jmarin":    {"nombre": "Joyce Marín",    "tel": "51933599903"},
    "lpasquel":  {"nombre": "Leyla Pasquel",  "tel": "51919502385"},
    "zurteaga":  {"nombre": "Zuley Urteaga",  "tel": "51933599864"},
    "lvalencia": {"nombre": "Linid Valencia", "tel": "51912379686"},
}
_carga    = {k: 0 for k in STAFF}
_carga_lk = threading.Lock()

def cc_libre():
    with _carga_lk:
        return min(_carga, key=_carga.get)

def cc_add(k):
    with _carga_lk:
        if k in _carga: _carga[k] += 1

# Mapa fijo equipo → coordinadora (basado en archivos de aliados reales)
_CC_POR_EQUIPO = {
    "EQUIPO 26": "dmoscoso",   # Diana Moscoso
    "EQUIPO 25": "jmarin",     # Joyce Marín
    "EQUIPO 24": "zurteaga",   # Zuley Urteaga
    "EQUIPO 23": "zurteaga",
    "EQUIPO 22": "lpasquel",   # Leyla Pasquel
    "EQUIPO 21": "lpasquel",
    "EQUIPO 20": "lpasquel",
    "EQUIPO 19": "lvalencia",  # Linid Valencia
    "EQUIPO 18": "lvalencia",
    "EQUIPO 17": "lvalencia",
    "EQUIPO 16": "lvalencia",
    "EQUIPO 15": "lvalencia",
    "EQUIPO 14": "lvalencia",
}

def cc_por_equipo(equipo):
    """Retorna la key del staff asignado al equipo. Fallback: cc_libre()."""
    return _CC_POR_EQUIPO.get(str(equipo).strip().upper(), cc_libre())

# ── CONFIG ────────────────────────────────────────────────────
class Cfg:
    TOKEN     = os.environ.get("WA_TOKEN","")
    PHONE_ID  = os.environ.get("WA_PHONE_ID","")
    VER_TOKEN = os.environ.get("WA_VERIFY_TOKEN","cpsl2026")
    SHEET_ID  = os.environ.get("SHEET_ID","")
    CREDS     = os.environ.get("GOOGLE_CREDENTIALS","")
    SHEET_TAB = os.environ.get("SHEET_TAB","Hoja 1")
    LOCK_T    = 5

    # CSV único — nombre exacto como está en GitHub
    CSV = os.path.join(BASE_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")

    # Rutas de persistencia
    S_REAL = os.path.join(DATA_DIR, "sesiones.json")
    S_SIM  = os.path.join(DATA_DIR, "sesiones_sim.json")
    HIST      = os.path.join(DATA_DIR, "historial_chat.json")  # mismo nombre que versiones anteriores
    HIST_ALT  = os.path.join(DATA_DIR, "historial.json")          # fallback versiones nuevas

    # Evento C1 E27
    FECHA   = "Viernes 1, Sábado 2 y Domingo 3 de mayo de 2026"
    LUGAR   = "Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores"
    REGISTRO= "Viernes 1 de mayo a las 9:00am (obligatorio)"

FECHAS_MSG = (
    "📅 *Próximas Fechas — Sede Lima 2026*\n\n"
    f"🚀 *C1 Equipo 27:* {Cfg.FECHA}\n"
    f"   📍 {Cfg.LUGAR}\n\n"
    "🔥 *C2 Equipo 27:* Jueves 14 de mayo\n"
    "👑 *MJ Inducción:* Viernes 17 de abril"
)

# ── CACHÉ CSV ─────────────────────────────────────────────────
_csv_cache    = None
_csv_mtime    = 0.0
_csv_lk       = threading.Lock()

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
            _csv_cache, _csv_mtime = rows, mt
            logger.info(f"CSV cargado: {len(rows)} filas")
            return rows
    except Exception as e:
        logger.error(f"CSV error: {e}")
        return []

# ── NORMALIZACIÓN ─────────────────────────────────────────────
def _d(s): return re.sub(r'\D','',str(s or ''))
def n9(t):  return _d(t)[-9:]
def np(s):  # primer nombre
    """CSV de IMOs tiene formato APELLIDO1 APELLIDO2 NOMBRE → tomar 3er token."""
    p = [x for x in str(s or '').strip().split() if len(x)>2]
    if not p: return str(s).strip().title()
    if len(p) >= 3: return p[2].title()   # APELLIDO1 APELLIDO2 NOMBRE → NOMBRE
    if len(p) == 2: return p[1].title()   # APELLIDO NOMBRE → NOMBRE
    return p[0].title()

# ── PERFIL CRM ────────────────────────────────────────────────
def perfil_crm(tel):
    """
    Retorna dict con tipo: IMO | PX | NUEVO
    Prioridad: si aparece como Tel.IMO → IMO (tiene enrolados pendientes)
               si aparece como Teléfono → PX
               si no aparece → NUEVO
    """
    t9    = n9(tel)
    rows  = _get_rows()
    p = {
        "tipo":       "NUEVO",
        "nombre":     None,
        "apellido":   "",
        "nombre_full":"",
        "equipo":     "",
        "imo_nombre": "",
        "imo_tel":    "",
        "staff_key":  None,
        "staff_tel":  None,
        "staff_nom":  None,
        "pendientes": [],   # lista de PX pendientes (para IMOs)
    }

    px_row  = None
    imo_rows = []

    for r in rows:
        if n9(r.get("Teléfono","")) == t9:
            px_row = r
        if n9(r.get("Tel. IMO","")) == t9 and n9(r.get("Tel. IMO","")):
            imo_rows.append(r)

    # ── IMO tiene prioridad ───────────────────────────────────
    if imo_rows:
        p["tipo"]       = "IMO"
        p["nombre"]     = np(imo_rows[0].get("IMO",""))
        p["imo_nombre"] = str(imo_rows[0].get("IMO","")).strip()
        p["pendientes"] = [
            f"• {r.get('Nombre','').strip().title()} "
            f"{r.get('Apellido','').strip().title()} "
            f"({r.get('Equipo','')})"
            for r in imo_rows
        ]

    # ── PX ────────────────────────────────────────────────────
    elif px_row:
        p["tipo"]       = "PX"
        p["nombre"]     = np(px_row.get("Nombre",""))
        p["apellido"]   = px_row.get("Apellido","").strip().title()
        p["nombre_full"]= f"{p['nombre']} {p['apellido']}".strip()
        p["equipo"]     = px_row.get("Equipo","")
        p["imo_nombre"] = px_row.get("IMO","").strip()
        p["imo_tel"]    = _d(px_row.get("Tel. IMO",""))

    # ── Asignar coordinadora por equipo (mapa fijo)
    # Para PX: usar su equipo directo
    # Para IMO: usar el equipo más reciente de sus enrolados
    if p["tipo"] == "PX":
        k = cc_por_equipo(p.get("equipo",""))
    elif p["tipo"] == "IMO":
        # Tomar el equipo con número más alto de sus enrolados
        equipos = [r.get("Equipo","") for r in imo_rows] if imo_rows else []
        import re as _re2
        nums = [int(m.group()) for eq in equipos for m in [_re2.search(r"\d+",eq)] if m]
        eq_top = f"EQUIPO {max(nums)}" if nums else ""
        k = cc_por_equipo(eq_top)
    else:
        k = cc_libre()
    p["staff_key"] = k
    p["staff_tel"] = STAFF[k]["tel"]
    p["staff_nom"] = STAFF[k]["nombre"]
    cc_add(k)

    return p

# ── SESIONES ──────────────────────────────────────────────────
def _sp(tel): return Cfg.S_SIM if str(tel).startswith("SIM_") else Cfg.S_REAL

def get_s(tel):
    path = _sp(tel)
    try:
        with FileLock(path+".lock", timeout=Cfg.LOCK_T):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    return json.load(f).get(str(tel), {})
    except FileLockTimeout: logger.warning(f"lock get {tel}")
    except Exception as e:  logger.error(f"get_s {e}")
    return {}

def set_s(tel, data):
    path = _sp(tel)
    try:
        with FileLock(path+".lock", timeout=Cfg.LOCK_T):
            d = {}
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f: d = json.load(f)
            d[str(tel)] = data
            with open(path,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    except FileLockTimeout: logger.warning(f"lock set {tel}")
    except Exception as e:  logger.error(f"set_s {e}")

def del_s(tel):
    path = _sp(tel)
    try:
        with FileLock(path+".lock", timeout=Cfg.LOCK_T):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f: d = json.load(f)
                d.pop(str(tel), None)
                with open(path,"w",encoding="utf-8") as f: json.dump(d,f,ensure_ascii=False,indent=2)
    except Exception: pass

def add_hist(tel, nom, txt, tipo):
    path = Cfg.HIST
    try:
        with FileLock(path+".lock", timeout=Cfg.LOCK_T):
            h = []
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f: h = json.load(f)
            h.append({"telefono":str(tel),"nombre":nom or "?","texto":txt,
                      "tipo":tipo,"hora":ahora().strftime("%d/%m %H:%M")})
            if len(h)>5000: h=h[-5000:]
            with open(path,"w",encoding="utf-8") as f: json.dump(h,f,ensure_ascii=False,indent=2)
    except Exception as e: logger.error(f"hist {e}")

# ── GOOGLE SHEETS JWT ─────────────────────────────────────────
_stok, _stok_exp = None, 0
_stok_lk = threading.Lock()

def _sheets_tok():
    global _stok, _stok_exp
    with _stok_lk:
        if _stok and time.time() < _stok_exp - 60: return _stok
        if not Cfg.CREDS: return None
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now   = int(time.time())
            creds = json.loads(Cfg.CREDS)
            pem   = creds["private_key"].replace("\\n","\n")
            hdr   = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            pld   = base64.urlsafe_b64encode(json.dumps({
                "iss":creds["client_email"],"scope":"https://www.googleapis.com/auth/spreadsheets",
                "aud":"https://oauth2.googleapis.com/token","iat":now,"exp":now+3600
            }).encode()).rstrip(b"=")
            msg_b = hdr+b"."+pld
            pk    = serialization.load_pem_private_key(pem.encode(),password=None)
            sig   = pk.sign(msg_b,cp.PKCS1v15(),hashes.SHA256())
            jwt   = (msg_b+b"."+base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token",
                data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":jwt},timeout=10)
            if r.status_code==200:
                d=r.json(); _stok=d["access_token"]; _stok_exp=now+d.get("expires_in",3600)
                return _stok
            logger.error(f"sheets tok {r.status_code}")
        except Exception as e: logger.error(f"sheets tok err {e}")
    return None

_q = queue.Queue()
def _wsheets():
    while True:
        try:
            t = _q.get()
            if Cfg.SHEET_ID:
                tok = _sheets_tok()
                if tok:
                    tab = Cfg.SHEET_TAB.replace(" ","%20")
                    req_lib.post(
                        f"https://sheets.googleapis.com/v4/spreadsheets/{Cfg.SHEET_ID}/values/{tab}!A:K:append",
                        params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},
                        json={"values":[[
                            ahora().strftime("%d/%m/%Y %H:%M:%S"),
                            t.get("dir",""),str(t.get("tel","")),
                            t.get("nom",""),t.get("tipo",""),
                            t.get("staff",""),t.get("msg","")[:500],
                            t.get("evento",""),t.get("estado",""),
                        ]]},
                        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
                        timeout=10
                    )
            time.sleep(0.8)
        except Exception as e: logger.error(f"wsheets {e}")
        finally: _q.task_done()

threading.Thread(target=_wsheets,daemon=False,name="wsheets").start()

def reg(tel, nom, tipo, msg, evento, estado="", dir_="IN", staff=""):
    if str(tel).startswith("SIM_"): return
    if not Cfg.SHEET_ID: return
    _q.put({"tel":tel,"nom":nom,"tipo":tipo,"msg":msg,
            "evento":evento,"estado":estado,"dir":dir_,"staff":staff})

# ── ENVÍO WA ──────────────────────────────────────────────────
def wa(tel, txt, log="BOT"):
    if str(tel).startswith("SIM_"):
        add_hist(tel, log, txt, "out"); return True
    if not Cfg.TOKEN:
        logger.critical("wa(): WA_TOKEN vacío — renovar en Render")
        return False
    try:
        r = req_lib.post(
            f"https://graph.facebook.com/v19.0/{Cfg.PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":str(tel),"type":"text",
                  "text":{"body":txt,"preview_url":False}},
            headers={"Authorization":f"Bearer {Cfg.TOKEN}","Content-Type":"application/json"},
            timeout=10
        )
        if r.status_code == 200:
            add_hist(tel, log, txt, "out")
            reg(tel, log, "", txt, "BOT_OUT", dir_="OUT")
            return True
        else:
            err  = r.json().get("error", {})
            code_err = err.get("code", 0)
            msg_err  = err.get("message","?")[:120]
            logger.error(f"wa() FALLO tel={tel} status={r.status_code} code={code_err}: {msg_err}")
            if code_err == 190:
                logger.critical("⚠️  WA_TOKEN EXPIRADO — ve a Render > Environment > WA_TOKEN y renuévalo")
            elif code_err == 100:
                logger.error(f"⚠️  PHONE_ID incorrecto: {Cfg.PHONE_ID}")
            return False
    except Exception as e:
        logger.error(f"wa() excepción tel={tel}: {e}")
        return False

def notif_cc(p, motivo, extra=""):
    """Notifica a la CC asignada con nombre completo y asunto claro."""
    tel_cc   = p.get("staff_tel") or STAFF[cc_libre()]["tel"]
    nom_cc   = p.get("staff_nom") or "Coordinación"
    # Siempre nombre completo
    nom_full = p.get("nombre_full") or ""
    nom_pila = p.get("nombre") or ""
    nom_px   = nom_full if nom_full and len(nom_full.split())>1 else nom_pila or "Sin nombre"
    tel_px   = p.get("_tel","")
    tipo     = p.get("tipo","")
    equipo   = p.get("equipo","")
    pend_n   = len(p.get("pendientes",[]))

    # Línea de contexto según tipo de perfil
    if tipo == "IMO":
        ctx = f"*IMO | {pend_n} enrolados pendientes C1*"
        if equipo: ctx += f" | {equipo}"
    elif tipo == "PX":
        ctx = f"*Prospecto C1{(' | '+equipo) if equipo else ''}*"
        imo_n = p.get("imo_nombre","")
        if imo_n: ctx += f"\n*Su IMO:* {imo_n}"
    else:
        ctx = "*Nuevo contacto*"

    logger.info(f"notif_cc INICIO → {nom_cc} tel={tel_cc} | px={nom_px} | {motivo[:40]}")
    if not tel_cc:
        logger.critical("notif_cc: tel_cc VACÍO — revisar STAFF y cc_por_equipo")
        return nom_cc
    if not Cfg.TOKEN:
        logger.critical("notif_cc: WA_TOKEN VACÍO — derivación no enviada")
        return nom_cc
    exito = wa(tel_cc,
       f"🚨 *TORRE DE CONTROL — CPSL Lima*\n\n"
       f"*Nombre:* {nom_px}\n"
       f"*Tel:* wa.me/{tel_px}\n"
       f"{ctx}\n\n"
       f"*Asunto:* {motivo}"
       + (f"\n*Detalle:* {extra}" if extra else ""),
       f"SIS→{nom_cc}"
    )
    if not exito:
        logger.error(f"notif_cc: wa() falló enviando a {tel_cc}")
    return nom_cc

# ── FLUJO PRINCIPAL ───────────────────────────────────────────
STOP_W  = {"STOP","BAJA","DETENER","NO MAS"}
RESET_W = {"HOLA","MENU","MENÚ","0","INICIO","START","HI"}

def flujo(tel, texto):
    try:
        up = texto.strip().upper()

        # ── STOP ─────────────────────────────────────────────
        if up in STOP_W:
            del_s(tel)
            wa(tel,"Has sido dado de baja. Escribe HOLA para reiniciar.\n\n*Crear Poder Sin Límites Perú*","SIS")
            reg(tel,"","","STOP","STOP",dir_="SYS")
            return

        s = get_s(tel)

        # ── Reset / primera vez ───────────────────────────────
        if not s or up in RESET_W:
            p = perfil_crm(tel)
            p["_tel"] = tel
            s = {"p": p, "st": "MAIN"}
            set_s(tel, s)
            _menu_main(tel, p)
            return

        p  = s.get("p", {})
        p["_tel"] = tel
        # Si el perfil no tiene staff asignado (sesión vieja), recalcular
        if p.get("tipo") != "NUEVO" and not p.get("staff_tel"):
            equipo = p.get("equipo","")
            k = cc_por_equipo(equipo) if equipo else cc_libre()
            p["staff_key"] = k
            p["staff_tel"] = STAFF[k]["tel"]
            p["staff_nom"] = STAFF[k]["nombre"]
            s["p"] = p
            set_s(tel, s)
        st = s.get("st","MAIN")
        sb = s.get("sb")  # sub-estado

        # ── Volver siempre ────────────────────────────────────
        if up in {"9","VOLVER"}:
            s["st"]="MAIN"; s["sb"]=None; set_s(tel,s)
            _menu_main(tel,p); return

        # ── Estado DERIVADO ───────────────────────────────────
        if st == "DER":
            tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]
            nom_cc = p.get("staff_nom","Coord")
            nom_px = p.get("nombre_full") or p.get("nombre","")
            nom_full_der = p.get("nombre_full") or nom_px
            wa(tel_cc,
               f"💬 *Mensaje de {nom_full_der}*\n"
               f"Tel: wa.me/{tel}\n\n"
               f"{texto}",
               f"RELAY→{nom_cc}")
            wa(tel,"✅ Mensaje entregado a tu coordinadora.\n_Escribe *0* para volver al menú._",p.get("nombre",""))
            return

        tipo = p.get("tipo","NUEVO")
        if tipo == "IMO":   _imo(tel, up, texto, s, p)
        elif tipo == "PX":  _px(tel, up, texto, s, p)
        else:               _nuevo(tel, up, texto, s, p)

    except Exception as e:
        logger.error(f"flujo {tel}: {e}", exc_info=True)


def _menu_main(tel, p):
    tipo = p.get("tipo","NUEVO")
    nom  = p.get("nombre") or "Líder"

    if tipo == "IMO":
        n = len(p.get("pendientes",[]))
        al = f"\n⚠️ Tienes *{n}* enrolado{'s' if n!=1 else ''} pendiente{'s' if n!=1 else ''} de C1." if n else "\n✅ Todos tus enrolados al día."
        wa(tel,
           f"👑 *Hola {nom}* — Portal IMO{al}\n\n"
           f"1️⃣ Ver mis pendientes de C1\n"
           f"2️⃣ Ver TODOS mis enrolados\n"
           f"3️⃣ Solicitar ser Aliado C1 E27\n"
           f"4️⃣ Fechas activas\n"
           f"5️⃣ Hablar con Coordinación\n"
           f"0️⃣ Salir\n\n"
           f"_STOP para darte de baja._", nom)

    elif tipo == "PX":
        nom_cc = p.get("staff_nom","Coordinación")
        wa(tel,
           f"🌟 *Hola {nom}!*\n"
           f"Tu coordinadora: *{nom_cc}*\n\n"
           f"1️⃣ Confirmar asistencia al C1 Equipo 27\n"
           f"2️⃣ Fechas y logística\n"
           f"3️⃣ Inversión y pagos\n"
           f"4️⃣ Hablar con mi coordinadora\n"
           f"0️⃣ Salir\n\n"
           f"_STOP para darte de baja._", nom)

    else:  # NUEVO
        wa(tel,
           f"🌟 *Bienvenido a Crear Poder Sin Límites Perú*\n"
           f"Canal Corporativo Oficial — Sede Lima.\n\n"
           f"1️⃣ Ya participé antes (cambié de número)\n"
           f"2️⃣ Soy nuevo — quiero información\n"
           f"0️⃣ Salir\n\n"
           f"_STOP para darte de baja._", "Sistema")


def _imo(tel, up, texto, s, p):
    nom  = p.get("nombre","Líder")
    pend = p.get("pendientes",[])
    st   = s.get("st","MAIN")

    if st == "MAIN":
        if up == "1":
            if pend:
                lista = "\n".join(pend[:20])
                if len(pend)>20: lista += f"\n_...y {len(pend)-20} más_"
                wa(tel,
                   f"⏳ *Pendientes de C1 — Equipo 27*\n"
                   f"📅 {Cfg.FECHA}\n📍 {Cfg.LUGAR}\n\n"
                   f"{lista}\n\n"
                   f"¿Cómo avanzan tus gestiones?\n"
                   f"1️⃣ Reportar una confirmación\n"
                   f"2️⃣ Sigo gestionando\n"
                   f"3️⃣ Necesito apoyo de Coordinación\n"
                   f"9️⃣ Volver", nom)
                s["st"]="IMO_PEND"; set_s(tel,s)
            else:
                wa(tel,"🎉 ¡Todos tus enrolados ya se sentaron! Felicitaciones.\n\n9️⃣ Volver",nom)

        elif up == "2":
            rows = _get_rows()
            t9   = n9(tel)
            todos = []
            for r in rows:
                if n9(r.get("Tel. IMO","")) == t9:
                    nom_px = f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()}"
                    eq     = r.get("Equipo","")
                    c1     = str(r.get("C1","")).strip().upper()
                    st_px  = "✅ Sentado" if c1=="SI" else "⏳ Pendiente"
                    todos.append(f"• {nom_px} ({eq}) — {st_px}")
            if todos:
                lista = "\n".join(todos[:25])
                if len(todos)>25: lista+=f"\n_...y {len(todos)-25} más_"
                wa(tel,f"📋 *Todos tus enrolados:*\n\n{lista}\n\n9️⃣ Volver",nom)
            else:
                wa(tel,"Sin enrolados vinculados en el sistema.\n\n9️⃣ Volver",nom)

        elif up == "3":
            nom_cc = notif_cc(p,"Solicita ser Aliado C1 E27",f"IMO: {p.get('imo_nombre',nom)}")
            wa(tel,
               f"✅ Solicitud registrada.\n\n"
               f"Tu coordinadora *{nom_cc}* te escribirá para confirmar tu rol como Aliado.\n\n"
               f"9️⃣ Volver",nom)
            reg(tel,nom,"IMO","Solicita ser Aliado","ALIADO",dir_="SYS",staff=nom_cc)

        elif up == "4":
            wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver",nom)

        elif up == "5":
            nom_cc = notif_cc(p,"IMO solicita atención directa")
            s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Derivado a *{nom_cc}*. Puedes escribirle directamente aquí.",nom)

        elif up == "0":
            del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA para volver. 🌟",nom)
        else:
            _menu_main(tel,p)

    elif st == "IMO_PEND":
        if up == "1":
            s["st"]="IMO_CONF"; set_s(tel,s)
            wa(tel,"Escribe el nombre de quien confirma.\n_Escribe 9 para volver._",nom)
        elif up == "2":
            s["st"]="MAIN"; set_s(tel,s)
            wa(tel,"Perfecto. Cuando tengas confirmaciones escríbenos. 💪\n\n9️⃣ Volver / 0️⃣ Menú",nom)
        elif up == "3":
            nom_cc = notif_cc(p,"IMO necesita apoyo para gestionar pendientes C1 E27",f"{len(pend)} pendientes")
            s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Derivado. *{nom_cc}* te apoyará directamente.",nom)
        else:
            s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)

    elif st == "IMO_CONF":
        nom_cc = notif_cc(p,"IMO reporta confirmación de enrolado",f"Nombre: '{texto}'")
        reg(tel,nom,"IMO",f"Confirma: {texto}","CONF_ENROLADO",dir_="SYS",staff=nom_cc)
        wa(tel,
           f"✅ *{texto}* registrado como confirmado.\n"
           f"Coordinación ({nom_cc}) lo procesará.\n\n"
           f"¿Otra confirmación? Escribe el nombre o *9* para volver.",nom)


def _px(tel, up, texto, s, p):
    nom    = p.get("nombre","Líder")
    nom_cc = p.get("staff_nom","Coordinación")
    st     = s.get("st","MAIN")

    if st == "MAIN":
        if up == "1":
            nom_cc2 = notif_cc(p,"PX CONFIRMA asistencia C1 E27")
            reg(tel,p.get("nombre_full",nom),"PX","Confirma C1 E27","CONFIRMA",dir_="SYS",staff=nom_cc2)
            wa(tel,
               f"¡Confirmado {nom}! ✅\n\n"
               f"📍 *{Cfg.LUGAR}*\n"
               f"🗓 {Cfg.FECHA}\n"
               f"⏰ {Cfg.REGISTRO}\n\n"
               f"Ropa cómoda y botella de agua. Bloquea los 3 días.\n\n"
               f"Tu coordinadora *{nom_cc2}* recibirá tu confirmación. 💪",nom)
            del_s(tel)

        elif up == "2":
            wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver",nom)

        elif up == "3":
            wa(tel,
               "💳 *Inversión y Pagos*\n\n"
               "BCP — Creación Cuántica E.I.R.L.\n"
               "Cuenta Soles: *1934218307060*\n\n"
               "1️⃣ Enviar voucher a Coordinación\n9️⃣ Volver",nom)
            s["st"]="PX_PAGO"; set_s(tel,s)

        elif up == "4":
            nom_cc2 = notif_cc(p,"PX solicita atención directa")
            s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Te derivo con *{nom_cc2}*. Escribe tu consulta aquí.",nom)

        elif up == "0":
            del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA para volver. 🌟",nom)
        else:
            _menu_main(tel,p)

    elif st == "PX_PAGO":
        if up == "1":
            nom_cc2 = notif_cc(p,"PX envía voucher de pago")
            s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Derivado a *{nom_cc2}*. Adjunta el voucher en el siguiente mensaje.",nom)
        else:
            s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)


def _nuevo(tel, up, texto, s, p):
    st = s.get("st","MAIN")

    if st == "MAIN":
        if up == "1":
            s["st"]="NVO_NUM"; set_s(tel,s)
            wa(tel,
               "Para encontrar tu registro escríbeme:\n\n"
               "*Nombre completo y DNI* en un solo mensaje.\n"
               "_Ej: Juan Pérez 12345678_\n\n"
               "_Escribe 9 para volver._","Sistema")
        elif up == "2":
            s["st"]="NVO_INFO"; set_s(tel,s)
            wa(tel,
               "🌟 *Crear Poder Sin Límites Perú*\n\n"
               "Entrenamientos de liderazgo y transformación de alto rendimiento. "
               "Salir del modo automático y crear resultados extraordinarios.\n\n"
               "1️⃣ Información del Capítulo 1\n"
               "2️⃣ Fechas 2026\n"
               "3️⃣ Inversión\n"
               "4️⃣ Hablar con Coordinación\n"
               "9️⃣ Volver","Sistema")
        elif up == "0":
            del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA cuando quieras. 🌟","Sistema")
        else:
            _menu_main(tel,p)

    elif st == "NVO_NUM":
        k = cc_libre(); cc_add(k)
        tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]
        wa(tel_cc,
           f"🔍 *VERIFICACIÓN DE IDENTIDAD*\n"
           f"Tel: wa.me/{tel}\n"
           f"Dato: '{texto}'\nBuscar en sistema y actualizar.","SIS")
        p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc
        s["p"]=p; s["st"]="DER"; set_s(tel,s)
        wa(tel,f"✅ Datos enviados a Coordinación ({nom_cc}). Te responderán pronto.","Sistema")
        reg(tel,texto,"NUEVO",texto,"CAMBIO_NUM",dir_="SYS",staff=nom_cc)

    elif st == "NVO_INFO":
        if up == "1":
            wa(tel,
               f"🚀 *Capítulo 1 — El Descubrimiento*\n\n"
               f"3 días vivenciales para observar los mecanismos que frenan tus resultados. "
               f"No es una conferencia — es transformación.\n\n"
               f"*Próxima fecha:* {Cfg.FECHA}\n"
               f"*Lugar:* {Cfg.LUGAR}\n\n"
               f"1️⃣ Inscribirme\n9️⃣ Volver","Sistema")
            s["st"]="NVO_C1"; set_s(tel,s)
        elif up == "2":
            wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver","Sistema")
        elif up == "3":
            wa(tel,
               "💳 *Inversión*\n\n"
               "El costo es personalizado. "
               "Tu coordinadora te dará todos los detalles.\n\n"
               "1️⃣ Contactar Coordinación\n9️⃣ Volver","Sistema")
            s["st"]="NVO_INV"; set_s(tel,s)
        elif up == "4":
            k=cc_libre(); cc_add(k)
            tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]
            wa(tel_cc,f"🆕 *NUEVO PROSPECTO*\nTel: wa.me/{tel}","SIS")
            p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc
            s["p"]=p; s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Derivado a Coordinación ({nom_cc}). Te escribirán pronto.","Sistema")
        elif up == "9":
            s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)

    elif st in ("NVO_C1","NVO_INV"):
        if up == "1":
            k=cc_libre(); cc_add(k)
            tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]
            wa(tel_cc,
               f"🆕 *NUEVO PROSPECTO INTERESADO*\nTel: wa.me/{tel}\n"
               f"Interés: {'C1' if st=='NVO_C1' else 'Inversión'}","SIS")
            p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc
            s["p"]=p; s["st"]="DER"; set_s(tel,s)
            wa(tel,f"✅ Coordinación ({nom_cc}) te escribirá en breve. 🌟","Sistema")
        elif up == "9":
            s["st"]="NVO_INFO"; set_s(tel,s)
            wa(tel,"1️⃣ Info C1\n2️⃣ Fechas\n3️⃣ Inversión\n4️⃣ Coordinación\n9️⃣ Volver","Sistema")


# ── ENDPOINTS ─────────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def wh_get():
    if request.args.get("hub.verify_token")==Cfg.VER_TOKEN:
        return request.args.get("hub.challenge"),200
    return "error",403

@app.route("/webhook", methods=["POST"])
def wh_post():
    d = request.get_json(silent=True)
    if not d: return jsonify({"status":"ok"}),200
    try:
        chg  = d["entry"][0]["changes"][0]["value"]
        if "messages" not in chg: return jsonify({"status":"ok"}),200
        msg  = chg["messages"][0]
        tel  = msg.get("from","")
        tipo = msg.get("type","")
        if tipo=="text":
            txt = str(msg["text"]["body"])
            s_wh  = get_s(tel)
            p_wh  = s_wh.get("p") or perfil_crm(tel)
            # Usar nombre completo siempre que esté disponible
            nom_d = (p_wh.get("nombre_full") or
                     p_wh.get("imo_nombre") or
                     p_wh.get("nombre") or tel)
            nom_h = f"({p_wh.get('tipo','?')}) {nom_d}"
            add_hist(tel, nom_h, txt, "in")
            reg(tel, p_wh.get("nombre",""), p_wh.get("tipo",""), txt, "MSG_IN",
                staff=p_wh.get("staff_nom",""))
            threading.Thread(target=flujo,args=(tel,txt),daemon=False,name=f"f{tel[-4:]}").start()
        else:
            s_wh = get_s(tel)
            p_wh = s_wh.get("p") or {"tipo":"?","nombre":None}
            nom_h = f"({p_wh.get('tipo','?')}) {p_wh.get('nombre') or tel}"
            add_hist(tel, nom_h, f"[{tipo}]", "in")
            wa(tel,"Por favor responde con texto o el número de tu opción.","SIS")
    except Exception as e: logger.error(f"wh {e}",exc_info=True)
    return jsonify({"status":"ok"}),200

@app.route("/api/historial")
def hist_all():
    """Retorna historial fusionado de todos los archivos posibles."""
    try:
        merged = {}  # key=tel+hora+texto para deduplicar
        for path in [Cfg.HIST, Cfg.HIST_ALT]:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for m in json.load(f):
                        k = f"{m.get('telefono','')}|{m.get('hora','')}|{m.get('texto','')[:30]}"
                        merged[k] = m
        resultado = sorted(merged.values(), key=lambda x: x.get("hora",""))
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"hist_all {e}")
    return jsonify([]), 200

@app.route("/api/historial/<tel>")
def hist_tel(tel):
    """Historial filtrado por teléfono — fusiona todos los archivos."""
    try:
        merged = {}
        for path in [Cfg.HIST, Cfg.HIST_ALT]:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for m in json.load(f):
                        if str(m.get("telefono",""))==str(tel):
                            k = f"{m.get('hora','')}|{m.get('texto','')[:30]}"
                            merged[k] = m
        resultado = sorted(merged.values(), key=lambda x: x.get("hora",""))
        return jsonify(resultado), 200
    except Exception as e:
        logger.error(f"hist_tel {e}")
    return jsonify([]), 200

@app.route("/api/carga_coordinadoras")
def carga_cc():
    return jsonify({k:{"nombre":v["nombre"],"casos":_carga.get(k,0),"tel":v["tel"]} for k,v in STAFF.items()}),200

@app.route("/api/enviar",methods=["POST"])
def api_enviar():
    d=request.json or {}
    tel=d.get("telefono",""); msg=d.get("mensaje","")
    if not tel or not msg: return jsonify({"error":"faltan datos"}),400
    wa(tel,msg,"PANEL")
    reg(tel,"PANEL","MANUAL",msg,"MANUAL_OUT",dir_="OUT")
    return jsonify({"status":"ok"}),200

@app.route("/api/mensaje_simulador",methods=["POST"])
def api_sim():
    """Simulador: inyecta perfil según prefijo del tel ficticio.
    SIM_IMO_*  → perfil IMO con pendientes de ejemplo
    SIM_PX_*   → perfil PX con coordinadora asignada
    SIM_GRAD_* → perfil IMO marcado como graduado MJ
    SIM_NEW_*  → perfil NUEVO
    SIM_<tel_real> → busca en CSV el perfil real del número
    """
    d   = request.json or {}
    tel = d.get("telefono","")
    txt = d.get("texto","")
    if not tel or not txt: return jsonify({"error":"faltan datos"}), 400

    # Construir perfil de simulación según el prefijo
    s_sim = get_s(tel)
    if not s_sim.get("p"):
        tel_up = tel.upper()
        if "SIM_IMO" in tel_up or "SIM_GRAD" in tel_up:
            tipo_sim = "IMO"
            p_iny = {
                "tipo":       tipo_sim,
                "nombre":     "Gareth",
                "apellido":   "Ramos Pérez",
                "nombre_full":"Gareth Said Ramos Pérez",
                "equipo":     "EQUIPO 26",
                "imo_nombre": "Gareth Said Ramos Pérez",
                "imo_tel":    tel,
                "staff_key":  "dmoscoso",
                "staff_tel":  STAFF["dmoscoso"]["tel"],
                "staff_nom":  STAFF["dmoscoso"]["nombre"],
                "pendientes": [
                    "• Juan Carlos Soto García (EQUIPO 26)",
                    "• María Fernanda López Ruiz (EQUIPO 25)",
                    "• Carlos Alberto Mendoza (EQUIPO 26)",
                ],
            }
        elif "SIM_PX" in tel_up:
            p_iny = {
                "tipo":       "PX",
                "nombre":     "Kely",
                "apellido":   "Arcce Rojas",
                "nombre_full":"Kely Arcce Rojas",
                "equipo":     "EQUIPO 26",
                "imo_nombre": "Gareth Said Ramos Pérez",
                "imo_tel":    "",
                "staff_key":  "jmarin",
                "staff_tel":  STAFF["jmarin"]["tel"],
                "staff_nom":  STAFF["jmarin"]["nombre"],
                "pendientes": [],
            }
        else:  # NUEVO o SIM_NEW
            p_iny = {
                "tipo":       "NUEVO",
                "nombre":     None,
                "nombre_full":"",
                "staff_key":  None,
                "staff_tel":  None,
                "staff_nom":  None,
                "pendientes": [],
            }
        # Intentar buscar en CSV si parece un número real
        if not any(x in tel_up for x in ["SIM_IMO","SIM_PX","SIM_GRAD","SIM_NEW"]):
            p_real = perfil_crm(tel)
            if p_real.get("tipo") != "NUEVO":
                p_iny = p_real
        s_sim["p"]  = p_iny
        s_sim["st"] = "MAIN"
        set_s(tel, s_sim)

    p_log = s_sim.get("p") or {}
    nom_h = f"({p_log.get('tipo','SIM')}) {p_log.get('nombre_full') or p_log.get('nombre') or tel}"
    add_hist(tel, nom_h, txt, "in")
    threading.Thread(target=flujo, args=(tel, txt), daemon=True,
                     name=f"sim{tel[-4:]}").start()
    return jsonify({"status":"ok"}), 200

@app.route("/api/test_notif", methods=["POST"])
def test_notif():
    """Prueba envío de notificación a una coordinadora. Uso: POST {cc:'dmoscoso', msg:'test'}"""
    d    = request.json or {}
    key  = d.get("cc","dmoscoso")
    msg  = d.get("msg","Test de notificación desde Torre de Control")
    tel  = STAFF.get(key,{}).get("tel","")
    nom  = STAFF.get(key,{}).get("nombre","?")
    if not tel:
        return jsonify({"error":f"CC '{key}' no encontrada"}), 400
    logger.info(f"TEST NOTIF → {nom} ({tel})")
    exito = wa(tel,
        f"🧪 *TEST Torre de Control*\n{msg}\n\nSi ves esto, las notificaciones funcionan ✅",
        "TEST"
    )
    return jsonify({"enviado":exito,"cc":nom,"tel":tel}), 200

@app.route("/api/clear_sessions", methods=["POST"])
def clear_sessions():
    """Borra todas las sesiones para forzar re-identificación con datos actualizados."""
    import glob
    borradas = 0
    for path in [Cfg.S_REAL, Cfg.S_SIM]:
        if os.path.exists(path):
            with open(path,"w") as f: json.dump({},f)
            borradas += 1
    logger.info(f"Sesiones borradas ({borradas} archivos)")
    return jsonify({"ok":True,"archivos_borrados":borradas}), 200

@app.route("/api/token_status")
def token_status():
    """Verifica si el WA_TOKEN está configurado y prueba una llamada a Meta."""
    token_ok = bool(Cfg.TOKEN) and len(Cfg.TOKEN) > 20
    phone_ok = bool(Cfg.PHONE_ID)
    result   = {"token_configurado":token_ok,"phone_id_configurado":phone_ok,
                "token_len":len(Cfg.TOKEN) if Cfg.TOKEN else 0}
    if token_ok and phone_ok:
        try:
            r = req_lib.get(
                f"https://graph.facebook.com/v19.0/{Cfg.PHONE_ID}",
                headers={"Authorization":f"Bearer {Cfg.TOKEN}"},timeout=8)
            result["meta_ok"]  = r.status_code == 200
            result["meta_resp"] = r.status_code
        except Exception as e:
            result["meta_ok"] = False; result["meta_err"] = str(e)
    return jsonify(result), 200

@app.route("/status")
def status():
    rows = _get_rows()
    return jsonify({
        "version":"v109","status":"activo",
        "csv_filas":len(rows),"csv_path":Cfg.CSV,
        "csv_ok":len(rows)>0,
        "hora":ahora().strftime("%d/%m/%Y %H:%M:%S"),
        "c1_e27":Cfg.FECHA,
        "carga_cc":{k:v for k,v in _carga.items()},
    }),200

@app.route("/chat")
def panel():
    try:
        with open(os.path.join(BASE_DIR,"panel_chat.html"),encoding="utf-8") as f: return f.read()
    except: return "<h2>Panel no disponible</h2>",200

# ── INTEGRACIÓN WORKER DE SEGUIMIENTO ────────────────────────
try:
    from seguimiento_github import (
        run_seguimiento, _estado as _estado_worker,
        AUTO as SEG_AUTO, HORA_AUTO as SEG_HORA
    )
    _SEG_OK = True
    logger.info(f"✅ Worker seguimiento GitHub cargado (AUTO={SEG_AUTO}, HORA={SEG_HORA})")
except ImportError:
    try:
        from seguimiento_autonomo import (
            run_seguimiento, _estado_worker,
        )
        _SEG_OK = True
        logger.info("✅ Worker seguimiento_autonomo cargado")
    except ImportError:
        _SEG_OK = False
        _estado_worker = {"corriendo":False,"ok":0,"err":0,"total":0,"ultimo":"No disponible","log":[]}
        def run_seguimiento(**kw): return {"error":"Worker no encontrado"}
        logger.warning("⚠️ Worker seguimiento no encontrado")

@app.route("/api/seguimiento/estado")
def seg_estado():
    return jsonify(_estado_worker), 200

@app.route("/api/seguimiento/iniciar", methods=["POST"])
def seg_iniciar():
    d   = request.json or {}
    res = run_seguimiento(
        modo        = d.get("modo","ambos"),
        limite_imos = d.get("limite_imos"),
        limite_px   = d.get("limite_px"),
    )
    return jsonify(res), 200

@app.route("/api/seguimiento/log")
def seg_log():
    return jsonify(_estado_worker.get("log",[])), 200

@app.route("/api/seguimiento/reenvio", methods=["POST"])
def seg_reenvio():
    """Reenvía a quienes no han respondido según el Sheet."""
    if not _SEG_OK:
        return jsonify({"error":"Worker no disponible"}), 503
    from seguimiento_autonomo import run_reenvio
    d   = request.json or {}
    res = run_reenvio(
        horas_espera = d.get("horas_espera", 48),
        limite       = d.get("limite"),
    )
    return jsonify(res), 200

@app.route("/api/seguimiento/detectar", methods=["GET"])
def seg_detectar():
    """Devuelve lista de contactos sin respuesta según el Sheet."""
    if not _SEG_OK:
        return jsonify({"error":"Worker no disponible"}), 503
    from seguimiento_autonomo import detectar_sin_respuesta
    horas = int(request.args.get("horas", 48))
    try:
        sin_resp = detectar_sin_respuesta(horas_espera=horas)
        return jsonify({"total": len(sin_resp), "contactos": sin_resp[:50]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/seguimiento/reenviar", methods=["POST"])
def seg_reenviar():
    d = request.json or {}
    if not _SEG_OK:
        return jsonify({"error":"Worker no disponible"}), 503
    res = run_reenvio(
        horas_espera = d.get("horas_espera", 48),
        limite       = d.get("limite"),
    )
    return jsonify(res), 200

@app.route("/api/seguimiento/sin_respuesta")
def seg_sin_resp():
    if not _SEG_OK:
        return jsonify([]), 200
    horas = int(request.args.get("horas", 48))
    resultado = detectar_sin_respuesta(horas_espera=horas)
    return jsonify(resultado), 200

if __name__=="__main__":
    logger.info("🚀 CPSL Torre de Control V109")
    logger.info(f"   CSV: {Cfg.CSV}")
    logger.info(f"   CSV existe: {os.path.exists(Cfg.CSV)}")
    logger.info(f"   Filas: {len(_get_rows())}")
    logger.info(f"   Sheet: {Cfg.SHEET_ID or 'NO CONFIG'}")
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)),debug=False)
