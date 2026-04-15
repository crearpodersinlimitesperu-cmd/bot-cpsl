"""
Bot WhatsApp — Crear Poder Sin Límites Perú
V109-FIX: Corrección de errores JSON + Compatibilidad worker
✅ LISTO PARA COPIAR Y PEGAR
"""

import os, re, json, time, csv, base64, random, logging, threading, queue, inspect
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("CPSL")
app = Flask(__name__)

# ── ERROR HANDLERS (Devuelven JSON, no HTML) ──────────────────
@app.errorhandler(500)
def error_500(e):
    logger.error(f"Error 500: {e}", exc_info=True)
    return jsonify({"error": "Error interno del servidor", "mensaje": str(e)}), 500

@app.errorhandler(404)
def error_404(e):
    return jsonify({"error": "Endpoint no encontrado"}), 404

# ── ZONA HORARIA ─────────────────────────────────────────────
TZ_LIMA = timezone(timedelta(hours=-5))
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
_carga = {k: 0 for k in STAFF}
_carga_lk = threading.Lock()

def cc_libre():
    with _carga_lk:
        return min(_carga, key=_carga.get)

def cc_add(k):
    with _carga_lk:
        if k in _carga: _carga[k] += 1

_CC_POR_EQUIPO = {
    "EQUIPO 26": "dmoscoso", "EQUIPO 25": "jmarin", "EQUIPO 24": "zurteaga",
    "EQUIPO 23": "zurteaga", "EQUIPO 22": "lpasquel", "EQUIPO 21": "lpasquel",
    "EQUIPO 20": "lpasquel", "EQUIPO 19": "lvalencia", "EQUIPO 18": "lvalencia",
    "EQUIPO 17": "lvalencia", "EQUIPO 16": "lvalencia", "EQUIPO 15": "lvalencia",
    "EQUIPO 14": "lvalencia",
}

def cc_por_equipo(equipo):
    return _CC_POR_EQUIPO.get(str(equipo).strip().upper(), cc_libre())

# ── CONFIG ────────────────────────────────────────────────────
class Cfg:
    TOKEN = os.environ.get("WA_TOKEN","")
    PHONE_ID = os.environ.get("WA_PHONE_ID","")
    VER_TOKEN = os.environ.get("WA_VERIFY_TOKEN","cpsl2026")
    SHEET_ID = os.environ.get("SHEET_ID","")
    CREDS = os.environ.get("GOOGLE_CREDENTIALS","")
    SHEET_TAB = os.environ.get("SHEET_TAB","Hoja 1")
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
    "📅 *Próximas Fechas — Sede Lima 2026*\n\n"
    f"🚀 *C1 Equipo 27:* {Cfg.FECHA}\n"
    f"   📍 {Cfg.LUGAR}\n\n"
    "🔥 *C2 Equipo 27:* Jueves 14 de mayo\n"
    "👑 *MJ Inducción:* Viernes 17 de abril"
)

# ── CACHÉ CSV ─────────────────────────────────────────────────
_csv_cache, _csv_mtime, _csv_lk = None, 0.0, threading.Lock()

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
def n9(t): return _d(t)[-9:]
def np(s):
    p = [x for x in str(s or '').strip().split() if len(x)>2]
    if not p: return str(s).strip().title()
    if len(p) >= 3: return p[2].title()
    if len(p) == 2: return p[1].title()
    return p[0].title()

# ── PERFIL CRM ────────────────────────────────────────────────
def perfil_crm(tel):
    t9 = n9(tel)
    rows = _get_rows()
    p = {"tipo":"NUEVO","nombre":None,"apellido":"","nombre_full":"","equipo":"",
         "imo_nombre":"","imo_tel":"","staff_key":None,"staff_tel":None,"staff_nom":None,"pendientes":[]}
    px_row, imo_rows = None, []
    for r in rows:
        if n9(r.get("Teléfono","")) == t9: px_row = r
        if n9(r.get("Tel. IMO","")) == t9 and n9(r.get("Tel. IMO","")): imo_rows.append(r)
    if imo_rows:
        p["tipo"] = "IMO"
        p["nombre"] = np(imo_rows[0].get("IMO",""))
        p["imo_nombre"] = str(imo_rows[0].get("IMO","")).strip()
        p["pendientes"] = [f"• {r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()} ({r.get('Equipo','')})" for r in imo_rows]
    elif px_row:
        p["tipo"] = "PX"
        p["nombre"] = np(px_row.get("Nombre",""))
        p["apellido"] = px_row.get("Apellido","").strip().title()
        p["nombre_full"] = f"{p['nombre']} {p['apellido']}".strip()
        p["equipo"] = px_row.get("Equipo","")
        p["imo_nombre"] = px_row.get("IMO","").strip()
        p["imo_tel"] = _d(px_row.get("Tel. IMO",""))
    if p["tipo"] == "PX":
        k = cc_por_equipo(p.get("equipo",""))
    elif p["tipo"] == "IMO":
        import re as _re2
        equipos = [r.get("Equipo","") for r in imo_rows] if imo_rows else []
        nums = [int(m.group()) for eq in equipos for m in [_re2.search(r"\d+",eq)] if m]
        eq_top = f"EQUIPO {max(nums)}" if nums else ""
        k = cc_por_equipo(eq_top)
    else:
        k = cc_libre()
    p["staff_key"], p["staff_tel"], p["staff_nom"] = k, STAFF[k]["tel"], STAFF[k]["nombre"]
    cc_add(k)
    return p

# ── SESIONES ──────────────────────────────────────────────────
def _sp(tel): return Cfg.S_SIM if str(tel).startswith("SIM_") else Cfg.S_REAL

