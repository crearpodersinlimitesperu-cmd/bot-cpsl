"""
SEGUIMIENTO AUTÓNOMO — CPSL Lima
=================================
Corre como Background Worker en Render (mismo repo que el bot).
Contacta IMOs y PX sin respuesta, actualiza Google Sheets,
notifica coordinadoras con nombre completo + asunto.

ACTIVACIÓN:
  - Endpoint POST /api/seguimiento/iniciar  (desde el panel)
  - Variable SEGUIMIENTO_AUTO=true + SEGUIMIENTO_HORA=09:00 (schedule)
  - Manual: python seguimiento_autonomo.py

ENV VARS RENDER:
  WA_TOKEN, WA_PHONE_ID, SHEET_ID, GOOGLE_CREDENTIALS,
  SEGUIMIENTO_AUTO (true/false), SEGUIMIENTO_HORA (HH:MM)
"""

import os, csv, re, json, time, base64, logging, threading, queue
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import requests as req

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("Seguimiento")

TZ_LIMA = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

def ahora(): return datetime.now(TZ_LIMA)

# ── CONFIG ────────────────────────────────────────────────────
WA_TOKEN   = os.environ.get("WA_TOKEN","")
PHONE_ID   = os.environ.get("WA_PHONE_ID","")
SHEET_ID   = os.environ.get("SHEET_ID","")
CREDS_JSON = os.environ.get("GOOGLE_CREDENTIALS","")
SHEET_TAB  = os.environ.get("SHEET_TAB","Hoja 1")
AUTO       = os.environ.get("SEGUIMIENTO_AUTO","false").lower()=="true"
HORA_AUTO  = os.environ.get("SEGUIMIENTO_HORA","09:00")

TEMPLATE_IMO = "invitacion_c1_px"   # {{1}}=nombre {{2}}=fecha
TEMPLATE_PX  = "invitacion_c1_px"   # misma plantilla para PX
LANG_CODE    = "es_PE"
FECHA_C1     = "Viernes 01 de Mayo"
PAUSA        = 1.5

CSV_PX    = os.path.join(BASE_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")
PROG_FILE = os.path.join(DATA_DIR, "progreso_seguimiento.json")
LOG_FILE  = os.path.join(DATA_DIR, "log_seguimiento.json")

STAFF = {
    "dmoscoso": {"nombre":"Diana Moscoso",  "tel":"51912379744"},
    "jmarin":   {"nombre":"Joyce Marín",    "tel":"51933599903"},
    "lpasquel": {"nombre":"Leyla Pasquel",  "tel":"51919502385"},
    "zurteaga": {"nombre":"Zuley Urteaga",  "tel":"51933599864"},
}
_carga = {k:0 for k in STAFF}
def cc_libre(): return min(_carga, key=_carga.get)

# Estado del worker en memoria — expuesto al panel
_estado_worker = {
    "corriendo": False,
    "inicio": None,
    "ok": 0, "err": 0, "total": 0,
    "ultimo": "", "log": []
}

# ── GOOGLE SHEETS JWT ─────────────────────────────────────────
_stok, _stok_exp = None, 0
_stok_lk = threading.Lock()

def sheets_tok():
    global _stok, _stok_exp
    with _stok_lk:
        if _stok and time.time() < _stok_exp-60: return _stok
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
                data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer",
                      "assertion":jwt},timeout=10)
            if r.status_code==200:
                d=r.json(); _stok=d["access_token"]
                _stok_exp=now+d.get("expires_in",3600); return _stok
        except Exception as e: log.error(f"tok err {e}")
    return None

def sheets_append(fila):
    """Agrega fila al Google Sheet."""
    if not SHEET_ID: return
    try:
        tok = sheets_tok()
        if not tok: return
        tab = SHEET_TAB.replace(" ","%20")
        req.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{tab}!A:L:append",
            params={"valueInputOption":"RAW","insertDataOption":"INSERT_ROWS"},
            json={"values":[fila]},
            headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"},
            timeout=10
        )
    except Exception as e: log.error(f"sheets {e}")

# ── ENVÍO WA ──────────────────────────────────────────────────
def wa_text(tel, txt):
    try:
        req.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,
                  "type":"text","text":{"body":txt}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"},timeout=10)
    except Exception as e: log.error(f"wa_text {e}")

