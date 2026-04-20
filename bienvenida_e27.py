"""
MÓDULO BIENVENIDA E27 — CPSL Lima
===================================
Envío masivo de bienvenida a los 275 nuevos participantes del Equipo 27.

REGLAS:
- Solo para PX (no IMOs)
- Incluye nombre de CC asignada y su teléfono
- Texto libre (sin plantilla) — solo dentro de ventana 24h activa
- Para contacto inicial sin ventana → necesita plantilla aprobada
- Pausa 45s entre mensajes, máximo 50/ciclo
- Registra cada envío

ENDPOINTS INTEGRADOS AL BOT:
  POST /api/bienvenida/e27/iniciar  {limite:50}
  GET  /api/bienvenida/e27/estado
  POST /api/bienvenida/e27/detener
"""

import os, csv, json, logging, time, threading, re
from datetime import datetime, timezone, timedelta

log = logging.getLogger("BienvenidaE27")
TZ  = timezone(timedelta(hours=-5))
def ahora(): return datetime.now(TZ)

DATA_DIR   = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
CSV_PATH   = os.path.join(os.path.dirname(os.path.abspath(__file__)), "E27_participantes_limpio.csv")
ESTADO_PATH = os.path.join(DATA_DIR, "bienvenida_e27_estado.json")
_lk = threading.Lock()

PHONE_ID  = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_TOKEN  = os.environ.get("WA_TOKEN", "")
PAUSA     = 45   # segundos entre mensajes — anti-spam Meta

# ── Estado global ──────────────────────────────────────────────────
_estado = {
    "corriendo":  False,
    "enviados":   0,
    "errores":    0,
    "total":      275,
    "ultimo":     "",
    "inicio":     None,
    "log":        [],
}

def _add_log(msg, nivel="INFO"):
    entry = f"[{ahora().strftime('%H:%M:%S')}] {msg}"
    _estado["log"] = ([entry] + _estado["log"])[:100]
    getattr(log, nivel.lower(), log.info)(msg)

# ── Cargar participantes ────────────────────────────────────────────
def cargar_participantes():
    """Carga los 275 PX del Equipo 27 desde el CSV."""
    if not os.path.exists(CSV_PATH):
        log.error(f"CSV no encontrado: {CSV_PATH}")
        return []
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def cargar_estado_envio():
    try:
        if os.path.exists(ESTADO_PATH):
            with open(ESTADO_PATH) as f:
                return json.load(f)
    except: pass
    return {}

def guardar_estado_envio(d):
    try:
        with open(ESTADO_PATH, "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"guardar_estado: {e}")

# ── Función de envío ───────────────────────────────────────────────
def _wa_text(tel, msg):
    """Envía texto libre via WhatsApp Cloud API."""
    if not WA_TOKEN: return False
    try:
        import requests
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json={"messaging_product":"whatsapp","to":tel,
                  "type":"text","text":{"body":msg}},
            headers={"Authorization":f"Bearer {WA_TOKEN}",
                     "Content-Type":"application/json"}, timeout=15)
        if r.status_code == 200: return True
        err = r.json().get("error",{}).get("message","")
        log.error(f"WA error {tel}: {err[:80]}")
        return False
    except Exception as e:
        log.error(f"WA exc {tel}: {e}")
        return False

def _construir_mensaje(px):
    """Construye el mensaje de bienvenida personalizado."""
    pila = (px.get("Nombres","") or px.get("Apellidos","")).split()[0].title()
    if not pila or len(pila) < 2:
        pila = px.get("Apellidos","Amigo/a").split()[0].title()
    
    cc_nom = px.get("CC_Nombre","tu coordinadora")
    cc_tel = px.get("CC_Telefono","")
    
    # Número limpio para mostrar
    tel_display = cc_tel.replace("+51 ","") if cc_tel.startswith("+51") else cc_tel

    return (
        f"Hola {pila}! Te escribimos desde *Crear Poder Sin L\u00edmites Per\u00fa*.\n\n"
        f"Bienvenido/a al *Equipo 27* \u2014 C1 E27.\n\n"
        f"\U0001F4C5 *Fechas:*\n"
        f"Viernes 01, S\u00e1bado 02 y Domingo 03 de Mayo 2026\n"
        f"\U0001F4CD Hotel Jos\u00e9 Antonio Deluxe, Calle Bellavista 133, Miraflores.\n\n"
        f"Tu coordinadora asignada es *{cc_nom}*.\n"
        f"Te pedimos guardar su n\u00famero: *{tel_display}*\n"
        f"Ella te contactar\u00e1 para acompa\u00f1arte en el proceso.\n\n"
        f"Nos vemos en la cancha. \u26a1\n"
        f"*CPSL Lima*"
    )

