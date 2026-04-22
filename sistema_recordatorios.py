"""
SISTEMA DE RECORDATORIOS CPSL — ANTI-SPAM META
===============================================
REGLAS FUNDAMENTALES:
1. Solo enviar a quien ya abrió conversación (ventana 24h activa)
2. MAX 1 mensaje por persona por día
3. MAX 50 mensajes por ciclo de envío
4. Pausa mínima 30s entre mensajes
5. Respetar STOP absoluto
6. NO usar plantillas para recordatorios — solo texto libre dentro ventana
7. Plantilla solo para el PRIMER contacto masivo (una vez)

ESTRATEGIA DE CONTACTO SIN SPAM:
- Ciclo 1 (día 0): Bot responde cuando PX escribe → confirma cita (costo $0)
- Ciclo 2 (día +1): Recordatorio amigable dentro de ventana activa (costo $0)  
- Ciclo 3 (día +2): Si no respondió → notificar al IMO para contacto personal
- Ciclo 4 (día +3): Solo si IMO confirmó interés → mensaje final del bot
- NO más mensajes después de día +3 sin nueva interacción
"""

import os, re, json, logging, time, threading
from datetime import datetime, timedelta, timezone

log = logging.getLogger("Recordatorios")
TZ  = timezone(timedelta(hours=-5))
def ahora(): return datetime.now(TZ)

DATA_DIR = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
RECORD_PATH = os.path.join(DATA_DIR, "recordatorios_estado.json")
_lk = threading.Lock()

# ── CARGA / GUARDADO DE ESTADO ────────────────────────────────────
def _cargar():
    try:
        if os.path.exists(RECORD_PATH):
            with open(RECORD_PATH, encoding="utf-8") as f:
                return json.load(f)
    except: pass
    return {}

def _guardar(estado):
    try:
        with open(RECORD_PATH, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"guardar_estado: {e}")

# ── VERIFICAR VENTANA DE 24H ──────────────────────────────────────
def tiene_ventana(historial_msgs, tel):
    """
    Retorna True si el PX escribió al bot en las últimas 23 horas.
    Solo enviamos dentro de esta ventana — NUNCA fuera.
    """
    ahora_dt = ahora()
    limite   = ahora_dt - timedelta(hours=23)
    for m in reversed(historial_msgs):
        if m.get("telefono") == tel and m.get("tipo") == "in":
            try:
                ts_str = m.get("ts") or m.get("hora","")
                # Intentar parsear — formato variable
                if len(ts_str) > 10:
                    # Formato dd/mm/yyyy HH:MM:SS o ISO
                    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                        try:
                            dt = datetime.strptime(ts_str[:19], fmt)
                            dt = dt.replace(tzinfo=TZ)
                            if dt > limite:
                                return True
                            break
                        except: continue
            except: pass
    return False

# ── MENSAJES DE RECORDATORIO (variados, no repetitivos) ──────────
RECORDATORIOS = [
    # Día 1 — Confirmación amigable
    lambda nombre, fecha: (
        f"Hola {nombre} \U0001F44B\n\n"
        f"Solo para confirmar tu lugar en C1 E27.\n"
        f"\U0001F4C5 {fecha} — Hotel José Antonio Deluxe, Miraflores.\n\n"
        f"¿Nos confirmas? 1️⃣ Sí  2️⃣ Info  3️⃣ No puedo"
    ),
    # Día 2 — Urgencia suave
    lambda nombre, fecha: (
        f"Hola {nombre}!\n\n"
        f"Los cupos para C1 E27 se están completando.\n"
        f"\U0001F4C5 {fecha}\n\n"
        f"¿Confirmas tu asistencia?\n"
        f"1️⃣ Sí, estaré  2️⃣ Necesito info  3️⃣ Ya no puedo"
    ),
    # Día 3 — Último recordatorio personal
    lambda nombre, fecha: (
        f"Hola {nombre}, te escribimos por última vez sobre C1 E27.\n\n"
        f"\U0001F4C5 {fecha}\n\n"
        f"Si no confirmas, liberaremos tu cupo.\n"
        f"1️⃣ Confirmo  2️⃣ Quiero hablar con alguien  3️⃣ No asistiré"
    ),
]

