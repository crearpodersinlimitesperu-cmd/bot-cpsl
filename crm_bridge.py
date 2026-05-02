"""
CRM BRIDGE — Puente entre Bot WhatsApp y CRM Crear Lima
=========================================================
Recibe los reportes parseados del bot y los escribe directamente
en la pestaña REPORTES_BOT del Google Sheets maestro del CRM.

El CRM (app_buscador.py) lee esta pestaña y cruza los datos
automáticamente con el Master de participantes.

FLUJO:
  Bot WhatsApp → crm_bridge.push_reporte_crm() → Google Sheets → CRM lee en vivo

También soporta:
  - José envía un reporte pegado al bot → IA detecta de qué CC es → lo registra
  - CC envía reporte directo → se registra con su nombre
"""

import os, re, json, logging, time, base64
from datetime import datetime, timedelta, timezone
import requests as req_lib

log = logging.getLogger("CRM_Bridge")
TZ  = timezone(timedelta(hours=-5))

# ── CONFIGURACIÓN ──────────────────────────────────────────────
CRM_SHEET_ID = os.environ.get("SHEET_ID", "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y")
CRM_TAB      = "REPORTES_BOT"

# Patrones para detectar a qué CC pertenece un reporte pegado
_CC_PATTERNS = {
    "DIANA": [r"diana", r"dmoscoso", r"moscoso", r"equipo\s*26", r"equipo\s*1[4-9]"],
    "JOYCE": [r"joyce", r"jmarin", r"mar[ií]n", r"equipo\s*2[0125]"]
}

def _detectar_cc(texto):
    """
    Detecta a qué coordinadora pertenece un reporte.
    Cascada: 1) Regex rápido  2) IA (Gemini/Groq)  3) DESCONOCIDA
    """
    t = texto.lower()
    # 1. Regex
    for cc, patterns in _CC_PATTERNS.items():
        for p in patterns:
            if re.search(p, t, re.IGNORECASE):
                return cc

    # 2. IA — preguntar a Gemini/Groq quién envió el reporte
    try:
        from ia_chain import ia_responder
        prompt = (
            f'Analiza este reporte de productividad de coordinadoras de Lima:\n'
            f'"""{texto[:500]}"""\n\n'
            f'Las coordinadoras son: DIANA (equipos 14-19,26), JOYCE (equipos 20-22,25).\n'
            f'Equipo 27 es el equipo actual de la campaña C1.\n'
            f'¿De cuál coordinadora es este reporte? Responde SOLO con el nombre: DIANA o JOYCE.\n'
            f'Si no puedes determinarlo, responde DESCONOCIDA.'
        )
        resp = ia_responder(prompt, contexto="general", timeout=5)
        if resp:
            resp_upper = resp.strip().upper()
            for nombre in ["DIANA", "JOYCE"]:
                if nombre in resp_upper:
                    log.info(f"CRM_Bridge: IA detectó CC={nombre}")
                    return nombre
    except Exception as e:
        log.warning(f"CRM_Bridge IA detección: {e}")

    return "DESCONOCIDA"