def get_s(tel):
    path = _sp(tel)
    try:
        with FileLock(path+".lock", timeout=Cfg.LOCK_T):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f: return json.load(f).get(str(tel), {})
    except FileLockTimeout: logger.warning(f"lock get {tel}")
    except Exception as e: logger.error(f"get_s {e}")
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
    except Exception as e: logger.error(f"set_s {e}")

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
            h.append({"telefono":str(tel),"nombre":nom or "?","texto":txt,"tipo":tipo,"hora":ahora().strftime("%d/%m %H:%M")})
            if len(h)>5000: h=h[-5000:]
            with open(path,"w",encoding="utf-8") as f: json.dump(h,f,ensure_ascii=False,indent=2)
    except Exception as e: logger.error(f"hist {e}")

# ── GOOGLE SHEETS JWT ─────────────────────────────────────────
_stok, _stok_exp, _stok_lk = None, 0, threading.Lock()

def _sheets_tok():
    global _stok, _stok_exp
    with _stok_lk:
        if _stok and time.time() < _stok_exp - 60: return _stok
        if not Cfg.CREDS: return None
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now = int(time.time())
            creds = json.loads(Cfg.CREDS)
            pem = creds["private_key"].replace("\\n","\n")
            hdr = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            pld = base64.urlsafe_b64encode(json.dumps({"iss":creds["client_email"],"scope":"https://www.googleapis.com/auth/spreadsheets","aud":"https://oauth2.googleapis.com/token","iat":now,"exp":now+3600}).encode()).rstrip(b"=")
            msg_b = hdr+b"."+pld
            pk = serialization.load_pem_private_key(pem.encode(),password=None)
            sig = pk.sign(msg_b,cp.PKCS1v15(),hashes.SHA256())
            jwt = (msg_b+b"."+base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req_lib.post("https://oauth2.googleapis.com/token",data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":jwt},timeout=10)
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
                    req_lib.post(f"https://sheets.googleapis.com/v4/spreadsheets/{Cfg.SHEET_ID}/values/{tab}!A:K:append",
                        params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},
                        json={"values":[[ahora().strftime("%d/%m/%Y %H:%M:%S"),t.get("dir",""),str(t.get("tel","")),t.get("nom",""),t.get("tipo",""),t.get("staff",""),t.get("msg","")[:500],t.get("evento",""),t.get("estado",""),]]},
                        headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},timeout=10)
            time.sleep(0.8)
        except Exception as e: logger.error(f"wsheets {e}")
        finally: _q.task_done()

threading.Thread(target=_wsheets,daemon=False,name="wsheets").start()

def reg(tel, nom, tipo, msg, evento, estado="", dir_="IN", staff=""):
    if str(tel).startswith("SIM_"): return
    if not Cfg.SHEET_ID: return
    _q.put({"tel":tel,"nom":nom,"tipo":tipo,"msg":msg,"evento":evento,"estado":estado,"dir":dir_,"staff":staff})

# ── ENVÍO WA ──────────────────────────────────────────────────
def wa(tel, txt, log="BOT"):
    if str(tel).startswith("SIM_"): add_hist(tel, log, txt, "out"); return True
    if not Cfg.TOKEN: logger.critical("wa(): WA_TOKEN vacío"); return False
    try:
        r = req_lib.post(f"https://graph.facebook.com/v19.0/{Cfg.PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":str(tel),"type":"text","text":{"body":txt,"preview_url":False}},
            headers={"Authorization":f"Bearer {Cfg.TOKEN}","Content-Type":"application/json"},timeout=10)
        if r.status_code == 200:
            add_hist(tel, log, txt, "out"); reg(tel, log, "", txt, "BOT_OUT", dir_="OUT"); return True
        else:
            err = r.json().get("error", {}); code_err = err.get("code", 0); msg_err = err.get("message","?")[:120]
            logger.error(f"wa() FALLO tel={tel} status={r.status_code} code={code_err}: {msg_err}")
            if code_err == 190: logger.critical("⚠️ WA_TOKEN EXPIRADO")
            elif code_err == 100: logger.error(f"⚠️ PHONE_ID incorrecto: {Cfg.PHONE_ID}")
            return False
    except Exception as e: logger.error(f"wa() excepción tel={tel}: {e}"); return False

def notif_cc(p, motivo, extra=""):
    tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]; nom_cc = p.get("staff_nom") or "Coordinación"
    nom_full = p.get("nombre_full") or ""; nom_pila = p.get("nombre") or ""
    nom_px = nom_full if nom_full and len(nom_full.split())>1 else nom_pila or "Sin nombre"
    tel_px = p.get("_tel",""); tipo = p.get("tipo",""); equipo = p.get("equipo",""); pend_n = len(p.get("pendientes",[]))
    if tipo == "IMO": ctx = f"*IMO | {pend_n} enrolados pendientes C1*"; ctx += f" | {equipo}" if equipo else ""
    elif tipo == "PX": ctx = f"*Prospecto C1{(' | '+equipo) if equipo else ''}*"; imo_n = p.get("imo_nombre",""); ctx += f"\n*Su IMO:* {imo_n}" if imo_n else ""
    else: ctx = "*Nuevo contacto*"
    logger.info(f"notif_cc INICIO → {nom_cc} tel={tel_cc} | px={nom_px} | {motivo[:40]}")
    if not tel_cc or not Cfg.TOKEN: logger.critical("notif_cc: tel_cc o WA_TOKEN vacío"); return nom_cc
    exito = wa(tel_cc, f"🚨 *TORRE DE CONTROL — CPSL Lima*\n\n*Nombre:* {nom_px}\n*Tel:* wa.me/{tel_px}\n{ctx}\n\n*Asunto:* {motivo}"+(f"\n*Detalle:* {extra}" if extra else ""), f"SIS→{nom_cc}")
    if not exito: logger.error(f"notif_cc: wa() falló enviando a {tel_cc}")
    return nom_cc

