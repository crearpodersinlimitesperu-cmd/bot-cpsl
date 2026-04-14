"""
SEGUIMIENTO AUTÓNOMO IMOs — C1 E27
====================================
1. Lee CAMPAÑA_IMOs_C1_E27.xlsx — estado actual de cada IMO
2. Lee Prospectos_Pendientes_C1_Depurado_Campana.csv — nombres y PX
3. PASO A: Notifica coordinadoras sobre IMOs que no quieren (NO ASISTE/STOP)
4. PASO B: Envía plantilla a los 265 IMOs sin respuesta
5. Guarda progreso — retomable si se interrumpe

USO:
    set WA_TOKEN=EAAxxxxxxx
    set WA_PHONE_ID=1085205258006361
    python seguimiento_imos_c1e27_v2.py
"""

import os, csv, json, time, re, openpyxl, requests, logging
from datetime import datetime
from collections import defaultdict

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SeguimientoIMOs")

WA_TOKEN  = os.environ.get("WA_TOKEN","")
PHONE_ID  = os.environ.get("WA_PHONE_ID","")
TEMPLATE  = "invitacion_c1_px"
LANG_CODE = "es_PE"
FECHA_C1  = "Viernes 01 de Mayo"
PAUSA     = 1.5

STAFF = {
    "dmoscoso": {"nombre":"Diana Moscoso",  "tel":"51912379744"},
    "jmarin":   {"nombre":"Joyce Marín",    "tel":"51933599903"},
    "lpasquel": {"nombre":"Leyla Pasquel",  "tel":"51919502385"},
    "zurteaga": {"nombre":"Zuley Urteaga",  "tel":"51933599864"},
}
_carga = {k:0 for k in STAFF}
def cc_libre(): return min(_carga, key=_carga.get)

CSV_PX     = "Prospectos_Pendientes_C1_Depurado_Campana.csv"
EXCEL_IMO  = "CAMPAÑA_IMOs_C1_E27.xlsx"
PROGRESO_F = "progreso_seguimiento_imos.json"
LOG_F      = "log_seguimiento_imos.csv"

ESTADOS_FINALES = {"CONFIRMA","YA ASISTIO","NO ASISTE","STOP","DEVOLUCION","BAJA"}

def norm(t):
    t = re.sub(r'\D','',str(t or ''))
    if t.startswith("51") and len(t)==11: return t
    if len(t)==9 and t.startswith("9"): return "51"+t
    return t

def nc(s):  # nombre completo legible
    p = str(s or '').strip().split()
    return ' '.join(x.title() for x in p[:4]) if p else ''

def np_(s):  # primer nombre
    p = [x for x in str(s or '').strip().split() if len(x)>2]
    return p[0].title() if p else str(s).strip().title()

def eq_max(pxs):
    nums = [int(m.group()) for r in pxs
            for m in [re.search(r'\d+',str(r.get("Equipo","")))] if m]
    return max(nums) if nums else 0

def log_row(f):
    nuevo = not os.path.exists(LOG_F)
    with open(LOG_F,"a",encoding="utf-8-sig",newline="") as fh:
        w = csv.writer(fh)
        if nuevo: w.writerow(["Fecha","Tel","Nombre IMO","N PX","Estado Prev","Accion","Detalle"])
        w.writerow(f)

def carg_prog():
    if os.path.exists(PROGRESO_F):
        with open(PROGRESO_F,encoding="utf-8") as f: return json.load(f)
    return {"enviados":[],"notificados":[]}

def guar_prog(p):
    with open(PROGRESO_F,"w",encoding="utf-8") as f: json.dump(p,f,ensure_ascii=False,indent=2)

def cargar_excel():
    if not os.path.exists(EXCEL_IMO): return {}
    est = {}
    wb = openpyxl.load_workbook(EXCEL_IMO,data_only=True,read_only=True)
    for row in wb["Hoja 1"].iter_rows(min_row=2,values_only=True):
        if not row[0]: continue
        t=norm(str(row[1] or '')); e=str(row[5] or '').strip()
        if t and len(t)==11: est[t]=e
    wb.close(); return est

