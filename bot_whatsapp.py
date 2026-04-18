"""
SEGUIMIENTO AUTÓNOMO — 100% desde GitHub + Google Sheets
=========================================================
Sin archivos locales. Todo desde:
  - GitHub: Prospectos_Pendientes_C1_Depurado_Campana.csv (fuente de PX/IMOs)
  - Google Sheet: registro de enviados y respondidos (fuente de verdad)
  - Render /data: solo caché temporal

LÓGICA:
  1. Lee el CSV de GitHub → 721 PX con sus IMOs
  2. Lee el Sheet → sabe quién ya recibió mensaje y quién ya respondió
  3. Envía SOLO a quienes NO recibieron mensaje O llevan +48h sin responder
  4. Registra cada envío en el Sheet
  5. Corre automáticamente si SEGUIMIENTO_AUTO=true
"""

import os, re, csv, json, time, base64, logging, threading
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests as req

log = logging.getLogger("Seguimiento")

TZ_LIMA  = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

def ahora(): return datetime.now(TZ_LIMA)

# ── CONFIG ────────────────────────────────────────────────────
WA_TOKEN   = os.environ.get("WA_TOKEN","")
PHONE_ID   = os.environ.get("WA_PHONE_ID","")
SHEET_ID   = os.environ.get("SHEET_ID","")
CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS","")
SHEET_TAB  = os.environ.get("SHEET_TAB","Hoja 1")
AUTO       = os.environ.get("SEGUIMIENTO_AUTO","false").lower() == "true"
HORA_AUTO  = os.environ.get("SEGUIMIENTO_HORA","09:00")

TEMPLATE   = "invitacion_c1_px"
LANG_CODE  = "es_PE"
FECHA_C1   = "Viernes 01 de Mayo"
PAUSA      = 1.5

# GitHub raw URL del CSV
GITHUB_CSV = ("https://raw.githubusercontent.com/"
              "crearpodersinlimitesperu-cmd/bot-cpsl/main/"
              "Prospectos_Pendientes_C1_Depurado_Campana.csv")

STAFF = {
    "dmoscoso":  {"nombre":"Diana Moscoso",  "tel":"51912379744"},
    "jmarin":    {"nombre":"Joyce Marín",    "tel":"51933599903"},
    "zurteaga":  {"nombre":"Zuley Urteaga",  "tel":"51933599864"},
    "lpasquel":  {"nombre":"Leyla Pasquel",  "tel":"51919502385"},
    "lvalencia": {"nombre":"Linid Valencia", "tel":"51912379686"},
}
CC_POR_EQUIPO = {
    "EQUIPO 26":"dmoscoso","EQUIPO 25":"jmarin","EQUIPO 24":"zurteaga",
    "EQUIPO 23":"zurteaga",
    "EQUIPO 22":"jmarin","EQUIPO 21":"jmarin","EQUIPO 20":"jmarin",    # antes Leyla
    "EQUIPO 19":"dmoscoso","EQUIPO 18":"dmoscoso","EQUIPO 17":"dmoscoso",  # antes Linid
    "EQUIPO 16":"dmoscoso","EQUIPO 15":"dmoscoso","EQUIPO 14":"dmoscoso",
}

# Estado del worker expuesto al panel
_estado = {
    "corriendo":False, "inicio":None,
    "ok":0, "err":0, "total":0,
    "ultimo":"", "log":[], "modo":""
}

# ── SHEETS JWT ────────────────────────────────────────────────
_stok, _stok_exp = None, 0
_stok_lk = threading.Lock()