# ── COORDINADORAS ─────────────────────────────────────────────
_CC_TELS = {
    "51912379744": {"key":"dmoscoso","nombre":"Diana","nombre_full":"Diana Moscoso"},
    "51933599903": {"key":"jmarin","nombre":"Joyce","nombre_full":"Joyce Marín"},
    "51933599864": {"key":"zurteaga","nombre":"Zuley","nombre_full":"Zuley Urteaga"},
    "51919502385": {"key":"lpasquel","nombre":"Leyla","nombre_full":"Leyla Pasquel"},
    "51912379686": {"key":"lvalencia","nombre":"Linid","nombre_full":"Linid Valencia"},
}

def _menu_cc(tel_cc, nom):
    wa(tel_cc, f"👋 Hola {nom}! Soy el asistente de Torre de Control CPSL.\n\n1️⃣ Enviar reporte del día\n2️⃣ Registrar confirmación de PX\n3️⃣ Reportar devolución\n4️⃣ Ver mis derivados pendientes\n0️⃣ Salir\n\n_Escribe el número de tu opción._", f"SIS→{nom}")

def _flujo_cc(tel, up, texto, cc_info):
    nom, nom_full, cc_key = cc_info["nombre"], cc_info["nombre_full"], cc_info["key"]
    s = get_s(tel) or {}; st = s.get("st_cc","MAIN"); JOSE_TEL = "51919563284"
    if not s or up in {"HOLA","MENU","0","INICIO"}:
        s = {"modo":"CC","cc_key":cc_key,"st_cc":"MAIN"}; set_s(tel, s); _menu_cc(tel, nom); return
    if st == "MAIN":
        if up == "1":
            wa(tel, f"📋 *Reporte del día — {nom_full}*\n\nEscribe tu reporte:\n✅ Confirmados: N\n🔀 Gestionando: N\n🛑 Devoluciones: N\n💬 Notas: texto libre\n\n_O escribe libremente._", f"SIS→{nom}"); s["st_cc"] = "ESPERANDO_REPORTE"; set_s(tel, s)
        elif up == "2":
            wa(tel, f"Escribe el nombre del PX que confirmó asistencia al C1 E27\n\n_Ejemplo: Juan Pérez — equipo 26_\n\n9️⃣ Volver", f"SIS→{nom}"); s["st_cc"] = "ESPERANDO_CONFIRMACION"; set_s(tel, s)
        elif up == "3":
            wa(tel, f"Escribe los datos del PX que solicita devolución:\n\n_Ejemplo: María García — +51999888777 — monto S/250_\n\n9️⃣ Volver", f"SIS→{nom}"); s["st_cc"] = "ESPERANDO_DEVOLUCION"; set_s(tel, s)
        elif up == "4":
            h = []; hist_path = Cfg.HIST
            if os.path.exists(hist_path):
                with open(hist_path, encoding="utf-8") as f: h = json.load(f)
            notifs = [m for m in h if m.get("telefono") == tel and "TORRE DE CONTROL" in m.get("texto","") and "DERIVACIONES" not in m.get("texto","")]
            if notifs:
                lista = "\n".join([f"• [{m['hora']}] {m['texto'][m['texto'].find('Nombre:')+8:m['texto'].find('Tel:')-1].strip()}" for m in notifs[-5:] if 'Nombre:' in m.get('texto','')])
                wa(tel, f"📋 *Tus últimas derivaciones recibidas:*\n\n{lista}\n\n_Para ver el historial completo revisa la Torre de Control._\n\n9️⃣ Volver", f"SIS→{nom}")
            else: wa(tel, f"No tienes derivaciones pendientes registradas.\n\n9️⃣ Volver", f"SIS→{nom}")
        elif up in {"9","VOLVER"}: s["st_cc"] = "MAIN"; set_s(tel, s); _menu_cc(tel, nom)
        else: _menu_cc(tel, nom)
    elif st == "ESPERANDO_REPORTE":
        if up in {"9","VOLVER"}: s["st_cc"] = "MAIN"; set_s(tel, s); _menu_cc(tel, nom); return
        hora_s = ahora().strftime("%d/%m/%Y %H:%M:%S"); reg(tel, nom_full, "", texto, "REPORTE_CC", dir_="IN", staff=nom_full); add_hist(tel, f"CC/{nom}", texto, "in")
        wa(tel, f"✅ Reporte registrado.\n\n_{hora_s}_\n\n0️⃣ Salir | 9️⃣ Menú", f"SIS→{nom}"); wa(JOSE_TEL, f"📊 *REPORTE CC — {nom_full}*\n_{hora_s}_\n\n{texto}", f"SIS→JOSE"); s["st_cc"] = "MAIN"; set_s(tel, s)
    elif st == "ESPERANDO_CONFIRMACION":
        if up in {"9","VOLVER"}: s["st_cc"] = "MAIN"; set_s(tel, s); _menu_cc(tel, nom); return
        hora_s = ahora().strftime("%d/%m/%Y %H:%M:%S"); reg(tel, nom_full, "", texto, "CONFIRMA_CC", dir_="IN", staff=nom_full); add_hist(tel, f"CC/{nom}", texto, "in")
        wa(tel, f"✅ Confirmación registrada:\n_{texto}_\n\n0️⃣ Salir | 9️⃣ Menú", f"SIS→{nom}"); wa(JOSE_TEL, f"✅ *CONFIRMACIÓN registrada por {nom_full}:*\n{texto}\n_{hora_s}_", f"SIS→JOSE"); s["st_cc"] = "MAIN"; set_s(tel, s)
    elif st == "ESPERANDO_DEVOLUCION":
        if up in {"9","VOLVER"}: s["st_cc"] = "MAIN"; set_s(tel, s); _menu_cc(tel, nom); return
        hora_s = ahora().strftime("%d/%m/%Y %H:%M:%S"); reg(tel, nom_full, "", texto, "DEVOLUCION_CC", dir_="IN", staff=nom_full); add_hist(tel, f"CC/{nom}", texto, "in")
        wa(tel, f"⚠️ Devolución registrada:\n_{texto}_\n\n0️⃣ Salir | 9️⃣ Menú", f"SIS→{nom}"); wa(JOSE_TEL, f"⚠️ *DEVOLUCIÓN reportada por {nom_full}:*\n{texto}\n_{hora_s}_", f"SIS→JOSE"); s["st_cc"] = "MAIN"; set_s(tel, s)