def _get_sheets_token():
    """Genera JWT token para Google Sheets API (misma lógica que el bot)."""
    creds_raw = os.environ.get("GOOGLE_CREDENTIALS", "")
    if not creds_raw:
        log.warning("CRM_Bridge: GOOGLE_CREDENTIALS no configurado")
        return None
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding as cp
        now   = int(time.time())
        creds = json.loads(creds_raw)
        pem   = creds["private_key"].replace("\\n", "\n")
        hdr   = base64.urlsafe_b64encode(json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
        pld   = base64.urlsafe_b64encode(json.dumps({
            "iss": creds["client_email"],
            "scope": "https://www.googleapis.com/auth/spreadsheets",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now, "exp": now + 3600
        }).encode()).rstrip(b"=")
        msg_b = hdr + b"." + pld
        pk    = serialization.load_pem_private_key(pem.encode(), password=None)
        sig   = pk.sign(msg_b, cp.PKCS1v15(), hashes.SHA256())
        jwt_tok = (msg_b + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
        r = req_lib.post("https://oauth2.googleapis.com/token",
            data={"grant_type":"urn:ietf:params:oauth:grant-type:jwt-bearer","assertion":jwt_tok},
            timeout=10)
        if r.status_code == 200:
            return r.json()["access_token"]
        log.error(f"CRM_Bridge token error: {r.status_code}")
    except Exception as e:
        log.error(f"CRM_Bridge token exc: {e}")
    return None


def push_reporte_crm(cc_nombre, reporte_parsed, texto_raw=""):
    """
    Escribe una fila en la pestaña REPORTES_BOT del Google Sheets del CRM.
    
    Args:
        cc_nombre: Nombre de la coordinadora (Diana, Joyce, Zuley)
        reporte_parsed: Dict con los campos parseados del reporte
        texto_raw: Texto original del mensaje
    """
    tok = _get_sheets_token()
    if not tok:
        log.warning("CRM_Bridge: Sin token, reporte no enviado al CRM")
        return False
    
    ahora_s = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    # Extraer métricas del reporte parseado
    nuevos    = reporte_parsed.get("nuevos", {})
    rezagados = reporte_parsed.get("rezagados", {})
    
    ok_n    = nuevos.get("OK", 0)
    nc_n    = nuevos.get("NC", 0)
    pend_n  = nuevos.get("PENDIENTE", nuevos.get("PEND", 0))
    tot_n   = nuevos.get("TOTAL", ok_n + nc_n + pend_n)
    
    ok_r    = rezagados.get("OK", 0)
    nc_r    = rezagados.get("NC", 0)
    pend_r  = rezagados.get("PENDIENTE", rezagados.get("PEND", 0))
    tot_r   = rezagados.get("TOTAL", ok_r + nc_r + pend_r)
    
    notas   = reporte_parsed.get("notas", "")
    
    # Fila: [Fecha, CC, Nuevos_OK, Nuevos_NC, Nuevos_Pend, Nuevos_Total, 
    #         Rezag_OK, Rezag_NC, Rezag_Pend, Rezag_Total, Notas, Raw]
    fila = [
        ahora_s,
        cc_nombre,
        ok_n, nc_n, pend_n, tot_n,
        ok_r, nc_r, pend_r, tot_r,
        notas[:200],
        texto_raw[:500]
    ]
    
    try:
        tab = CRM_TAB.replace(" ", "%20")
        r = req_lib.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{CRM_SHEET_ID}/values/{tab}!A:L:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": [fila]},
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            timeout=10
        )
        if r.status_code == 200:
            log.info(f"CRM_Bridge: Reporte de {cc_nombre} enviado al CRM ✅")
            return True
        else:
            log.error(f"CRM_Bridge: Error {r.status_code}: {r.text[:100]}")
            return False
    except Exception as e:
        log.error(f"CRM_Bridge: Excepción al enviar: {e}")
        return False


def push_gestion_individual(cc_nombre, nombre_px, resultado, fecha=None):
    """
    Registra una gestión individual (cierre de caso, actualización, etc.)
    en la pestaña GESTIONES_BOT del CRM.
    """
    tok = _get_sheets_token()
    if not tok:
        return False
    
    ahora_s = fecha or datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    
    fila = [
        ahora_s,
        cc_nombre,
        nombre_px,
        resultado,  # RESUELTO, EN_GESTION, SIN_CONTACTO
    ]
    
    try:
        tab = "GESTIONES_BOT"
        r = req_lib.post(
            f"https://sheets.googleapis.com/v4/spreadsheets/{CRM_SHEET_ID}/values/{tab}!A:D:append",
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": [fila]},
            headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json"},
            timeout=10
        )
        if r.status_code == 200:
            log.info(f"CRM_Bridge: Gestión {resultado} de {nombre_px} por {cc_nombre} ✅")
            return True
        log.error(f"CRM_Bridge gestión: {r.status_code}")
    except Exception as e:
        log.error(f"CRM_Bridge gestión exc: {e}")
    return False


def push_reporte_jose(texto_raw):
    """
    José pega un reporte en el bot → IA detecta de qué CC es → lo registra.
    Retorna (cc_detectada, éxito)
    """
    cc = _detectar_cc(texto_raw)
    
    # Parsear el reporte usando el parser existente
    try:
        from reportes_cc import parsear_reporte
        parsed = parsear_reporte(texto_raw, cc)
        exito = push_reporte_crm(cc, parsed, texto_raw)
        return cc, exito
    except Exception as e:
        log.error(f"CRM_Bridge push_reporte_jose: {e}")
        return cc, False


def kpi_consolidado_whatsapp():
    """
    Lee datos reales del Google Sheets y genera un resumen ejecutivo
    para enviar por WhatsApp a José.
    
    Retorna un string formateado listo para WhatsApp.
    """
    tok = _get_sheets_token()
    if not tok:
        return "⚠️ Sin acceso al CRM. Verifica credenciales."
    
    hdr = {"Authorization": f"Bearer {tok}"}
    ahora_s = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    
    try:
        # 1. Leer MASTER (Hoja 1) — nombres y coordinadores
        r1 = req_lib.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{CRM_SHEET_ID}/values/Hoja%201!A:N",
            headers=hdr, timeout=15
        )
        master_rows = r1.json().get("values", []) if r1.status_code == 200 else []
        
        # 2. Leer PRODUCTIVIDAD
        r2 = req_lib.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{CRM_SHEET_ID}/values/PRODUCTIVIDAD!A:N",
            headers=hdr, timeout=15
        )
        prod_rows = r2.json().get("values", []) if r2.status_code == 200 else []
        
        # 3. Leer REPORTES_BOT (últimos reportes de WhatsApp)
        r3 = req_lib.get(
            f"https://sheets.googleapis.com/v4/spreadsheets/{CRM_SHEET_ID}/values/REPORTES_BOT!A:L",
            headers=hdr, timeout=15
        )
        bot_rows = r3.json().get("values", []) if r3.status_code == 200 else []
        
    except Exception as e:
        log.error(f"CRM KPI: {e}")
        return f"⚠️ Error leyendo datos: {e}"
    
    # ── Procesar Master ──
    total_master = max(len(master_rows) - 1, 0)
    cc_count = {"DIANA": 0, "JOYCE": 0, "SIN_CC": 0}
    if master_rows:
        headers_m = [h.upper().strip() for h in master_rows[0]]
        idx_cc = next((i for i, h in enumerate(headers_m) if "COORDINADOR" in h), -1)
        idx_est = next((i for i, h in enumerate(headers_m) if "ESTATUS" in h and "C1" in h), -1)
        
        ok_c1 = 0
        for row in master_rows[1:]:
            cc_val = row[idx_cc].upper().strip() if idx_cc >= 0 and idx_cc < len(row) else ""
            est_val = row[idx_est].upper().strip() if idx_est >= 0 and idx_est < len(row) else ""
            
            if "DIANA" in cc_val:
                cc_count["DIANA"] += 1
            elif "JOYCE" in cc_val:
                cc_count["JOYCE"] += 1
            elif "ZULEY" in cc_val:
                # Reasignación equitativa histórica de Zuley
                if cc_count["DIANA"] <= cc_count["JOYCE"]: cc_count["DIANA"] += 1
                else: cc_count["JOYCE"] += 1
            else:
                cc_count["SIN_CC"] += 1
            
            if est_val in ("OK", "CONFIRMADO", "SENTADO", "ASISTIO"):
                ok_c1 += 1
    else:
        ok_c1 = 0
    
    # ── Procesar Productividad ──
    prod_por_cc = {"DIANA": {"OK": 0, "NC": 0, "TOTAL": 0},
                   "JOYCE": {"OK": 0, "NC": 0, "TOTAL": 0}}
    if prod_rows and len(prod_rows) > 1:
        headers_p = [h.upper().strip() for h in prod_rows[0]]
        idx_cc_p = next((i for i, h in enumerate(headers_p) if "CC_REPORTADA" in h), -1)
        idx_res = next((i for i, h in enumerate(headers_p) if "RESULTADO" in h), -1)
        
        for row in prod_rows[1:]:
            cc_p = row[idx_cc_p].upper().strip() if idx_cc_p >= 0 and idx_cc_p < len(row) else ""
            res_p = row[idx_res].upper().strip() if idx_res >= 0 and idx_res < len(row) else ""
            
            for cc_k in prod_por_cc:
                if cc_k in cc_p or ("ZULEY" in cc_p and cc_k == "DIANA"):  # Zuley pasa a sumar a Diana para simplificar el histórico
                    prod_por_cc[cc_k]["TOTAL"] += 1
                    if "OK" in res_p or "CONFIRM" in res_p or "ASIST" in res_p:
                        prod_por_cc[cc_k]["OK"] += 1
                    elif "NC" in res_p or "NO CONTEST" in res_p:
                        prod_por_cc[cc_k]["NC"] += 1
                    break
    
    total_gestiones = sum(d["TOTAL"] for d in prod_por_cc.values())
    total_ok = sum(d["OK"] for d in prod_por_cc.values())
    total_nc = sum(d["NC"] for d in prod_por_cc.values())
    
    # ── Procesar Reportes Bot ──
    n_reportes_bot = max(len(bot_rows) - 1, 0) if bot_rows else 0
    
    # ── META C1 ──
    META = 325
    pct = round((ok_c1 / META) * 100, 1) if META > 0 else 0
    faltan = max(META - ok_c1, 0)
    
    # ── Construir mensaje ──
    msg = (
        f"📊 *CONSOLIDADO CRM — Torre de Control*\n"
        f"_{ahora_s}_\n\n"
        f"{'━' * 30}\n"
        f"🎯 *META C1 E27: {ok_c1}/{META}* ({pct}%)\n"
        f"{'█' * min(int(pct/5), 20)}{'░' * max(20 - int(pct/5), 0)} {pct}%\n"
        f"Faltan: *{faltan}* confirmados\n"
        f"{'━' * 30}\n\n"
        f"👥 *Base Total:* {total_master} participantes\n"
        f"📞 *Gestiones Productividad:* {total_gestiones}\n"
        f"✅ OK/Confirmados: {total_ok}\n"
        f"❌ No Contesta: {total_nc}\n\n"
        f"{'─' * 30}\n"
        f"*POR COORDINADORA:*\n\n"
    )
    
    for cc_name in ["DIANA", "JOYCE"]:
        asig = cc_count.get(cc_name, 0)
        ok_p = prod_por_cc[cc_name]["OK"]
        nc_p = prod_por_cc[cc_name]["NC"]
        tot_p = prod_por_cc[cc_name]["TOTAL"]
        pct_ok = round((ok_p / tot_p) * 100) if tot_p > 0 else 0
        
        emoji = "🟢" if pct_ok >= 60 else "🟡" if pct_ok >= 40 else "🔴"
        msg += (
            f"{emoji} *{cc_name}*\n"
            f"   Asignados: {asig} | Gestiones: {tot_p}\n"
            f"   ✅ OK: {ok_p} | ❌ NC: {nc_p} | Efect: {pct_ok}%\n\n"
        )
    
    msg += (
        f"{'─' * 30}\n"
        f"📱 Reportes vía Bot: {n_reportes_bot}\n"
        f"🔄 Sin coordinador: {cc_count.get('SIN_CC', 0)}\n\n"
        f"_Escribe un número para otra opción._"
    )
    
    return msg