def _sheets_token():
    global _stok, _stok_exp
    with _stok_lk:
        if _stok and time.time() < _stok_exp - 60: return _stok
        if not CREDS_JSON: return None
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding as cp
            now   = int(time.time())
            creds = json.loads(CREDS_JSON)
            pem   = creds["private_key"].replace("\\n","\n")
            hdr   = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
            pld   = base64.urlsafe_b64encode(json.dumps({
                "iss":creds["client_email"],
                "scope":"https://www.googleapis.com/auth/spreadsheets",
                "aud":"https://oauth2.googleapis.com/token",
                "iat":now,"exp":now+3600
            }).encode()).rstrip(b"=")
            msg_b = hdr+b"."+pld
            pk    = serialization.load_pem_private_key(pem.encode(),password=None)
            sig   = pk.sign(msg_b,cp.PKCS1v15(),hashes.SHA256())
            jwt   = (msg_b+b"."+base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
            r = req.post("https://oauth2.googleapis.com/token",
                data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":jwt},
                timeout=10)
            if r.status_code==200:
                d=r.json(); _stok=d["access_token"]; _stok_exp=now+d.get("expires_in",3600)
                return _stok
        except Exception as e: log.error(f"sheets tok: {e}")
    return None

def sheet_read():
    """Lee el Sheet completo. Retorna lista de filas."""
    if not SHEET_ID: return []
    try:
        tok = _sheets_token()
        if not tok: return []
        tab = SHEET_TAB.replace(" ","%20")
        r = req.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{tab}!A:L",
            headers={"Authorization":f"Bearer {tok}"}, timeout=15)
        if r.status_code == 200:
            return r.json().get("values",[])
        log.error(f"sheet_read {r.status_code}")
    except Exception as e: log.error(f"sheet_read: {e}")
    return []

def sheet_append(fila):
    """Agrega una fila al Sheet."""
    if not SHEET_ID: return
    try:
        tok = _sheets_token()
        if not tok: return
        tab = SHEET_TAB.replace(" ","%20")
        req.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{tab}!A:L:append",
            params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},
            json={"values":[fila]},
            headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
            timeout=10)
    except Exception as e: log.error(f"sheet_append: {e}")

