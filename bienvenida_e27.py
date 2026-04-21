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
PAUSA      = 45   # segundos entre mensajes — anti-spam Meta
HORA_INICIO = 8   # 08:00 Lima — reanudar envío
HORA_FIN    = 21  # 21:00 Lima — detener envío

def _en_ventana_horaria():
    """Retorna True si estamos dentro del horario de envío (08:00–21:00 Lima)."""
    h = ahora().hour
    return HORA_INICIO <= h < HORA_FIN

def _esperar_ventana():
    """Pausa el hilo hasta que se abra la ventana horaria. Retorna False si se detuvo."""
    while not _en_ventana_horaria():
        if not _estado["corriendo"]:
            return False
        prox = ahora().replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
        if prox <= ahora():
            prox = prox + timedelta(days=1)
        espera = (prox - ahora()).total_seconds()
        _add_log(f"⏸ Ventana cerrada — reanuda a las {HORA_INICIO:02d}:00 (en {int(espera//3600)}h {int((espera%3600)//60)}m)")
        # Duerme en tramos de 60s para poder responder a "detener"
        for _ in range(int(espera // 60) + 1):
            if not _estado["corriendo"]:
                return False
            time.sleep(min(60, espera))
            espera -= 60
            if espera <= 0:
                break
    return True

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
        f"Tu lugar en el entrenamiento ya est\u00e1 confirmado:\n"
        f"Viernes 01, S\u00e1bado 02 y Domingo 03 de Mayo 2026\n"
        f"Hotel Jos\u00e9 Antonio Deluxe, Calle Bellavista 133, Miraflores.\n\n"
        f"Tu coordinadora es *{cc_nom}*.\n"
        f"Guarda su n\u00famero: *{tel_display}*\n"
        f"Ella te acompa\u00f1ar\u00e1 en el proceso.\n\n"
        f"Nos vemos en la cancha. \u26a1\n"
        f"*CPSL Lima*"
    )


# ── Notificación a CC cada 10 enviados de su grupo ─────────────────
_cc_contadores = {}  # {cc_key: count}

def _notif_cc_progreso(estado_previo, cc_key, cc_nombre, cc_tel):
    """Notifica a la CC cada 10 mensajes enviados a sus participantes."""
    if not cc_key or not cc_tel:
        return
    # Contar enviados de esta CC
    enviados_cc = sum(
        1 for v in estado_previo.values()
        if v.get("estado") == "ENVIADO" and v.get("cc") == cc_key
    )
    prev = _cc_contadores.get(cc_key, 0)
    _cc_contadores[cc_key] = enviados_cc
    # Notificar en múltiplos de 10 (solo cuando cruce el umbral)
    if enviados_cc > 0 and (enviados_cc // 10) > (prev // 10):
        total_cc = 91 if cc_key == "jmarin" else 92  # Joyce:91, Zuley:92, Diana:92
        pct = int(enviados_cc / total_cc * 100)
        msg = (
            f"📊 *Bienvenida E27 — Avance {cc_nombre.split()[0]}*\n"
            f"Enviados a tus participantes: *{enviados_cc} de {total_cc}* ({pct}%)\n"
            f"El Equipo 27 ya está recibiendo su bienvenida. ⚡"
        )
        try:
            import requests
            requests.post(
                f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
                json={"messaging_product":"whatsapp","to":cc_tel.replace("+51 ","51").replace("+","").replace(" ",""),
                      "type":"text","text":{"body":msg}},
                headers={"Authorization":f"Bearer {WA_TOKEN}","Content-Type":"application/json"},
                timeout=10
            )
            log.info(f"Notif CC {cc_nombre}: {enviados_cc}/{total_cc}")
        except Exception as e:
            log.warning(f"Notif CC error: {e}")

# ── Actualizar Google Sheets fila por fila ─────────────────────────
_sheets_buffer = []
_sheets_ultimo_flush = 0

def _actualizar_sheets_fila(px, estado):
    """Acumula cambios y hace flush a Sheets cada 10 filas o 60s."""
    global _sheets_ultimo_flush
    SHEET_ID = os.environ.get("SHEET_ID","")
    CREDS    = os.environ.get("GOOGLE_CREDENTIALS","")
    if not SHEET_ID or not CREDS:
        return
    
    _sheets_buffer.append({
        "tel":    px.get("Telefono",""),
        "nombre": f"{px.get('Apellidos','')} {px.get('Nombres','')}",
        "cc":     px.get("CC_Nombre",""),
        "estado": estado,
        "ts":     ahora().strftime("%d/%m %H:%M"),
    })
    
    ahora_ts = time.time()
    if len(_sheets_buffer) >= 10 or (ahora_ts - _sheets_ultimo_flush) > 60:
        _flush_sheets()
        _sheets_ultimo_flush = ahora_ts

def _flush_sheets():
    """Envía el buffer acumulado a Google Sheets."""
    if not _sheets_buffer:
        return
    try:
        import json as _json
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        
        SHEET_ID = os.environ.get("SHEET_ID","")
        CREDS    = os.environ.get("GOOGLE_CREDENTIALS","")
        creds_d  = _json.loads(CREDS)
        creds    = service_account.Credentials.from_service_account_info(
            creds_d, scopes=["https://www.googleapis.com/auth/spreadsheets"])
        svc = build("sheets","v4",credentials=creds,cache_discovery=False)
        
        # Buscar/crear hoja "BIENVENIDA_E27"
        meta = svc.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
        nombres = [s["properties"]["title"] for s in meta.get("sheets",[])]
        
        if "BIENVENIDA_E27" not in nombres:
            svc.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body={
                "requests":[{"addSheet":{"properties":{"title":"BIENVENIDA_E27"}}}]
            }).execute()
            # Encabezado
            svc.spreadsheets().values().update(
                spreadsheetId=SHEET_ID, range="BIENVENIDA_E27!A1:E1",
                valueInputOption="RAW",
                body={"values":[["TELÉFONO","NOMBRE","CC","ESTADO","TIMESTAMP"]]}
            ).execute()
        
        rows = [[b["tel"],b["nombre"],b["cc"],b["estado"],b["ts"]] for b in _sheets_buffer]
        svc.spreadsheets().values().append(
            spreadsheetId=SHEET_ID, range="BIENVENIDA_E27!A:E",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()
        
        log.info(f"Sheets flush: {len(rows)} filas escritas")
        _sheets_buffer.clear()
    except Exception as e:
        log.warning(f"Sheets flush error: {e}")

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
            # Ventana horaria — si cierra, pausar hasta mañana
            if not _en_ventana_horaria():
                _add_log(f"⏸ 21:00 — Envío pausado. {enviados_ciclo} enviados en este ciclo. Reanuda a las 08:00.")
                if not _esperar_ventana():
                    break
            
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
            # Actualizar Google Sheets en background
            _actualizar_sheets_fila(px, "ENVIADO" if ok else "ERROR")
            
            if ok:
                _estado["enviados"] += 1
                enviados_ciclo += 1
                _add_log(f"Bienvenida OK: {px.get('Apellidos','')} {px.get('Nombres','').split()[0]} ({tel})")
                # Notificar a CC cada 10 enviados de su grupo
                _notif_cc_progreso(estado_previo, px.get("CC_Asignada",""), px.get("CC_Nombre",""), px.get("CC_Telefono",""))
            else:
                _estado["errores"] += 1
                _add_log(f"Bienvenida ERROR: {px.get('Apellidos','')} ({tel})", "WARNING")
            
            _estado["ultimo"] = f"{px.get('Apellidos','')} {px.get('Nombres','').split()[0] if px.get('Nombres') else ''}"
            time.sleep(PAUSA)

        resumen = (f"Bienvenida E27 completada — "
                   f"Enviados: {_estado['enviados']}, "
                   f"Errores: {_estado['errores']}, "
                   f"Pendientes: {len(pendientes) - enviados_ciclo}")
        _flush_sheets()  # flush final
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