# ── LÓGICA PRINCIPAL DE RECORDATORIO ──────────────────────────────
def procesar_recordatorio(tel, nombre, fecha_evento, historial_msgs, wa_fn):
    """
    Decide si enviar recordatorio basado en el estado y la ventana de 24h.
    wa_fn: función wa(tel, msg, log_prefix) del bot principal
    Retorna: {"enviado": bool, "motivo": str, "ciclo": int}
    """
    with _lk:
        estado = _cargar()
        px     = estado.get(tel, {"ciclo": 0, "ultimo_envio": None, "stop": False})

    # Respetar STOP absoluto
    if px.get("stop"):
        return {"enviado": False, "motivo": "STOP", "ciclo": px["ciclo"]}

    # No más de 3 ciclos
    if px["ciclo"] >= 3:
        return {"enviado": False, "motivo": "MAX_CICLOS", "ciclo": px["ciclo"]}

    # Solo enviar dentro de ventana de 24h
    if not tiene_ventana(historial_msgs, tel):
        return {"enviado": False, "motivo": "SIN_VENTANA", "ciclo": px["ciclo"]}

    # No enviar más de 1 vez por día
    if px["ultimo_envio"]:
        try:
            ultimo = datetime.fromisoformat(px["ultimo_envio"])
            if (ahora() - ultimo).total_seconds() < 86400:
                return {"enviado": False, "motivo": "YA_ENVIADO_HOY", "ciclo": px["ciclo"]}
        except: pass

    # Seleccionar mensaje según ciclo
    ciclo_actual = px["ciclo"]
    pila         = nombre.split()[0].title() if nombre else "hola"
    msg_fn       = RECORDATORIOS[min(ciclo_actual, len(RECORDATORIOS)-1)]
    msg          = msg_fn(pila, fecha_evento)

    # Enviar
    ok = wa_fn(tel, msg, "RECORD")
    if ok:
        with _lk:
            estado = _cargar()
            estado[tel] = {
                "ciclo":       ciclo_actual + 1,
                "ultimo_envio":ahora().isoformat(),
                "stop":        False,
                "nombre":      nombre,
            }
            _guardar(estado)
        log.info(f"Recordatorio C{ciclo_actual+1} enviado: {nombre} ({tel})")
        return {"enviado": True, "motivo": "OK", "ciclo": ciclo_actual + 1}
    else:
        log.warning(f"Recordatorio fallo: {nombre} ({tel})")
        return {"enviado": False, "motivo": "ERROR_WA", "ciclo": ciclo_actual}

def marcar_stop(tel):
    """Marca STOP permanente para no volver a contactar."""
    with _lk:
        estado = _cargar()
        if tel not in estado:
            estado[tel] = {}
        estado[tel]["stop"] = True
        _guardar(estado)

def marcar_confirmado(tel):
    """Marca confirmación — no necesita más recordatorios."""
    with _lk:
        estado = _cargar()
        if tel not in estado:
            estado[tel] = {}
        estado[tel]["ciclo"]     = 99  # fin de ciclos
        estado[tel]["confirmado"]= True
        estado[tel]["stop"]      = False
        _guardar(estado)

def resumen_recordatorios():
    """Resumen del estado actual de recordatorios."""
    with _lk:
        estado = _cargar()
    total      = len(estado)
    confirmados= sum(1 for v in estado.values() if v.get("confirmado"))
    stops      = sum(1 for v in estado.values() if v.get("stop"))
    ciclo_1    = sum(1 for v in estado.values() if v.get("ciclo",0) == 1)
    ciclo_2    = sum(1 for v in estado.values() if v.get("ciclo",0) == 2)
    ciclo_3    = sum(1 for v in estado.values() if v.get("ciclo",0) >= 3)
    sin_ciclo  = sum(1 for v in estado.values() if v.get("ciclo",0) == 0)
    return {
        "total": total,
        "confirmados": confirmados,
        "stops": stops,
        "ciclo_1": ciclo_1,
        "ciclo_2": ciclo_2,
        "ciclo_3_mas": ciclo_3,
        "sin_contactar": sin_ciclo,
    }
