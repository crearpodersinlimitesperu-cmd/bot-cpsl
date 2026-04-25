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
CRM_SHEET_ID = "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y"  # Sheet del CRM
CRM_TAB      = "REPORTES_BOT"

# Patrones para detectar a qué CC pertenece un reporte pegado
_CC_PATTERNS = {
    "DIANA": [r"diana", r"dmoscoso", r"moscoso", r"equipo\s*26", r"equipo\s*1[4-9]"],
    "JOYCE": [r"joyce", r"jmarin", r"mar[ií]n", r"equipo\s*2[0125]"],
    "ZULEY": [r"zuley", r"zurteaga", r"urteaga", r"equipo\s*2[34]"],
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
            f'Las coordinadoras son: DIANA (equipos 14-19,26), JOYCE (equipos 20-22,25), ZULEY (equipos 23-24).\n'
            f'Equipo 27 es el equipo actual de la campaña C1.\n'
            f'¿De cuál coordinadora es este reporte? Responde SOLO con el nombre: DIANA, JOYCE o ZULEY.\n'
            f'Si no puedes determinarlo, responde DESCONOCIDA.'
        )
        resp = ia_responder(prompt, contexto="general", timeout=5)
        if resp:
            resp_upper = resp.strip().upper()
            for nombre in ["DIANA", "JOYCE", "ZULEY"]:
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