def cargar_imos():
    if not os.path.exists(CSV_PX): return {}
    imos=defaultdict(list)
    with open(CSV_PX,encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            raw=re.sub(r'\D','',str(r.get("Tel. IMO","") or ''))
            if raw.startswith("51") and len(raw)==11: t=raw
            elif len(raw)==9 and raw.startswith("9"): t="51"+raw
            else: continue
            imos[t].append(r)
    return imos

def send_wa(tel, txt):
    try:
        requests.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,"type":"text",
                  "text":{"body":txt}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"}, timeout=10)
    except Exception as e: logger.error(f"send_wa {e}")

def enviar_tmpl(tel, pila):
    try:
        r=requests.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,"type":"template",
                  "template":{"name":TEMPLATE,"language":{"code":LANG_CODE},
                  "components":[{"type":"body","parameters":[
                      {"type":"text","text":pila},
                      {"type":"text","text":FECHA_C1}]}]}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"}, timeout=15)
        if r.status_code==200:
            return True, r.json().get("messages",[{}])[0].get("id","")
        return False, r.json().get("error",{}).get("message",r.text[:100])
    except Exception as e: return False, str(e)

def notif_coord(tel_imo, nom_imo, n_px, motivo, px_lst=None):
    k=cc_libre(); c=STAFF[k]; _carga[k]+=1
    px_txt=""
    if px_lst:
        px_txt="\n*Enrolados pendientes:*\n"+"\n".join(f"• {p}" for p in px_lst[:10])
    send_wa(c["tel"],
        f"🚨 *SEGUIMIENTO IMOs — CPSL Lima*\n\n"
        f"*IMO:* {nom_imo}\n"
        f"*Tel:* wa.me/{tel_imo}\n"
        f"*PX pendientes:* {n_px}\n"
        f"*Motivo:* {motivo}{px_txt}")
    logger.info(f"  ↳ Notificado → {c['nombre']}")
    return c["nombre"]

def main():
    if not WA_TOKEN: logger.error("WA_TOKEN vacío"); return
    if not PHONE_ID: logger.error("WA_PHONE_ID vacío"); return

    logger.info("Cargando datos...")
    estados  = cargar_excel()
    imos_map = cargar_imos()
    prog     = carg_prog()
    ya_env   = set(prog.get("enviados",[]))
    ya_notif = set(prog.get("notificados",[]))

    # ── PASO A: Notificar no-quieren pendientes ───────────────
    no_q = []
    for tel,est in estados.items():
        if est in ESTADOS_FINALES and tel not in ya_notif and tel in imos_map:
            pxs=imos_map[tel]; nom=nc(pxs[0].get("IMO",""))
            px_lst=[f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()} ({r.get('Equipo','')})" for r in pxs]
            no_q.append({"tel":tel,"nom":nom,"n_px":len(pxs),"est":est,"px":px_lst})

    if no_q:
        print(f"\n⚠️  {len(no_q)} IMOs con estado final (aún sin notificar a coordinadora):")
        for d in no_q: print(f"   {d['nom'][:38]} | {d['n_px']} PX | {d['est']}")
        print("\n¿Notificar coordinadoras ahora? (s/n): ",end="")
        if input().strip().lower()=="s":
            for d in no_q:
                motivo={
                    "NO ASISTE":"Declina asistir — gestionar devolución si aplica",
                    "STOP":     "Solicitó STOP — archivar enrolados",
                    "DEVOLUCION":"Solicita devolución — gestionar urgente",
                }.get(d["est"],f"Estado: {d['est']}")
                nom_c=notif_coord(d["tel"],d["nom"],d["n_px"],motivo,d["px"])
                log_row([datetime.now().strftime("%Y-%m-%d %H:%M"),
                         d["tel"],d["nom"],d["n_px"],d["est"],
                         f"NOTIFICADO→{nom_c}",motivo])
                ya_notif.add(d["tel"])
                prog["notificados"]=list(ya_notif); guar_prog(prog)
                time.sleep(1.0)
            print(f"✅ {len(no_q)} notificaciones enviadas.")

    # ── PASO B: Seguimiento a sin respuesta ───────────────────
    cands=[]
    for tel,pxs in imos_map.items():
        if tel in ya_env: continue
        est=estados.get(tel,"")
        if est in ESTADOS_FINALES: continue
        nom=nc(pxs[0].get("IMO","")); pila=np_(pxs[0].get("IMO",""))
        px_lst=[f"{r.get('Nombre','').strip().title()} {r.get('Apellido','').strip().title()} ({r.get('Equipo','')})" for r in pxs]
        cands.append({"tel":tel,"nom":nom,"pila":pila,
                      "n_px":len(pxs),"eq_max":eq_max(pxs),
                      "est":est or "NO_CONTACTADO","px":px_lst})

    cands.sort(key=lambda x:(-x["eq_max"],-x["n_px"]))

    print()
    print("="*58)
    print(f"  SEGUIMIENTO IMOs C1 E27 — {TEMPLATE}")
    print(f"  Ya enviados antes:   {len(ya_env)}")
    print(f"  A enviar ahora:      {len(cands)}")
    print(f"  Tiempo estimado:     ~{len(cands)*PAUSA/60:.0f} min")
    print("="*58)

    if not cands: print("✅ Sin pendientes."); return

    print("\nPrimeros en cola:")
    for c in cands[:5]:
        print(f"  {c['nom'][:38]} | {c['n_px']} PX | E{c['eq_max']}")

    print(f"\n¿Confirmas enviar a {len(cands)} IMOs? (s/n): ",end="")
    if input().strip().lower()!="s": print("Cancelado."); return

    ok=err=0; t0=datetime.now()
    for i,c in enumerate(cands,1):
        exito,res=enviar_tmpl(c["tel"],c["pila"])
        ahora=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if exito:
            ok+=1; ya_env.add(c["tel"])
            prog["enviados"]=list(ya_env); guar_prog(prog)
            log_row([ahora,c["tel"],c["nom"],c["n_px"],c["est"],"ENVIADO",res])
            logger.info(f"[{i}/{len(cands)}] ✅  {c['nom'][:35]} ({c['n_px']} PX)")
        else:
            err+=1
            log_row([ahora,c["tel"],c["nom"],c["n_px"],c["est"],"ERROR",res[:80]])
            logger.error(f"[{i}/{len(cands)}] ❌  {c['pila']} — {res[:60]}")
        time.sleep(PAUSA)
        if i%50==0:
            s=(datetime.now()-t0).seconds
            logger.info(f"--- {i}/{len(cands)} | ✅{ok} ❌{err} | {s//60}m{s%60}s ---")

    s=(datetime.now()-t0).seconds
    print()
    print("="*58)
    print(f"  ✅ COMPLETADO | OK:{ok} ERR:{err} | {s//60}m{s%60}s")
    print(f"  Log: {LOG_F}")
    print("="*58)
    if err: print(f"\n⚠️  {err} errores. Vuelve a ejecutar — los OK no se repiten.")

if __name__=="__main__":
    main()
