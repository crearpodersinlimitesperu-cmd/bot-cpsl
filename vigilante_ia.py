"""
vigilante_ia.py — Vigilante Autónomo con IAs Gratuitas
=======================================================
Cada 15 minutos revisa el estado de todo el sistema,
usa las IAs de ia_multimodelo para analizar anomalías,
y reporta errores al Gerente por WhatsApp (texto libre).

100% GRATIS — usa DuckDuckGo AI, HuggingFace, Groq, Gemini Flash.
"""
import os, json, time, logging, re, traceback
from datetime import datetime
from zoneinfo import ZoneInfo
import requests as req

log = logging.getLogger("VIGILANTE")
TZ = ZoneInfo("America/Lima")

# ── Config ──
WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_API = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"
SHEET_ID = os.environ.get("CRM_SHEET_ID", "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y")

# Teléfono del gerente (Jose Sanchez)
GERENTE_TEL = os.environ.get("GERENTE_TEL", "573116024515")
GERENTE_NOMBRE = "Jose"

# Archivo de estado persistente
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR
ESTADO_FILE = os.path.join(DATA_DIR, "vigilante_estado.json")
ALERTAS_LOG = os.path.join(DATA_DIR, "vigilante_alertas.json")

# Throttle: no enviar más de 1 alerta del mismo tipo cada 6 horas
# y evitar bucles infinitos limitando el total diario
THROTTLE_HORAS = 6
MAX_ALERTAS_DIA = 3


def ahora():
    return datetime.now(TZ)


def _cargar_estado():
    try:
        if os.path.exists(ESTADO_FILE):
            with open(ESTADO_FILE) as f:
                return json.load(f)
    except: pass
    return {"alertas_enviadas": {}, "ultimo_chequeo": None, "errores_acumulados": []}


def _guardar_estado(estado):
    try:
        with open(ESTADO_FILE, "w") as f:
            json.dump(estado, f, indent=2, default=str)
    except: pass