def wa_template(tel, nombre_pila, template=TEMPLATE_IMO):
    try:
        r = req.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,"type":"template",
                  "template":{"name":template,"language":{"code":LANG_CODE},
                  "components":[{"type":"body","parameters":[
                      {"type":"text","text":nombre_pila},
                      {"type":"text","text":FECHA_C1},
                  ]}]}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"},timeout=15)
        if r.status_code==200:
            return True, r.json().get("messages",[{}])[0].get("id","")
        return False, r.json().get("error",{}).get("message",r.text[:100])
    except Exception as e:
        return False, str(e)

# ── UTILIDADES ────────────────────────────────────────────────
def norm(t):
    t = re.sub(r'\D','',str(t or ''))
    if t.startswith("51") and len(t)==11: return t
    if len(t)==9 and t.startswith("9"): return "51"+t
    return t

def nc(s):   # nombre completo legible
    p = str(s or '').strip().split()
    return ' '.join(x.title() for x in p[:4]) if p else ''

def np_(s):  # primer nombre
    p = [x for x in str(s or '').strip().split() if len(x)>2]
    return p[0].title() if p else str(s).strip().title()

def eq_max(pxs):
    nums = [int(m.group()) for r in pxs
            for m in [re.search(r'\d+',str(r.get("Equipo","")))] if m]
    return max(nums) if nums else 0

def cargar_prog():
    if os.path.exists(PROG_FILE):
        with open(PROG_FILE,encoding="utf-8") as f: return json.load(f)
    return {"env_imos":[],"env_px":[],"notif":[]}

def guardar_prog(p):
    with open(PROG_FILE,"w",encoding="utf-8") as f:
        json.dump(p,f,ensure_ascii=False,indent=2)

def add_log(msg, nivel="INFO"):
    _estado_worker["log"].append({
        "hora": ahora().strftime("%H:%M:%S"),
        "nivel": nivel, "msg": msg
    })
    if len(_estado_worker["log"]) > 500:
        _estado_worker["log"] = _estado_worker["log"][-500:]
    if nivel=="ERROR": log.error(msg)
    else:              log.info(msg)

def notif_cc(tel, nom, motivo, n_px, px_lst=None, tipo="IMO"):
    k = cc_libre(); c = STAFF[k]; _carga[k]+=1
    px_txt = ""
    if px_lst:
        px_txt = "\n*Enrolados pendientes:*\n"+"\n".join(f"• {p}" for p in px_lst[:10])
    icono = "👑" if tipo=="IMO" else "🚀"
    wa_text(c["tel"],
        f"{icono} *SEGUIMIENTO {tipo} — CPSL Lima*\n\n"
        f"*{'IMO' if tipo=='IMO' else 'Prospecto'}:* {nom}\n"
        f"*Tel:* wa.me/{tel}\n"
        f"*PX pendientes:* {n_px}\n"
        f"*Asunto:* {motivo}{px_txt}"
    )
    return c["nombre"]