# ── FLUJO PRINCIPAL ───────────────────────────────────────────
STOP_W = {"STOP","BAJA","DETENER","NO MAS"}; RESET_W = {"HOLA","MENU","MENÚ","0","INICIO","START","HI"}

def flujo(tel, texto):
    try:
        up = texto.strip().upper()
        if up in STOP_W: del_s(tel); wa(tel,"Has sido dado de baja. Escribe HOLA para reiniciar.\n\n*Crear Poder Sin Límites Perú*","SIS"); reg(tel,"","","STOP","STOP",dir_="SYS"); return
        s = get_s(tel)
        if not s or up in RESET_W:
            if tel in _CC_TELS: s = {"modo":"CC","cc_key":_CC_TELS[tel]["key"],"st_cc":"MAIN"}; set_s(tel, s); _menu_cc(tel, _CC_TELS[tel]["nombre"]); return
            p = perfil_crm(tel); p["_tel"] = tel; s = {"p": p, "st": "MAIN"}; set_s(tel, s); _menu_main(tel, p); return
        if tel in _CC_TELS: _flujo_cc(tel, up, texto, _CC_TELS[tel]); return
        p = s.get("p", {}); p["_tel"] = tel
        if p.get("tipo") != "NUEVO" and not p.get("staff_tel"):
            equipo = p.get("equipo",""); k = cc_por_equipo(equipo) if equipo else cc_libre()
            p["staff_key"], p["staff_tel"], p["staff_nom"] = k, STAFF[k]["tel"], STAFF[k]["nombre"]; s["p"] = p; set_s(tel, s)
        st, sb = s.get("st","MAIN"), s.get("sb")
        if up in {"9","VOLVER"}: s["st"]="MAIN"; s["sb"]=None; set_s(tel,s); _menu_main(tel,p); return
        if st == "DER":
            tel_cc = p.get("staff_tel") or STAFF[cc_libre()]["tel"]; nom_cc = p.get("staff_nom","Coord"); nom_px = p.get("nombre_full") or p.get("nombre",""); nom_full_der = p.get("nombre_full") or nom_px
            wa(tel_cc, f"💬 *Mensaje de {nom_full_der}*\nTel: wa.me/{tel}\n\n{texto}", f"RELAY→{nom_cc}"); wa(tel,"✅ Mensaje entregado a tu coordinadora.\n_Escribe *0* para volver al menú._",p.get("nombre","")); return
        tipo = p.get("tipo","NUEVO")
        if tipo == "IMO": _imo(tel, up, texto, s, p)
        elif tipo == "PX": _px(tel, up, texto, s, p)
        else: _nuevo(tel, up, texto, s, p)
    except Exception as e: logger.error(f"flujo {tel}: {e}", exc_info=True)

def _menu_main(tel, p):
    tipo, nom = p.get("tipo","NUEVO"), p.get("nombre") or "Líder"
    if tipo == "IMO":
        n = len(p.get("pendientes",[])); al = f"\n⚠️ Tienes *{n}* enrolado{'s' if n!=1 else ''} pendiente{'s' if n!=1 else ''} de C1." if n else "\n✅ Todos tus enrolados al día."
        wa(tel, f"👑 *Hola {nom}* — Portal IMO{al}\n\n1️⃣ Ver mis pendientes de C1\n2️⃣ Ver TODOS mis enrolados\n3️⃣ Solicitar ser Aliado C1 E27\n4️⃣ Fechas activas\n5️⃣ Hablar con Coordinación\n0️⃣ Salir\n\n_STOP para darte de baja._", nom)
    elif tipo == "PX":
        nom_cc = p.get("staff_nom","Coordinación"); wa(tel, f"🌟 *Hola {nom}!*\nTu coordinadora: *{nom_cc}*\n\n1️⃣ Confirmar asistencia al C1 Equipo 27\n2️⃣ Fechas y logística\n3️⃣ Inversión y pagos\n4️⃣ Hablar con mi coordinadora\n0️⃣ Salir\n\n_STOP para darte de baja._", nom)
    else: wa(tel, f"🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial — Sede Lima.\n\n1️⃣ Ya participé antes (cambié de número)\n2️⃣ Soy nuevo — quiero información\n0️⃣ Salir\n\n_STOP para darte de baja._", "Sistema")