def _enviar_alerta_whatsapp(mensaje):
    """Envía un mensaje de texto libre al gerente por WhatsApp."""
    if not WA_TOKEN:
        log.warning("[VIGILANTE] Sin WA_TOKEN, no puedo alertar por WhatsApp")
        return False
    
    tel = re.sub(r'[^\d]', '', GERENTE_TEL)
    headers = {"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"}
    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "text",
        "text": {"body": mensaje[:4000]}  # Límite WhatsApp
    }
    try:
        r = req.post(WA_API, headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            log.info(f"[VIGILANTE] Alerta enviada al gerente ({tel[:6]}***)")
            return True
        log.error(f"[VIGILANTE] Error WA {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log.error(f"[VIGILANTE] Error WA: {e}")
        return False


def _throttle_ok(tipo_alerta, estado):
    """Verifica si se puede enviar esta alerta (anti-spam y cuota diaria)."""
    # 1. Chequeo de cuota diaria global
    hoy = ahora().strftime("%d/%m")
    alertas_hoy = sum(1 for e in estado.get("errores_acumulados", []) if e.get("ts", "").startswith(hoy))
    if alertas_hoy >= MAX_ALERTAS_DIA:
        return False

    # 2. Chequeo de throttle por tipo
    ultimo = estado["alertas_enviadas"].get(tipo_alerta)
    if not ultimo:
        return True
    try:
        t = datetime.fromisoformat(ultimo).replace(tzinfo=TZ)
        horas = (ahora() - t).total_seconds() / 3600
        return horas >= THROTTLE_HORAS
    except:
        return True


def _registrar_alerta(tipo, detalle, estado):
    """Registra que se envió una alerta."""
    estado["alertas_enviadas"][tipo] = ahora().isoformat()
    estado["errores_acumulados"].append({
        "ts": ahora().strftime("%d/%m %H:%M"),
        "tipo": tipo,
        "detalle": detalle[:200]
    })
    # Mantener solo las últimas 50 alertas
    estado["errores_acumulados"] = estado["errores_acumulados"][-50:]


# ══════════════════════════════════════════════════════════════
# CHEQUEOS DEL SISTEMA
# ══════════════════════════════════════════════════════════════

def chequeo_bot_render():
    """Verifica que el bot en Render esté respondiendo."""
    try:
        r = req.get("https://bot-cpsl.onrender.com/", timeout=15)
        if r.status_code == 200:
            return {"ok": True, "msg": "Bot Render OK"}
        return {"ok": False, "msg": f"Bot Render respondio {r.status_code}"}
    except Exception as e:
        return {"ok": False, "msg": f"Bot Render CAIDO: {e}"}


def chequeo_sheets():
    """Verifica la conexión a Google Sheets y que las pestañas clave existan."""
    try:
        from sync_cloud import conectar_sheets
        c = conectar_sheets()
        if not c:
            return {"ok": False, "msg": "Sin conexion a Google Sheets (credenciales no configuradas)"}
        
        sh = c.open_by_key(SHEET_ID)
        tabs = [w.title for w in sh.worksheets()]
        
        # Pestañas reales usadas por el sistema (al menos una debe existir)
        # El sistema puede llamarlas CREARPSL_GESTION o GESTION_LLAMADAS
        requeridas_cualquiera = [
            ["CREARPSL_GESTION", "GESTION_LLAMADAS"],   # Al menos una de estas
            ["HISTORIAL"],                                # Esta sí debe existir
        ]
        
        faltantes = []
        for grupo in requeridas_cualquiera:
            if not any(t in tabs for t in grupo):
                faltantes.append(grupo[0])  # Reportar solo el nombre preferido
        
        if faltantes:
            return {"ok": False, "msg": f"Pestanas faltantes en Sheets: {faltantes}. Disponibles: {tabs[:5]}"}
        
        # Verificar datos en la hoja de gestión
        tab_datos = next((t for t in ["CREARPSL_GESTION", "GESTION_LLAMADAS"] if t in tabs), None)
        if tab_datos:
            ws = sh.worksheet(tab_datos)
            total = max(0, len(ws.get_all_values()) - 1)  # Sin header
            if total == 0:
                return {"ok": False, "msg": f"{tab_datos} está vacía — pegar datos desde CREARPSL"}
            return {"ok": True, "msg": f"Sheets OK — {tab_datos}: {total} registros | {len(tabs)} pestanas totales"}
        
        return {"ok": True, "msg": f"Sheets OK — {len(tabs)} pestanas"}
    except Exception as e:
        return {"ok": False, "msg": f"Error Sheets: {e}"}


def chequeo_ias():
    """Verifica cuántas IAs están respondiendo."""
    try:
        from ia_multimodelo import estado_ias
        ias = estado_ias()
        activas = sum(1 for ia in ias if ia["activa"])
        total = len(ias)
        
        if activas < 5:
            return {"ok": False, "msg": f"Solo {activas}/{total} IAs activas"}
        return {"ok": True, "msg": f"IAs OK: {activas}/{total} activas"}
    except Exception as e:
        return {"ok": False, "msg": f"Error revisando IAs: {e}"}


def chequeo_envios_imo():
    """Verifica que los envíos de IMO estén funcionando (mira el log de envíos)."""
    try:
        envio_path = os.path.join(DATA_DIR, "imo_envios.json")
        if not os.path.exists(envio_path):
            return {"ok": True, "msg": "Sin envios IMO registrados (normal si es primer dia)"}
        
        with open(envio_path) as f:
            envios = json.load(f)
        
        # Contar envíos de hoy
        hoy = ahora().strftime("%Y-%m-%d")
        enviados_hoy = sum(1 for k, v in envios.items() 
                          if "_last_sent" in k and isinstance(v, str) and hoy in v)
        
        return {"ok": True, "msg": f"Envios IMO hoy: {enviados_hoy}"}
    except Exception as e:
        return {"ok": False, "msg": f"Error revisando envios: {e}"}


def chequeo_web_crm():
    """Verifica que el CRM de Render esté respondiendo.
    
    NOTA: Render free tier puede dormir hasta 50s al primer ping.
    Un timeout NO es señal de caída — es normal. Solo alertamos si
    la respuesta es un error HTTP claro (4xx/5xx).
    """
    try:
        url = os.environ.get("CRM_URL", "https://crm-crearlima.onrender.com")
        # Timeout extendido a 55s para dar tiempo a que Render despierte
        r = req.get(url, timeout=55)
        if r.status_code == 200:
            return {"ok": True, "msg": "CRM Dashboard OK"}
        elif r.status_code in (502, 503, 504):
            return {"ok": False, "msg": f"CRM error de servidor ({r.status_code}) — posible crash en Render"}
        else:
            return {"ok": True, "msg": f"CRM respondio {r.status_code} (no critico)"}
    except req.exceptions.Timeout:
        # Timeout en Render = normal en plan gratuito. No es una caída real.
        return {"ok": True, "msg": "CRM en standby (Render free tier durmiendo — normal fuera de horario)"}
    except req.exceptions.ConnectionError as e:
        return {"ok": False, "msg": f"CRM SIN RED — error de conexion: {str(e)[:100]}"}
    except Exception as e:
        return {"ok": False, "msg": f"CRM error inesperado: {str(e)[:100]}"}


# ══════════════════════════════════════════════════════════════
# ANÁLISIS CON IA
# ══════════════════════════════════════════════════════════════

def analizar_con_ia(errores_encontrados):
    """Usa una IA gratuita para analizar los errores y generar un reporte útil."""
    if not errores_encontrados:
        return None
    
    try:
        from ia_multimodelo import ia_responder, PROMPTS
        
        # Configurar prompt de vigilante
        PROMPTS["vigilante"] = (
            "Eres un ingeniero de sistemas que monitorea una plataforma de gestion educativa. "
            "Analiza los errores detectados y genera un resumen BREVE (max 3 lineas) "
            "indicando: que paso, que tan grave es (CRITICO/MEDIO/BAJO), y que hacer. "
            "Responde en espanol. No uses emojis. Se directo."
        )
        
        errores_txt = "\n".join(f"- {e['tipo']}: {e['msg']}" for e in errores_encontrados)
        prompt = f"Errores detectados en el sistema:\n{errores_txt}\n\nAnalisis:"
        
        analisis = ia_responder(prompt, contexto="vigilante", timeout=10)
        return analisis
    except Exception as e:
        log.error(f"[VIGILANTE] Error en analisis IA: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════

def ejecutar_vigilancia():
    """Ejecuta todos los chequeos y envía alertas si hay problemas."""
    log.info(f"[VIGILANTE] Iniciando chequeo — {ahora().strftime('%H:%M')}")
    estado = _cargar_estado()
    
    chequeos = [
        ("BOT_RENDER", chequeo_bot_render),
        ("SHEETS", chequeo_sheets),
        ("IAS", chequeo_ias),
        ("ENVIOS_IMO", chequeo_envios_imo),
        ("CRM_WEB", chequeo_web_crm),
    ]
    
    errores = []
    resultados = []
    
    for tipo, fn in chequeos:
        try:
            resultado = fn()
            resultados.append({"tipo": tipo, **resultado})
            if not resultado["ok"]:
                errores.append({"tipo": tipo, "msg": resultado["msg"]})
        except Exception as e:
            errores.append({"tipo": tipo, "msg": f"Excepcion: {e}"})
    
    estado["ultimo_chequeo"] = ahora().isoformat()
    
    if errores:
        # Filtrar solo los que no han sido enviados recientemente
        nuevos = [e for e in errores if _throttle_ok(e["tipo"], estado)]
        
        if nuevos:
            # Pedir análisis a la IA
            analisis_ia = analizar_con_ia(nuevos)
            
            # Construir mensaje para el gerente
            hora_str = ahora().strftime("%d/%m %H:%M")
            msg = f"*ALERTA SISTEMA CPSL*\n{hora_str}\n\n"
            
            for e in nuevos:
                msg += f"- {e['tipo']}: {e['msg']}\n"
            
            if analisis_ia:
                msg += f"\n*Diagnostico IA:*\n{analisis_ia}\n"
            
            msg += f"\nChequeos OK: {sum(1 for r in resultados if r['ok'])}/{len(resultados)}"
            
            # Enviar por WhatsApp
            enviado = _enviar_alerta_whatsapp(msg)
            
            if enviado:
                for e in nuevos:
                    _registrar_alerta(e["tipo"], e["msg"], estado)
                log.info(f"[VIGILANTE] {len(nuevos)} alertas enviadas al gerente")
            else:
                log.error("[VIGILANTE] No se pudo enviar alerta al gerente")
        else:
            log.info(f"[VIGILANTE] {len(errores)} errores pero ya alertados (throttle)")
    else:
        log.info(f"[VIGILANTE] Todo OK — {len(resultados)} chequeos pasados")
    
    _guardar_estado(estado)
    return resultados


# ── Para uso como script independiente ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    resultados = ejecutar_vigilancia()
    for r in resultados:
        status = "OK" if r["ok"] else "FALLO"
        print(f"  [{status}] {r['tipo']}: {r['msg']}")
