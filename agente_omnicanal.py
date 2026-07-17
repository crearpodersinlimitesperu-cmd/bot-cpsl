import os
import sys
import time
import json
import logging
import threading
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Reconfigurar codificación para evitar caídas en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Importar ecosistema CREAR LIMA
try:
    from sms_gateway import SMSGateway
    from bot_correo_ia import EMAIL_GERENCIA, EMAIL_PASS, disparar_alertas_matutinas, procesar_respuestas_correo
    from ia_multimodelo import ia_responder, ia_clasificar
except ImportError as e:
    print(f"[WARNING] Faltan módulos del CRM/Bot local: {e}")

load_dotenv()

app = Flask(__name__)
logger = logging.getLogger("Omnicanal")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

sms_gw = SMSGateway()

# ── 1. GESTOR DE ENVÍOS OMNICANAL ──
def enviar_mensaje_omnicanal(tel, email, mensaje_sms, mensaje_correo_html, asunto="Notificación CPSL"):
    """
    Intenta enviar mensaje por SMS y Correo.
    Si el correo está disponible, manda un HTML enriquecido.
    Siempre manda SMS como fallback o notificación rápida.
    """
    enviado_sms = False
    enviado_correo = False

    # 1. Enviar SMS
    if tel:
        try:
            enviado_sms = sms_gw.send_sms(tel, mensaje_sms)
        except Exception as e:
            logger.error(f"Error SMS a {tel}: {e}")

    # 2. Enviar Correo (si hay email)
    if email and "@" in email:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_GERENCIA, EMAIL_PASS)
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_GERENCIA
            msg['To'] = email
            msg['Subject'] = asunto
            msg.attach(MIMEText(mensaje_correo_html, 'html'))
            
            server.send_message(msg)
            server.quit()
            enviado_correo = True
            logger.info(f"✅ Correo enviado a {email}")
        except Exception as e:
            logger.error(f"❌ Error correo a {email}: {e}")

    return {"sms_ok": enviado_sms, "correo_ok": enviado_correo}

# ── 2. WEBHOOKS DE RECEPCIÓN ──
@app.route("/api/webhook_sms", methods=["POST", "GET"])
def webhook_sms_entrante():
    """
    Endpoint para recibir SMS entrantes desde MacroDroid u otro servicio.
    Se espera que MacroDroid haga un GET o POST a esta URL.
    Ejemplo MacroDroid: HTTP GET /api/webhook_sms?tel=[numero]&mensaje=[sms_text]
    """
    data = request.json if request.is_json else request.args
    tel = data.get("tel") or data.get("numero", "")
    mensaje = data.get("mensaje", "").strip()

    if not tel or not mensaje:
        return jsonify({"error": "Faltan parámetros"}), 400

    logger.info(f"📨 SMS RECIBIDO de {tel}: {mensaje}")

    # Procesamiento Inteligente
    cat = ia_clasificar(mensaje)
    logger.info(f"🧠 Clasificación SMS: {cat}")

    # Generar respuesta corta para SMS (Evitar textos largos)
    prompt_sms = f"Participante SMS: {tel}\nMensaje: '{mensaje}'\nCategoría: {cat}\nResponde en máximo 140 caracteres, directo y conciso."
    respuesta_ia = ia_responder(prompt_sms, contexto="px_respuesta")

    if respuesta_ia:
        # Enviar respuesta automática por SMS
        threading.Thread(target=sms_gw.send_sms, args=(tel, respuesta_ia), daemon=True).start()
    
    return jsonify({"status": "recibido", "clasificacion": cat, "respuesta_enviada": respuesta_ia}), 200

# ── 3. SCHEDULER DE CORREOS Y ALERTAS (Heredado de bot_correo_ia) ──
def _scheduler_omnicanal():
    logger.info("🤖 AGENTE OMNICANAL INICIADO. VIGILANDO CORREOS Y TAREAS PROGRAMADAS...")
    alertas_enviadas_hoy = False
    
    while True:
        try:
            ahora = datetime.now()
            dia_semana = ahora.weekday()
            hora = ahora.hour
            minuto = ahora.minute
            
            # Alertas Matutinas (8:50 AM)
            if dia_semana in [1, 2, 3, 4] and hora == 8 and minuto == 50:
                if not alertas_enviadas_hoy:
                    # OJO: disparar_alertas_matutinas usa WA internamente. 
                    # Lo hemos adaptado para que envíe correo y SMS si fallara WA.
                    disparar_alertas_matutinas()
                    alertas_enviadas_hoy = True
            
            if hora == 0:
                alertas_enviadas_hoy = False
                
            # Procesar Respuestas de Correo
            if minuto % 10 == 0:
                procesar_respuestas_correo()
                
        except Exception as e:
            logger.error(f"Error en scheduler omnicanal: {e}")
            
        time.sleep(60)

# Iniciar Schedulers
threading.Thread(target=_scheduler_omnicanal, daemon=True, name="scheduler_omni").start()

@app.route("/")
def home():
    return jsonify({"agente": "Omnicanal CPSL", "estado": "Activo", "whatsapp": "Desconectado"}), 200

def is_already_running(script_name):
    import os
    try:
        import psutil
        my_pid = os.getpid()
        my_ppid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                if name and 'python' in name.lower():
                    pid = proc.info['pid']
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if pid != my_pid and pid != my_ppid and script_name in cmdline_str:
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except:
        return False

if __name__ == "__main__":
    if is_already_running("agente_omnicanal.py"):
        logger.error("El agente omnicanal ya se encuentra en ejecución en otro proceso. Cancelando inicio.")
        sys.exit(1)
    logger.info("🚀 Arrancando Agente Omnicanal...")
    app.run(host="0.0.0.0", port=10000, debug=False)