def _imo(tel, up, texto, s, p):
    nom, pend, st = p.get("nombre","Líder"), p.get("pendientes",[]), s.get("st","MAIN")
    if st == "MAIN":
        if up == "1":
            if pend:
                lista = "\n".join(pend[:20]); lista += f"\n_...y {len(pend)-20} más_" if len(pend)>20 else ""
                wa(tel, f"⏳ *Pendientes de C1 — Equipo 27*\n📅 {Cfg.FECHA}\n📍 {Cfg.LUGAR}\n\n{lista}\n\n¿Cómo avanzan tus gestiones?\n1️⃣ Reportar una confirmación\n2️⃣ Sigo gestionando\n3️⃣ Necesito apoyo de Coordinación\n9️⃣ Volver", nom); s["st"]="IMO_PEND"; set_s(tel,s)
            else: wa(tel,"🎉 ¡Todos tus enrolados ya se sentaron! Felicitaciones.\n\n9️⃣ Volver",nom)
        elif up == "2":
            rows, t9, todos = _get_rows(), n9(tel), []
            for r in rows:
                if n9(r.get("Tel. IMO","")) == t9:
                    nom_px = f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()}"; eq = r.get("Equipo",""); c1 = str(r.get("C1","")).strip().upper(); st_px = "✅ Sentado" if c1=="SI" else "⏳ Pendiente"
                    todos.append(f"• {nom_px} ({eq}) — {st_px}")
            if todos: lista = "\n".join(todos[:25]); lista+=f"\n_...y {len(todos)-25} más_" if len(todos)>25 else ""; wa(tel,f"📋 *Todos tus enrolados:*\n\n{lista}\n\n9️⃣ Volver",nom)
            else: wa(tel,"Sin enrolados vinculados en el sistema.\n\n9️⃣ Volver",nom)
        elif up == "3": nom_cc = notif_cc(p,"Solicita ser Aliado C1 E27",f"IMO: {p.get('imo_nombre',nom)}"); wa(tel, f"✅ Solicitud registrada.\n\nTu coordinadora *{nom_cc}* te escribirá para confirmar tu rol como Aliado.\n\n9️⃣ Volver",nom); reg(tel,nom,"IMO","Solicita ser Aliado","ALIADO",dir_="SYS",staff=nom_cc)
        elif up == "4": wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver",nom)
        elif up == "5": nom_cc = notif_cc(p,"IMO solicita atención directa"); s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Derivado a *{nom_cc}*. Puedes escribirle directamente aquí.",nom)
        elif up == "0": del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA para volver. 🌟",nom)
        else: _menu_main(tel,p)
    elif st == "IMO_PEND":
        if up == "1": s["st"]="IMO_CONF"; set_s(tel,s); wa(tel,"Escribe el nombre de quien confirma.\n_Escribe 9 para volver._",nom)
        elif up == "2": s["st"]="MAIN"; set_s(tel,s); wa(tel,"Perfecto. Cuando tengas confirmaciones escríbenos. 💪\n\n9️⃣ Volver / 0️⃣ Menú",nom)
        elif up == "3": nom_cc = notif_cc(p,"IMO necesita apoyo para gestionar pendientes C1 E27",f"{len(pend)} pendientes"); s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Derivado. *{nom_cc}* te apoyará directamente.",nom)
        else: s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)
    elif st == "IMO_CONF":
        nom_cc = notif_cc(p,"IMO reporta confirmación de enrolado",f"Nombre: '{texto}'"); reg(tel,nom,"IMO",f"Confirma: {texto}","CONF_ENROLADO",dir_="SYS",staff=nom_cc)
        wa(tel, f"✅ *{texto}* registrado como confirmado.\nCoordinación ({nom_cc}) lo procesará.\n\n¿Otra confirmación? Escribe el nombre o *9* para volver.",nom)

def _px(tel, up, texto, s, p):
    nom, nom_cc, st = p.get("nombre","Líder"), p.get("staff_nom","Coordinación"), s.get("st","MAIN")
    if st == "MAIN":
        if up == "1": nom_cc2 = notif_cc(p,"PX CONFIRMA asistencia C1 E27"); reg(tel,p.get("nombre_full",nom),"PX","Confirma C1 E27","CONFIRMA",dir_="SYS",staff=nom_cc2); wa(tel, f"¡Confirmado {nom}! ✅\n\n📍 *{Cfg.LUGAR}*\n🗓 {Cfg.FECHA}\n⏰ {Cfg.REGISTRO}\n\nRopa cómoda y botella de agua. Bloquea los 3 días.\n\nTu coordinadora *{nom_cc2}* recibirá tu confirmación. 💪",nom); del_s(tel)
        elif up == "2": wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver",nom)
        elif up == "3": wa(tel, "💳 *Inversión y Pagos*\n\nBCP — Creación Cuántica E.I.R.L.\nCuenta Soles: *1934218307060*\n\n1️⃣ Enviar voucher a Coordinación\n9️⃣ Volver",nom); s["st"]="PX_PAGO"; set_s(tel,s)
        elif up == "4": nom_cc2 = notif_cc(p,"PX solicita atención directa"); s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Te derivo con *{nom_cc2}*. Escribe tu consulta aquí.",nom)
        elif up == "0": del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA para volver. 🌟",nom)
        else: _menu_main(tel,p)
    elif st == "PX_PAGO":
        if up == "1": nom_cc2 = notif_cc(p,"PX envía voucher de pago"); s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Derivado a *{nom_cc2}*. Adjunta el voucher en el siguiente mensaje.",nom)
        else: s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)