# ── DATOS DESDE GITHUB ────────────────────────────────────────
def cargar_csv_github():
    """Descarga el CSV desde GitHub. Retorna lista de dicts."""
    try:
        r = req.get(GITHUB_CSV, timeout=20)
        if r.status_code == 200:
            lines  = r.text.splitlines()
            reader = csv.DictReader(lines)
            rows   = list(reader)
            log.info(f"CSV GitHub: {len(rows)} filas")
            return rows
        log.error(f"CSV GitHub {r.status_code}")
    except Exception as e:
        log.error(f"CSV GitHub error: {e}")
    # Fallback: usar CSV local si existe
    local = os.path.join(BASE_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")
    if os.path.exists(local):
        with open(local, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        log.info(f"CSV local fallback: {len(rows)} filas")
        return rows
    return []

# ── UTILIDADES ────────────────────────────────────────────────
def norm(t):
    t = re.sub(r'\D','',str(t or ''))
    if t.startswith("51") and len(t)==11: return t
    if len(t)==9 and t.startswith("9"): return "51"+t
    return t

def nc(s):
    p = str(s or '').strip().split()
    return ' '.join(x.title() for x in p[:4]) if p else ''

def np_(s):
    p = [x for x in str(s or '').strip().split() if len(x)>2]
    if not p: return str(s).strip().title()
    if len(p)>=3: return p[2].title()
    if len(p)==2: return p[1].title()
    return p[0].title()

def eq_num(eq):
    m = re.search(r'\d+', str(eq or ''))
    return int(m.group()) if m else 0

def add_log(msg, nivel="INFO"):
    _estado["log"].append({"hora":ahora().strftime("%H:%M:%S"),"nivel":nivel,"msg":msg})
    if len(_estado["log"]) > 300: _estado["log"] = _estado["log"][-300:]
    if nivel == "ERROR": log.error(msg)
    else: log.info(msg)

# ── ANÁLISIS DEL SHEET ────────────────────────────────────────
def analizar_sheet():
    """
    Lee el Sheet y retorna:
    - ya_enviados: set de tels que ya recibieron mensaje de seguimiento
    - respondieron: set de tels que ya respondieron (tienen MSG_IN)
    - ultimo_envio: dict tel → datetime del último envío
    """
    filas = sheet_read()
    ya_enviados  = set()
    respondieron = set()
    ultimo_envio = {}

    EVENTOS_ENVIO = {"SEGUIMIENTO_IMO","SEGUIMIENTO_PX","BOT_OUT","CONFIRMA",
                     "SOLICITUD_ALIADO","IMO_CONFIRMA_ENROLADO"}

    for fila in filas[1:]:  # skip header
        if len(fila) < 9: continue
        try:
            fecha_str = str(fila[0]).strip()
            direccion = str(fila[1]).strip().upper()
            tel       = str(fila[2]).strip()
            evento    = str(fila[8]).strip().upper() if len(fila)>8 else ""

            if not tel or len(tel) < 9: continue

            if direccion == "OUT" or evento in EVENTOS_ENVIO:
                ya_enviados.add(tel)
                # Guardar fecha del último envío
                try:
                    dt = datetime.strptime(fecha_str, "%d/%m/%Y %H:%M:%S")
                    dt = dt.replace(tzinfo=TZ_LIMA)
                    if tel not in ultimo_envio or dt > ultimo_envio[tel]:
                        ultimo_envio[tel] = dt
                except: pass

            if direccion == "IN":
                respondieron.add(tel)
        except: continue

    return ya_enviados, respondieron, ultimo_envio

# ── ENVÍO WA ──────────────────────────────────────────────────
def wa_text(tel, txt):
    if not WA_TOKEN: return False
    try:
        r = req.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,
                  "type":"text","text":{"body":txt}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"}, timeout=10)
        return r.status_code == 200
    except Exception as e: log.error(f"wa_text: {e}"); return False

def wa_template(tel, pila):
    """
    Envío de seguimiento.
    - Si la plantilla está aprobada (TEMPLATE_APROBADA=true) → usa template de Meta
    - Si no → envía texto libre (requiere ventana 24h abierta, costo $0)
    """
    if not WA_TOKEN: return False, "Sin token"

    usar_template = os.environ.get("TEMPLATE_APROBADA","").lower() == "true"

    if usar_template:
        # Usar plantilla aprobada por Meta
        nombre_tpl = os.environ.get("WA_TEMPLATE_NAME", TEMPLATE)
        try:
            r = req.post(
                f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
                json={"messaging_product":"whatsapp","to":tel,"type":"template",
                      "template":{"name":nombre_tpl,"language":{"code":LANG_CODE},
                      "components":[{"type":"body","parameters":[
                          {"type":"text","text":pila},
                          {"type":"text","text":FECHA_C1}
                      ]}]}},
                headers={"Authorization":f"Bearer {WA_TOKEN}",
                         "Content-Type":"application/json"}, timeout=15)
            if r.status_code == 200:
                return True, r.json().get("messages",[{}])[0].get("id","")
            err = r.json().get("error",{}).get("message",r.text[:80])
            # Si falla por template inexistente, caer en texto libre
            if "132001" in str(err) or "132000" in str(err):
                log.warning(f"Template fallo ({err}) — usando texto libre para {tel}")
            else:
                return False, err
        except Exception as e:
            log.error(f"wa_template error: {e}")

    # ── TEXTO LIBRE (ventana 24h abierta, $0 costo) ───────────────
    msg = (
        "Hola " + pila + " 👋\n\n"
        "Te escribimos desde *Crear Poder Sin Límites Perú*.\n"
        "Tienes un cupo reservado para *C1 E27*:\n"
        "📅 Viernes 01, Sábado 02 y Domingo 03 de Mayo\n"
        "Hotel José Antonio Deluxe, Miraflores.\n\n"
        "¿Confirmas tu asistencia?\n\n"
        "1️⃣ Sí, confirmo\n"
        "2️⃣ Necesito más info\n"
        "3️⃣ No puedo asistir")
    try:
        r = req.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,
                  "type":"text","text":{"body":msg}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"}, timeout=15)
        if r.status_code == 200:
            return True, r.json().get("messages",[{}])[0].get("id","")
        err = r.json().get("error",{}).get("message",r.text[:80])
        return False, err
    except Exception as e:
        return False, str(e)

def notif_cc(cc_key, nom_px, tel_px, motivo):
    cc = STAFF.get(cc_key, STAFF["dmoscoso"])
    wa_text(cc["tel"],
        f"🚨 *TORRE DE CONTROL — CPSL Lima*\n\n"
        f"*Nombre:* {nom_px}\n"
        f"*Tel:* wa.me/{tel_px}\n"
        f"*Asunto:* {motivo}")
    return cc["nombre"]

# ══════════════════════════════════════════════════════════════
# WORKER PRINCIPAL
# ══════════════════════════════════════════════════════════════
def run_seguimiento(modo="ambos", horas_reenvio=48, limite=None):
    """
    Seguimiento 100% desde GitHub + Sheet.
    modo: 'px' | 'imos' | 'ambos'
    horas_reenvio: reenviar a quien lleva N horas sin responder
    """
    global _estado
    if _estado["corriendo"]:
        return {"error":"Ya hay un seguimiento en curso"}

    _estado.update({"corriendo":True,"inicio":ahora().isoformat(),
                    "ok":0,"err":0,"total":0,"ultimo":"Iniciando...","log":[],"modo":modo})

    def _run():
        try:
            add_log("Cargando CSV desde GitHub...")
            rows = cargar_csv_github()
            if not rows:
                add_log("CSV vacío o no accesible","ERROR"); return

            add_log("Leyendo Google Sheet...")
            ya_enviados, respondieron, ultimo_envio = analizar_sheet()
            ahora_dt = ahora()
            add_log(f"Sheet: {len(ya_enviados)} enviados, {len(respondieron)} respondieron")

            # ── Construir lista de candidatos ─────────────────
            # Agrupar PX por IMO
            imos_map = defaultdict(list)
            px_list  = []

            for r in rows:
                tel_px  = norm(str(r.get("Teléfono","") or ''))
                tel_imo = norm(re.sub(r'\D','',str(r.get("Tel. IMO","") or ''))[-9:])
                equipo  = str(r.get("Equipo","")).strip()
                nom_px  = f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()}".strip()
                nom_imo = str(r.get("IMO","")).strip()

                if tel_imo and len(tel_imo)==11:
                    imos_map[tel_imo].append({
                        "tel_px":tel_px,"nom_px":nom_px,
                        "equipo":equipo,"nom_imo":nom_imo
                    })

                if tel_px and len(tel_px)==11:
                    px_list.append({
                        "tel":tel_px,"nombre":nom_px,
                        "pila":np_(r.get("Nombre","")),
                        "equipo":equipo,"eq_num":eq_num(equipo),
                        "cc_key":CC_POR_EQUIPO.get(equipo,"dmoscoso")
                    })

            # Filtrar candidatos:
            # - No enviados: nunca contactados
            # - Con reenvío: enviados hace más de horas_reenvio y sin respuesta
            def necesita_contacto(tel):
                if tel not in ya_enviados: return True, "primer_contacto"
                if tel in respondieron:    return False, "ya_respondio"
                ult = ultimo_envio.get(tel)
                if ult:
                    horas = (ahora_dt - ult).total_seconds() / 3600
                    if horas >= horas_reenvio: return True, f"reenvio_{int(horas)}h"
                return False, "reciente"

            cands_imo = []
            cands_px  = []

            if modo in ("imos","ambos"):
                for tel_imo, pxs in imos_map.items():
                    ok, razon = necesita_contacto(tel_imo)
                    if not ok: continue
                    eq_top = max([p["equipo"] for p in pxs],
                                 key=lambda x: eq_num(x)) if pxs else ""
                    cands_imo.append({
                        "tel":tel_imo,
                        "nom":nc(pxs[0]["nom_imo"]),
                        "pila":np_(pxs[0]["nom_imo"]),
                        "n_px":len(pxs),
                        "equipo":eq_top,
                        "cc_key":CC_POR_EQUIPO.get(eq_top,"dmoscoso"),
                        "razon":razon
                    })
                cands_imo.sort(key=lambda x:(-eq_num(x["equipo"]),-x["n_px"]))

            if modo in ("px","ambos"):
                for p in px_list:
                    ok, razon = necesita_contacto(p["tel"])
                    if not ok: continue
                    cands_px.append({**p,"razon":razon})
                cands_px.sort(key=lambda x:-x["eq_num"])

            total = len(cands_imo) + len(cands_px)
            if limite: 
                cands_imo = cands_imo[:limite//2]
                cands_px  = cands_px[:limite//2]
                total = len(cands_imo) + len(cands_px)

            _estado["total"] = total
            add_log(f"Candidatos: {len(cands_imo)} IMOs + {len(cands_px)} PX = {total} total")

            if total == 0:
                add_log("Sin candidatos — todos contactados o respondieron ✅"); return

            # ── Enviar IMOs ───────────────────────────────────
            for i, c in enumerate(cands_imo, 1):
                _estado["ultimo"] = f"IMO {i}/{len(cands_imo)}: {c['nom'][:25]}"
                ok, res = wa_template(c["tel"], c["pila"])
                hora_s  = ahora().strftime("%d/%m/%Y %H:%M:%S")
                if ok:
                    _estado["ok"] += 1
                    add_log(f"✅ IMO {c['nom'][:30]} ({c['n_px']} PX) [{c['razon']}]")
                    sheet_append([hora_s,"OUT",c["tel"],c["nom"],"","IMO",
                                  STAFF[c["cc_key"]]["nombre"],"plantilla",
                                  f"SEGUIMIENTO_IMO","",str(c["n_px"]),res])
                else:
                    _estado["err"] += 1
                    add_log(f"❌ {c['pila']}: {res[:50]}","ERROR")
                time.sleep(PAUSA)

            # ── Enviar PX ─────────────────────────────────────
            for i, p in enumerate(cands_px, 1):
                _estado["ultimo"] = f"PX {i}/{len(cands_px)}: {p['nombre'][:25]}"
                ok, res = wa_template(p["tel"], p["pila"])
                hora_s  = ahora().strftime("%d/%m/%Y %H:%M:%S")
                if ok:
                    _estado["ok"] += 1
                    add_log(f"✅ PX {p['nombre'][:30]} ({p['equipo']}) [{p['razon']}]")
                    sheet_append([hora_s,"OUT",p["tel"],p["nombre"],"","PX",
                                  STAFF[p["cc_key"]]["nombre"],"plantilla",
                                  f"SEGUIMIENTO_PX",p["equipo"],"",res])
                else:
                    _estado["err"] += 1
                    add_log(f"❌ {p['pila']}: {res[:50]}","ERROR")
                time.sleep(PAUSA)

            add_log(f"✅ COMPLETADO — {_estado['ok']} enviados / {_estado['err']} errores")

        except Exception as e:
            add_log(f"ERROR CRÍTICO: {e}","ERROR")
            log.error(f"run_seguimiento: {e}", exc_info=True)
        finally:
            _estado["corriendo"] = False
            _estado["ultimo"]    = "Completado"

    threading.Thread(target=_run, daemon=False, name="seg-github").start()
    return {"iniciado":True, "modo":modo, "horas_reenvio":horas_reenvio}

# ── SCHEDULER AUTOMÁTICO ──────────────────────────────────────
def _scheduler():
    while True:
        try:
            if AUTO and not _estado["corriendo"]:
                hora_actual = ahora().strftime("%H:%M")
                if hora_actual == HORA_AUTO:
                    log.info(f"Scheduler: lanzando seguimiento automático ({HORA_AUTO})")
                    run_seguimiento(modo="ambos", horas_reenvio=48)
        except Exception as e: log.error(f"scheduler: {e}")
        time.sleep(60)

# ── SOLICITUD AUTOMÁTICA DE REPORTES A CCs ───────────────────
HORA_REPORTE = os.environ.get("REPORTE_HORA","12:30")  # default 12:30pm

def _scheduler_reportes():
    """
    Scheduler de reportes:
    - A las 12:30 → solicita reporte a Diana, Zuley, Joyce
    - A las 14:30 → recordatorio a quienes no respondieron
    - A las 15:00 → envía consolidado a José aunque falten reportes
    """
    import requests as req2
    BOT_URL   = os.environ.get("BOT_URL","https://bot-cpsl.onrender.com")
    JOSE_TEL  = "51919563284"
    ya_solicitado   = False
    ya_recordatorio = False
    ya_consolidado  = False
    ultimo_dia      = None

    while True:
        try:
            ahora_dt   = datetime.now(TZ_LIMA)
            hora_actual = ahora_dt.strftime("%H:%M")
            dia_actual  = ahora_dt.strftime("%d/%m/%Y")

            # Reset diario
            if dia_actual != ultimo_dia:
                ya_solicitado   = False
                ya_recordatorio = False
                ya_consolidado  = False
                ultimo_dia      = dia_actual

            # 12:30 → Solicitar reportes a todas las CCs
            if hora_actual == HORA_REPORTE and not ya_solicitado:
                log.info(f"Solicitando reportes a coordinadoras ({HORA_REPORTE})")
                req2.post(f"{BOT_URL}/api/solicitar_reporte",
                         json={"cc":"todas"}, timeout=10)
                ya_solicitado = True

            # 14:30 → Recordatorio a quien no respondió
            if hora_actual == "14:30" and not ya_recordatorio:
                try:
                    r = req2.get(f"{BOT_URL}/api/reporte_consolidado", timeout=10)
                    d = r.json()
                    pendientes = d.get("pendientes", [])
                    if pendientes:
                        log.info(f"Recordatorio a: {pendientes}")
                        # Reenviar solicitud solo a los pendientes
                        for nom in pendientes:
                            # Buscar tel por nombre
                            CCS_TELS = {
                                "Diana Moscoso":  "51912379744",
                                "Joyce Marín":    "51933599903",
                                "Zuley Urteaga":  "51933599864",
                                "Leyla Pasquel":  "51919502385",
                                "Linid Valencia": "51912379686",
                            }
                            tel = CCS_TELS.get(nom)
                            if tel:
                                req2.post(f"{BOT_URL}/api/enviar",
                                    json={"telefono": tel,
                                          "mensaje": f"⏰ *Recordatorio* {nom.split()[0]}, aún no hemos recibido tu reporte del día. Por favor envíalo cuando puedas. Escribe *HOLA* para acceder al menú."},
                                    timeout=10)
                except Exception as e:
                    log.error(f"recordatorio_reportes: {e}")
                ya_recordatorio = True

            # 15:00 → Enviar consolidado a José aunque falten
            if hora_actual == "15:00" and not ya_consolidado:
                try:
                    r = req2.get(f"{BOT_URL}/api/reporte_consolidado", timeout=10)
                    d = r.json()
                    consolidado = d.get("consolidado")
                    pendientes  = d.get("pendientes", [])
                    reportes_n  = d.get("reportes", 0)
                    if consolidado:
                        msg_cons = "CONSOLIDADO DIARIO CPSL Lima\n\n" + str(consolidado)
                        req2.post(f"{BOT_URL}/api/enviar",
                            json={"telefono": JOSE_TEL, "mensaje": msg_cons},
                            timeout=10)
                    elif reportes_n == 0:
                        noms = ", ".join(pendientes) if pendientes else "Todas"
                        msg_sin = "Sin reportes recibidos hoy. Pendientes: " + noms
                        req2.post(f"{BOT_URL}/api/enviar",
                            json={"telefono": JOSE_TEL, "mensaje": msg_sin},
                            timeout=10)
                except Exception as e:
                    log.error(f"consolidado_jose: {e}")
                ya_consolidado = True

        except Exception as e:
            log.error(f"scheduler_reportes error: {e}")
        time.sleep(60)

if AUTO:
    threading.Thread(target=_scheduler, daemon=True, name="scheduler").start()
    log.info(f"Scheduler activo — seguimiento diario a {HORA_AUTO}")
    threading.Thread(target=_scheduler_reportes, daemon=True, name="scheduler-reportes").start()
    log.info(f"Scheduler reportes activo — solicitará reportes a las {HORA_REPORTE}")