# ── Proceso principal de envío ─────────────────────────────────────
def run_bienvenida_e27(limite=50, solo_ventana_activa=False):
    """
    Envía mensajes de bienvenida a los PX del E27.
    
    Args:
        limite: máximo de envíos por ciclo (default 50, max 100)
        solo_ventana_activa: True = solo enviar si el PX ya escribió al bot
    """
    with _lk:
        if _estado["corriendo"]:
            return {"error": "Ya hay un envío en curso"}
        _estado["corriendo"] = True
        _estado["inicio"]    = ahora().isoformat()
        _estado["enviados"]  = 0
        _estado["errores"]   = 0

    limite = min(limite or 50, 100)
    
    try:
        participantes = cargar_participantes()
        estado_previo = cargar_estado_envio()
        
        pendientes = [
            p for p in participantes
            if estado_previo.get(p["Telefono"], {}).get("estado") != "ENVIADO"
        ]
        
        _add_log(f"Bienvenida E27 iniciada — {len(pendientes)} pendientes de {len(participantes)} total")
        _estado["total"] = len(pendientes)
        
        enviados_ciclo = 0
        for px in pendientes:
            if not _estado["corriendo"]: break
            if enviados_ciclo >= limite: break
            
            tel = px.get("Telefono","")
            if not tel or not re.match(r'^51\d{9}$', tel):
                _add_log(f"Tel inválido: {px.get('Apellidos','')} — '{tel}'", "WARNING")
                continue
            
            msg = _construir_mensaje(px)
            ok  = _wa_text(tel, msg)
            
            ts = ahora().isoformat()
            estado_previo[tel] = {
                "estado":  "ENVIADO" if ok else "ERROR",
                "ts":      ts,
                "nombre":  f"{px.get('Apellidos','')} {px.get('Nombres','')}",
                "cc":      px.get("CC_Asignada",""),
            }
            guardar_estado_envio(estado_previo)
            
            if ok:
                _estado["enviados"] += 1
                enviados_ciclo += 1
                _add_log(f"Bienvenida OK: {px.get('Apellidos','')} {px.get('Nombres','').split()[0]} ({tel})")
            else:
                _estado["errores"] += 1
                _add_log(f"Bienvenida ERROR: {px.get('Apellidos','')} ({tel})", "WARNING")
            
            _estado["ultimo"] = f"{px.get('Apellidos','')} {px.get('Nombres','').split()[0] if px.get('Nombres') else ''}"
            time.sleep(PAUSA)

        resumen = (f"Bienvenida E27 completada — "
                   f"Enviados: {_estado['enviados']}, "
                   f"Errores: {_estado['errores']}, "
                   f"Pendientes: {len(pendientes) - enviados_ciclo}")
        _add_log(resumen)
        return {"ok": _estado["enviados"], "err": _estado["errores"], "pendientes": len(pendientes) - enviados_ciclo}

    except Exception as e:
        _add_log(f"ERROR CRÍTICO: {e}", "ERROR")
        return {"error": str(e)}
    finally:
        _estado["corriendo"] = False

def estado_bienvenida():
    """Retorna el estado actual del envío."""
    estado_previo = cargar_estado_envio()
    enviados_total = sum(1 for v in estado_previo.values() if v.get("estado") == "ENVIADO")
    errores_total  = sum(1 for v in estado_previo.values() if v.get("estado") == "ERROR")
    return {
        **_estado,
        "enviados_total_historico": enviados_total,
        "errores_total_historico":  errores_total,
        "pendientes_total":         275 - enviados_total,
    }

def detener_bienvenida():
    """Detiene el envío en curso."""
    _estado["corriendo"] = False
    _add_log("Envío detenido manualmente")
    return {"ok": True}