def _nuevo(tel, up, texto, s, p):
    st = s.get("st","MAIN")
    if st == "MAIN":
        if up == "1": s["st"]="NVO_NUM"; set_s(tel,s); wa(tel, "Para encontrar tu registro escríbeme:\n\n*Nombre completo y DNI* en un solo mensaje.\n_Ej: Juan Pérez 12345678_\n\n_Escribe 9 para volver._","Sistema")
        elif up == "2": s["st"]="NVO_INFO"; set_s(tel,s); wa(tel, "🌟 *Crear Poder Sin Límites Perú*\n\nEntrenamientos de liderazgo y transformación de alto rendimiento. Salir del modo automático y crear resultados extraordinarios.\n\n1️⃣ Información del Capítulo 1\n2️⃣ Fechas 2026\n3️⃣ Inversión\n4️⃣ Hablar con Coordinación\n9️⃣ Volver","Sistema")
        elif up == "0": del_s(tel); wa(tel,"Hasta pronto. Escribe HOLA cuando quieras. 🌟","Sistema")
        else: _menu_main(tel,p)
    elif st == "NVO_NUM":
        k = cc_libre(); cc_add(k); tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]
        wa(tel_cc, f"🔍 *VERIFICACIÓN DE IDENTIDAD*\nTel: wa.me/{tel}\nDato: '{texto}'\nBuscar en sistema y actualizar.","SIS")
        p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc; s["p"]=p; s["st"]="DER"; set_s(tel,s)
        wa(tel,f"✅ Datos enviados a Coordinación ({nom_cc}). Te responderán pronto.","Sistema"); reg(tel,texto,"NUEVO",texto,"CAMBIO_NUM",dir_="SYS",staff=nom_cc)
    elif st == "NVO_INFO":
        if up == "1": wa(tel, f"🚀 *Capítulo 1 — El Descubrimiento*\n\n3 días vivenciales para observar los mecanismos que frenan tus resultados. No es una conferencia — es transformación.\n\n*Próxima fecha:* {Cfg.FECHA}\n*Lugar:* {Cfg.LUGAR}\n\n1️⃣ Inscribirme\n9️⃣ Volver","Sistema"); s["st"]="NVO_C1"; set_s(tel,s)
        elif up == "2": wa(tel,FECHAS_MSG+"\n\n9️⃣ Volver","Sistema")
        elif up == "3": wa(tel, "💳 *Inversión*\n\nEl costo es personalizado. Tu coordinadora te dará todos los detalles.\n\n1️⃣ Contactar Coordinación\n9️⃣ Volver","Sistema"); s["st"]="NVO_INV"; set_s(tel,s)
        elif up == "4": k=cc_libre(); cc_add(k); tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]; wa(tel_cc,f"🆕 *NUEVO PROSPECTO*\nTel: wa.me/{tel}","SIS"); p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc; s["p"]=p; s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Derivado a Coordinación ({nom_cc}). Te escribirán pronto.","Sistema")
        elif up == "9": s["st"]="MAIN"; set_s(tel,s); _menu_main(tel,p)
    elif st in ("NVO_C1","NVO_INV"):
        if up == "1": k=cc_libre(); cc_add(k); tel_cc=STAFF[k]["tel"]; nom_cc=STAFF[k]["nombre"]; wa(tel_cc, f"🆕 *NUEVO PROSPECTO INTERESADO*\nTel: wa.me/{tel}\nInterés: {'C1' if st=='NVO_C1' else 'Inversión'}","SIS"); p["staff_key"]=k; p["staff_tel"]=tel_cc; p["staff_nom"]=nom_cc; s["p"]=p; s["st"]="DER"; set_s(tel,s); wa(tel,f"✅ Coordinación ({nom_cc}) te escribirá en breve. 🌟","Sistema")
        elif up == "9": s["st"]="NVO_INFO"; set_s(tel,s); wa(tel,"1️⃣ Info C1\n2️⃣ Fechas\n3️⃣ Inversión\n4️⃣ Coordinación\n9️⃣ Volver","Sistema")

# ── ENDPOINTS ─────────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def wh_get():
    if request.args.get("hub.verify_token")==Cfg.VER_TOKEN: return request.args.get("hub.challenge"),200
    return "error",403

@app.route("/webhook", methods=["POST"])
def wh_post():
    d = request.get_json(silent=True)
    if not d: return jsonify({"status":"ok"}),200
    try:
        chg = d["entry"][0]["changes"][0]["value"]
        if "messages" not in chg: return jsonify({"status":"ok"}),200
        msg = chg["messages"][0]; tel = msg.get("from",""); tipo = msg.get("type","")
        if tipo=="text":
            txt = str(msg["text"]["body"]); s_wh = get_s(tel); p_wh = s_wh.get("p") or perfil_crm(tel)
            nom_d = (p_wh.get("nombre_full") or p_wh.get("imo_nombre") or p_wh.get("nombre") or tel)
            nom_h = f"({p_wh.get('tipo','?')}) {nom_d}"; add_hist(tel, nom_h, txt, "in")
            reg(tel, p_wh.get("nombre",""), p_wh.get("tipo",""), txt, "MSG_IN", staff=p_wh.get("staff_nom",""))
            threading.Thread(target=flujo,args=(tel,txt),daemon=False,name=f"f{tel[-4:]}").start()
        else:
            s_wh = get_s(tel); p_wh = s_wh.get("p") or {"tipo":"?","nombre":None}
            nom_h = f"({p_wh.get('tipo','?')}) {p_wh.get('nombre') or tel}"; add_hist(tel, nom_h, f"[{tipo}]", "in")
            wa(tel,"Por favor responde con texto o el número de tu opción.","SIS")
    except Exception as e: logger.error(f"wh {e}",exc_info=True)
    return jsonify({"status":"ok"}),200

@app.route("/api/historial")
def hist_all():
    """Devuelve historial en formato que espera el panel V110"""
    try:
        merged = {}
        for path in [Cfg.HIST, Cfg.HIST_ALT]:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for m in json.load(f):
                        k = f"{m.get('telefono','')}|{m.get('hora','')}|{m.get('texto','')[:30]}"
                        merged[k] = m
        resultado = sorted(merged.values(), key=lambda x: x.get("hora",""))
        # Formatear para el panel: nombre con (TIPO), hora en DD/MM HH:mm
        formatted = []
        for m in resultado:
            hora_raw = m.get("hora","")
            try:
                if hora_raw and "/" not in hora_raw:
                    dt = datetime.fromisoformat(hora_raw.replace("Z","+00:00"))
                    hora_fmt = dt.astimezone(TZ_LIMA).strftime("%d/%m %H:%M")
                else:
                    hora_fmt = hora_raw
            except: hora_fmt = hora_raw
            nom_raw = m.get("nombre","Desconocido")
            formatted.append({"telefono":str(m.get("telefono")),"nombre":nom_raw,"texto":m.get("texto",""),"tipo":m.get("tipo","in"),"hora":hora_fmt,"coordinadora":m.get("coordinadora")})
        return jsonify(formatted), 200
    except Exception as e: logger.error(f"hist_all {e}"); return jsonify([]), 200