# ── CARGA DE DATOS ────────────────────────────────────────────
def cargar_imos():
    """Agrupa PX por IMO. Retorna dict tel_imo → {nom, pxs}"""
    if not os.path.exists(CSV_PX): return {}
    imos = defaultdict(list)
    with open(CSV_PX,encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            raw = re.sub(r'\D','',str(r.get("Tel. IMO","") or ''))
            if raw.startswith("51") and len(raw)==11: t=raw
            elif len(raw)==9 and raw.startswith("9"):  t="51"+raw
            else: continue
            imos[t].append(r)
    return imos

def cargar_px():
    """Retorna lista de PX con teléfono válido."""
    if not os.path.exists(CSV_PX): return []
    pxs = []
    with open(CSV_PX,encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            raw = re.sub(r'\D','',str(r.get("Teléfono","") or ''))
            if raw.startswith("51") and len(raw)==11: t=raw
            elif len(raw)==9 and raw.startswith("9"):  t="51"+raw
            else: continue
            pxs.append({
                "tel":      t,
                "nombre":   nc(r.get("Nombre","")),
                "apellido": nc(r.get("Apellido","")),
                "pila":     np_(r.get("Nombre","")),
                "equipo":   r.get("Equipo",""),
                "imo":      r.get("IMO","").strip(),
                "tel_imo":  norm(re.sub(r'\D','',str(r.get("Tel. IMO","") or ''))[-9:]),
                "eq_num":   int(m.group()) if (m:=re.search(r'\d+',r.get("Equipo",""))) else 0,
            })
    return pxs

# ══════════════════════════════════════════════════════════════
# WORKER PRINCIPAL
# ══════════════════════════════════════════════════════════════
def run_seguimiento(modo="ambos", limite_imos=None, limite_px=None):
    """
    modo: 'imos' | 'px' | 'ambos'
    Corre seguimiento de IMOs y/o PX sin respuesta.
    """
    global _estado_worker
    if _estado_worker["corriendo"]:
        return {"error": "Ya hay un seguimiento en curso"}

    _estado_worker.update({
        "corriendo": True, "inicio": ahora().isoformat(),
        "ok": 0, "err": 0, "total": 0,
        "ultimo": "Iniciando...", "log": []
    })

    def _run():
        try:
            prog = cargar_prog()
            ya_env_imos = set(prog.get("env_imos",[]))
            ya_env_px   = set(prog.get("env_px",[]))
            ya_notif    = set(prog.get("notif",[]))
            imos_map    = cargar_imos()
            px_list     = cargar_px()

            add_log(f"CSV cargado: {len(imos_map)} IMOs, {len(px_list)} PX")

            total_env = 0

            # ── PASO 1: IMOs ──────────────────────────────────
            if modo in ("imos","ambos"):
                cands_imo = []
                for tel, pxs in imos_map.items():
                    if tel in ya_env_imos: continue
                    nom  = nc(pxs[0].get("IMO",""))
                    pila = np_(pxs[0].get("IMO",""))
                    px_lst = [f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()} ({r.get('Equipo','')})"
                              for r in pxs]
                    cands_imo.append({
                        "tel":tel,"nom":nom,"pila":pila,
                        "n_px":len(pxs),"eq_max":eq_max(pxs),
                        "px":px_lst
                    })
                cands_imo.sort(key=lambda x:(-x["eq_max"],-x["n_px"]))
                if limite_imos: cands_imo=cands_imo[:limite_imos]

                add_log(f"IMOs a contactar: {len(cands_imo)}")
                _estado_worker["total"] += len(cands_imo)

                for i, c in enumerate(cands_imo, 1):
                    _estado_worker["ultimo"] = f"IMO {i}/{len(cands_imo)}: {c['nom'][:30]}"
                    exito, res = wa_template(c["tel"], c["pila"], TEMPLATE_IMO)
                    hora_s = ahora().strftime("%d/%m/%Y %H:%M:%S")

                    if exito:
                        _estado_worker["ok"] += 1
                        ya_env_imos.add(c["tel"])
                        prog["env_imos"] = list(ya_env_imos)
                        guardar_prog(prog)
                        add_log(f"✅ IMO {c['nom'][:35]} ({c['n_px']} PX)")
                        sheets_append([
                            hora_s,"OUT",c["tel"],c["nom"],"","IMO",
                            "","plantilla_enviada","SEGUIMIENTO_IMO","",c["n_px"],res
                        ])
                        total_env += 1
                    else:
                        _estado_worker["err"] += 1
                        add_log(f"❌ IMO {c['pila']} — {res[:60]}", "ERROR")

                    time.sleep(PAUSA)

            # ── PASO 2: PX ────────────────────────────────────
            if modo in ("px","ambos"):
                # Solo PX de E26 y E25 (los más urgentes)
                cands_px = [p for p in px_list
                            if p["tel"] not in ya_env_px and p["eq_num"]>=25]
                cands_px.sort(key=lambda x:(-x["eq_num"]))
                if limite_px: cands_px=cands_px[:limite_px]

                add_log(f"PX E25/E26 a contactar: {len(cands_px)}")
                _estado_worker["total"] += len(cands_px)

                for i, p in enumerate(cands_px, 1):
                    nom_full = f"{p['nombre']} {p['apellido']}".strip()
                    _estado_worker["ultimo"] = f"PX {i}/{len(cands_px)}: {nom_full[:30]}"
                    exito, res = wa_template(p["tel"], p["pila"], TEMPLATE_PX)
                    hora_s = ahora().strftime("%d/%m/%Y %H:%M:%S")

                    if exito:
                        _estado_worker["ok"] += 1
                        ya_env_px.add(p["tel"])
                        prog["env_px"] = list(ya_env_px)
                        guardar_prog(prog)
                        add_log(f"✅ PX {nom_full[:35]} ({p['equipo']})")
                        sheets_append([
                            hora_s,"OUT",p["tel"],nom_full,"","PX",
                            p["imo"],"plantilla_enviada","SEGUIMIENTO_PX",p["equipo"],"",res
                        ])
                        total_env += 1
                    else:
                        _estado_worker["err"] += 1
                        add_log(f"❌ PX {p['pila']} — {res[:60]}", "ERROR")

                    time.sleep(PAUSA)

            # ── PASO 3: Notificar no-quieren ──────────────────
            # Leer historial del Sheet para detectar NO ASISTE/STOP
            # (el bot ya registra cada respuesta en Sheets)
            # Aquí revisamos sesiones del bot en /data/sesiones.json
            ses_path = os.path.join(DATA_DIR,"sesiones.json")
            if os.path.exists(ses_path):
                with open(ses_path,encoding="utf-8") as f:
                    sesiones = json.load(f)
                for tel, s in sesiones.items():
                    p = s.get("p",{})
                    st = s.get("st","")
                    if tel in ya_notif: continue
                    # Detectar textos de no-quieren en el historial del bot
                    # (el bot actualiza el estado en sesion cuando detecta NO ASISTE)
                    if st in ("NO_ASISTE","STOP","DEVOLUCION"):
                        nom = p.get("nombre_full") or p.get("nombre","")
                        tipo = p.get("tipo","PX")
                        n_px = len(p.get("pendientes",[]))
                        nom_coord = notif_cc(tel, nom,
                            "Declina participación — gestionar devolución si aplica",
                            n_px, p.get("pendientes",[]), tipo)
                        ya_notif.add(tel)
                        prog["notif"] = list(ya_notif)
                        guardar_prog(prog)
                        add_log(f"📢 Notificado {nom} → {nom_coord}")
                        sheets_append([
                            ahora().strftime("%d/%m/%Y %H:%M:%S"),
                            "SYS",tel,nom,"",tipo,"",
                            f"NO_QUIERE:{st}",f"NOTIF→{nom_coord}","","",""
                        ])
                        time.sleep(1.0)

            add_log(f"✅ COMPLETADO — {_estado_worker['ok']} enviados, {_estado_worker['err']} errores")

        except Exception as e:
            add_log(f"ERROR CRÍTICO: {e}", "ERROR")
        finally:
            _estado_worker["corriendo"] = False
            _estado_worker["ultimo"] = "Completado"

    threading.Thread(target=_run, daemon=False, name="worker-seguimiento").start()
    return {"iniciado": True, "total_estimado": _estado_worker["total"]}

# ── SCHEDULER ────────────────────────────────────────────────
def _scheduler():
    """Dispara seguimiento automático a la hora configurada."""
    while True:
        try:
            ahora_h = ahora().strftime("%H:%M")
            if AUTO and ahora_h == HORA_AUTO and not _estado_worker["corriendo"]:
                log.info(f"Scheduler: lanzando seguimiento automático ({HORA_AUTO})")
                run_seguimiento(modo="ambos")
        except Exception as e:
            log.error(f"scheduler err {e}")
        time.sleep(60)  # revisar cada minuto

if AUTO:
    threading.Thread(target=_scheduler, daemon=True, name="scheduler").start()
    log.info(f"Scheduler activado — seguimiento diario a {HORA_AUTO}")

# ── FLASK ENDPOINTS (integrado al bot principal vía import) ──
# Si se importa desde bot_whatsapp.py, estos endpoints quedan disponibles
# Si se corre directo, levanta servidor propio
if __name__ == "__main__":
    from flask import Flask, jsonify, request as freq
    app2 = Flask(__name__)

    @app2.route("/seguimiento/estado")
    def seg_estado():
        return jsonify(_estado_worker)

    @app2.route("/seguimiento/iniciar", methods=["POST"])
    def seg_iniciar():
        d = freq.json or {}
        res = run_seguimiento(
            modo      = d.get("modo","ambos"),
            limite_imos = d.get("limite_imos"),
            limite_px   = d.get("limite_px"),
        )
        return jsonify(res)

    app2.run(host="0.0.0.0", port=10001, debug=False)