@app.route("/api/historial/<tel>")
def hist_tel(tel):
    try:
        merged = {}
        for path in [Cfg.HIST, Cfg.HIST_ALT]:
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    for m in json.load(f):
                        if str(m.get("telefono",""))==str(tel):
                            k = f"{m.get('hora','')}|{m.get('texto','')[:30]}"; merged[k] = m
        resultado = sorted(merged.values(), key=lambda x: x.get("hora",""))
        return jsonify(resultado), 200
    except Exception as e: logger.error(f"hist_tel {e}"); return jsonify([]), 200

@app.route("/api/carga_coordinadoras")
def carga_cc():
    return jsonify({k:{"nombre":v["nombre"],"casos":_carga.get(k,0),"tel":v["tel"]} for k,v in STAFF.items()}),200

@app.route("/api/enviar",methods=["POST"])
def api_enviar():
    d=request.json or {}; tel=d.get("telefono",""); msg=d.get("mensaje","")
    if not tel or not msg: return jsonify({"error":"faltan datos"}),400
    wa(tel,msg,"PANEL"); reg(tel,"PANEL","MANUAL",msg,"MANUAL_OUT",dir_="OUT")
    return jsonify({"status":"ok"}),200

@app.route("/api/mensaje_simulador",methods=["POST"])
def api_sim():
    d = request.json or {}; tel = d.get("telefono",""); txt = d.get("texto","")
    if not tel or not txt: return jsonify({"error":"faltan datos"}), 400
    s_sim = get_s(tel)
    if not s_sim.get("p"):
        tel_up = tel.upper()
        if "SIM_IMO" in tel_up or "SIM_GRAD" in tel_up:
            p_iny = {"tipo":"IMO","nombre":"Gareth","apellido":"Ramos Pérez","nombre_full":"Gareth Said Ramos Pérez","equipo":"EQUIPO 26","imo_nombre":"Gareth Said Ramos Pérez","imo_tel":tel,"staff_key":"dmoscoso","staff_tel":STAFF["dmoscoso"]["tel"],"staff_nom":STAFF["dmoscoso"]["nombre"],"pendientes":["• Juan Carlos Soto García (EQUIPO 26)","• María Fernanda López Ruiz (EQUIPO 25)","• Carlos Alberto Mendoza (EQUIPO 26)"]}
        elif "SIM_PX" in tel_up:
            p_iny = {"tipo":"PX","nombre":"Kely","apellido":"Arcce Rojas","nombre_full":"Kely Arcce Rojas","equipo":"EQUIPO 26","imo_nombre":"Gareth Said Ramos Pérez","imo_tel":"","staff_key":"jmarin","staff_tel":STAFF["jmarin"]["tel"],"staff_nom":STAFF["jmarin"]["nombre"],"pendientes":[]}
        else:
            p_iny = {"tipo":"NUEVO","nombre":None,"nombre_full":"","staff_key":None,"staff_tel":None,"staff_nom":None,"pendientes":[]}
        if not any(x in tel_up for x in ["SIM_IMO","SIM_PX","SIM_GRAD","SIM_NEW"]):
            p_real = perfil_crm(tel)
            if p_real.get("tipo") != "NUEVO": p_iny = p_real
        s_sim["p"] = p_iny; s_sim["st"] = "MAIN"; set_s(tel, s_sim)
    p_log = s_sim.get("p") or {}; nom_h = f"({p_log.get('tipo','SIM')}) {p_log.get('nombre_full') or p_log.get('nombre') or tel}"
    add_hist(tel, nom_h, txt, "in"); threading.Thread(target=flujo, args=(tel, txt), daemon=True, name=f"sim{tel[-4:]}").start()
    return jsonify({"status":"ok"}), 200

@app.route("/api/test_notif", methods=["POST"])
def test_notif():
    d = request.json or {}; key = d.get("cc","dmoscoso"); msg = d.get("msg","Test de notificación desde Torre de Control")
    tel = STAFF.get(key,{}).get("tel",""); nom = STAFF.get(key,{}).get("nombre","?")
    if not tel: return jsonify({"error":f"CC '{key}' no encontrada"}), 400
    logger.info(f"TEST NOTIF → {nom} ({tel})"); exito = wa(tel, f"🧪 *TEST Torre de Control*\n{msg}\n\nSi ves esto, las notificaciones funcionan ✅", "TEST")
    return jsonify({"enviado":exito,"cc":nom,"tel":tel}), 200

@app.route("/api/solicitar_reporte", methods=["POST"])
def solicitar_reporte():
    d = request.json or {}; dest = d.get("cc","todas"); hora_s = ahora().strftime("%H:%M"); targets = []
    if dest == "todas": targets = list(STAFF.items())
    elif dest in STAFF: targets = [(dest, STAFF[dest])]
    else: return jsonify({"error": f"CC '{dest}' no encontrada"}), 400
    enviados = []
    for key, cc in targets:
        if key not in ("dmoscoso","jmarin","zurteaga"): continue
        ok = wa(cc["tel"], f"📊 *Torre de Control — CPSL Lima*\n\nHola {cc['nombre'].split()[0]}, por favor envía tu reporte del día:\n\n✅ Confirmados hoy: ?\n🔀 En gestión: ?\n🛑 Devoluciones: ?\n💬 Notas:\n\n_Responde este mensaje con los datos o escribe *HOLA* para ver el menú._", f"SIS→JOSE")
        enviados.append({"cc": cc["nombre"], "tel": cc["tel"], "enviado": ok}); logger.info(f"Solicitud de reporte enviada a {cc['nombre']}")
    return jsonify({"ok": True, "enviados": enviados}), 200

@app.route("/api/clear_sessions", methods=["POST"])
def clear_sessions():
    import glob; borradas = 0
    for path in [Cfg.S_REAL, Cfg.S_SIM]:
        if os.path.exists(path):
            with open(path,"w") as f: json.dump({},f); borradas += 1
    logger.info(f"Sesiones borradas ({borradas} archivos)"); return jsonify({"ok":True,"archivos_borrados":borradas}), 200

@app.route("/api/token_status")
def token_status():
    token_ok = bool(Cfg.TOKEN) and len(Cfg.TOKEN) > 20; phone_ok = bool(Cfg.PHONE_ID)
    result = {"token_configurado":token_ok,"phone_id_configurado":phone_ok,"token_len":len(Cfg.TOKEN) if Cfg.TOKEN else 0}
    if token_ok and phone_ok:
        try:
            r = req_lib.get(f"https://graph.facebook.com/v19.0/{Cfg.PHONE_ID}",headers={"Authorization":f"Bearer {Cfg.TOKEN}"},timeout=8)
            result["meta_ok"] = r.status_code == 200; result["meta_resp"] = r.status_code
        except Exception as e: result["meta_ok"] = False; result["meta_err"] = str(e)
    return jsonify(result), 200

@app.route("/status")
def status():
    rows = _get_rows()
    return jsonify({"version":"v109-FIX","status":"activo","csv_filas":len(rows),"csv_path":Cfg.CSV,"csv_ok":len(rows)>0,"hora":ahora().strftime("%d/%m/%Y %H:%M:%S"),"c1_e27":Cfg.FECHA,"carga_cc":{k:v for k,v in _carga.items()}}),200

@app.route("/chat")
def panel():
    try:
        with open(os.path.join(BASE_DIR,"panel_chat.html"),encoding="utf-8") as f: return f.read()
    except: return "<h2>Panel no disponible</h2>",200

# ── WORKER SEGUIMIENTO (con compatibilidad) ───────────────────
try:
    from seguimiento_github import run_seguimiento as _run_seg, _estado as _estado_worker, AUTO as SEG_AUTO, HORA_AUTO as SEG_HORA
    _SEG_OK = True; logger.info(f"✅ Worker seguimiento GitHub cargado (AUTO={SEG_AUTO}, HORA={SEG_HORA})")
except ImportError:
    try:
        from seguimiento_autonomo import run_seguimiento as _run_seg, _estado_worker
        _SEG_OK = True; logger.info("✅ Worker seguimiento_autonomo cargado")
    except ImportError:
        _SEG_OK = False
        _estado_worker = {"corriendo":False,"ok":0,"err":0,"total":0,"ultimo":"No disponible","log":[]}
        def _run_seg(**kw): return {"error":"Worker no encontrado"}
        logger.warning("⚠️ Worker seguimiento no encontrado")

@app.route("/api/seguimiento/estado")
def seg_estado():
    return jsonify(_estado_worker), 200

@app.route("/api/seguimiento/iniciar", methods=["POST"])
def seg_iniciar():
    """✅ FIX: Compatible con cualquier versión de run_seguimiento"""
    try:
        d = request.json or {}; modo = d.get("modo", "ambos")
        if not _SEG_OK: return jsonify({"error": "Worker de seguimiento no disponible"}), 503
        # Verificar qué parámetros acepta run_seguimiento
        sig = inspect.signature(_run_seg); params = sig.parameters
        kwargs = {"modo": modo}
        if "limite_imos" in params: kwargs["limite_imos"] = d.get("limite_imos")
        if "limite_px" in params: kwargs["limite_px"] = d.get("limite_px")
        res = _run_seg(**kwargs)
        return jsonify(res or {"ok": True}), 200
    except Exception as e:
        logger.error(f"Error en seg_iniciar: {e}", exc_info=True)
        return jsonify({"error": str(e), "detalle": "Revisa los logs del servidor"}), 500

@app.route("/api/seguimiento/log")
def seg_log():
    return jsonify(_estado_worker.get("log",[])), 200

@app.route("/api/seguimiento/reenvio", methods=["POST"])
def seg_reenvio():
    if not _SEG_OK: return jsonify({"error":"Worker no disponible"}), 503
    try:
        from seguimiento_autonomo import run_reenvio
        d = request.json or {}; res = run_reenvio(horas_espera = d.get("horas_espera", 48), limite = d.get("limite"))
        return jsonify(res), 200
    except ImportError:
        return jsonify({"error":"Función run_reenvio no disponible"}), 503

@app.route("/api/seguimiento/detectar", methods=["GET"])
def seg_detectar():
    if not _SEG_OK: return jsonify({"error":"Worker no disponible"}), 503
    try:
        from seguimiento_autonomo import detectar_sin_respuesta
        horas = int(request.args.get("horas", 48)); sin_resp = detectar_sin_respuesta(horas_espera=horas)
        return jsonify({"total": len(sin_resp), "contactos": sin_resp[:50]}), 200
    except ImportError:
        return jsonify({"error":"Función detectar_sin_respuesta no disponible"}), 503

@app.route("/api/seguimiento/reenviar", methods=["POST"])
def seg_reenviar():
    d = request.json or {}
    if not _SEG_OK: return jsonify({"error":"Worker no disponible"}), 503
    try:
        from seguimiento_autonomo import run_reenvio
        res = run_reenvio(horas_espera = d.get("horas_espera", 48), limite = d.get("limite"))
        return jsonify(res), 200
    except ImportError:
        return jsonify({"error":"Función run_reenvio no disponible"}), 503

@app.route("/api/seguimiento/sin_respuesta")
def seg_sin_resp():
    if not _SEG_OK: return jsonify([]), 200
    try:
        from seguimiento_autonomo import detectar_sin_respuesta
        horas = int(request.args.get("horas", 48)); resultado = detectar_sin_respuesta(horas_espera=horas)
        return jsonify(resultado), 200
    except ImportError:
        return jsonify([]), 200

if __name__=="__main__":
    logger.info("🚀 CPSL Torre de Control V109-FIX")
    logger.info(f"   CSV: {Cfg.CSV}"); logger.info(f"   CSV existe: {os.path.exists(Cfg.CSV)}")
    logger.info(f"   Filas: {len(_get_rows())}"); logger.info(f"   Sheet: {Cfg.SHEET_ID or 'NO CONFIG'}")
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)),debug=False)
