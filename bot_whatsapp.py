"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V102: SMART ROUTING (Memoria, Reparto Equitativo Zuley/Diana/Joyce + Panel)
"""
import os, re, json, time, csv, logging, threading
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# --- 1. CONFIGURACIÓN MAESTRA ---
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    ASIGNACIONES_PATH = os.path.join(DATA_DIR, "asignaciones.json")
    
    # 🌟 EQUIPO DE COORDINACIÓN
    COORDINADORAS = {
        "Diana": "51912379744",
        "Joyce": "51933599903",
        "Zuley": "51933599864"
    }

# --- 2. MOTOR DE MEMORIA Y ASIGNACIÓN EQUITATIVA ---
def cargar_asignaciones():
    try:
        if os.path.exists(Config.ASIGNACIONES_PATH):
            with open(Config.ASIGNACIONES_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return {}

def guardar_asignaciones(data):
    try:
        with FileLock(Config.ASIGNACIONES_PATH + ".lock", timeout=5):
            with open(Config.ASIGNACIONES_PATH, "w", encoding="utf-8") as f: 
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"Error guardando asignación: {e}")

def obtener_o_asignar_coordinadora(telefono_cliente):
    asignaciones = cargar_asignaciones()
    tel_str = str(telefono_cliente)
    
    # Si ya es su clienta, devolver a la misma coordinadora
    if tel_str in asignaciones:
        return asignaciones[tel_str]
    
    # Si es nuevo, buscar a la coordinadora con menos casos (Reparto Equitativo)
    conteo = {nombre: 0 for nombre in Config.COORDINADORAS.keys()}
    for caso in asignaciones.values():
        nombre_coord = caso.get("nombre")
        if nombre_coord in conteo:
            conteo[nombre_coord] += 1
            
    # Elegir la que tenga el mínimo de casos
    coord_elegida = min(conteo, key=conteo.get)
    nueva_asignacion = {"nombre": coord_elegida, "tel": Config.COORDINADORAS[coord_elegida]}
    
    # Guardar en memoria permanente
    asignaciones[tel_str] = nueva_asignacion
    guardar_asignaciones(asignaciones)
    
    return nueva_asignacion

# --- 3. HISTORIAL PARA EL PANEL (/chat) ---
def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return []

def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=5):
            h = get_historial()
            hora = datetime.now(TZ_LIMA).strftime("%d/%m %H:%M")
            h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": hora})
            if len(h) > 2000: h = h[-2000:]
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"Error guardando historial: {e}")

# --- 4. MOTOR DE ENVÍO DE MENSAJES ---
def enviar_mensaje(tel, texto, log_name="BOT"):
    url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    try:
        req_lib.post(url, json=payload, headers=headers, timeout=10)
        append_historial(tel, log_name, texto, "out")
        return True
    except Exception as e:
        logger.error(f"Error enviando mensaje: {e}")
        return False

# --- 5. CEREBRO DEL BOT (RESPUESTAS) ---
def flujo_principal(tel, texto, nombre_px="Aliado"):
    txt_up = str(texto).strip().upper()
    append_historial(tel, nombre_px, texto, "in")
    
    # 1. PX Confirma (SÍ)
    if "SÍ" in txt_up or "SI" in txt_up or "CONFIRM" in txt_up or txt_up == "1":
        coord = obtener_o_asignar_coordinadora(tel)
        msg_px = f"¡Excelente elección! 🚀 Registramos tu confirmación.\n\nSoy {coord['nombre']} y seré tu coordinadora. En breve me comunicaré contigo para asistirte con el registro formal.\n\nMientras tanto, puedes ver los métodos de inversión escribiendo *PAGOS*."
        enviar_mensaje(tel, msg_px)
        enviar_mensaje(coord['tel'], f"🚨 *CONFIRMACIÓN C1:* Un prospecto (wa.me/{tel}) acaba de confirmar asistencia y se te ha asignado a ti.")
        
    # 2. PX o IMO pide Apoyo
    elif "DUDA" in txt_up or "APOYO" in txt_up or "INFORMACIÓN" in txt_up or txt_up == "2" or txt_up == "3":
        coord = obtener_o_asignar_coordinadora(tel)
        msg_px = f"Con mucho gusto. Soy {coord['nombre']} de Coordinación. He recibido tu solicitud y seré la encargada de apoyarte personalmente. 🙏"
        enviar_mensaje(tel, msg_px)
        enviar_mensaje(coord['tel'], f"🚨 *SOLICITUD DE STAFF:* Se te asignó a wa.me/{tel}. Dijo: '{texto}'")
        
    # 3. Solicitud de Pagos
    elif "PAGO" in txt_up:
        msg_pago = f"💳 *Opciones de Inversión:*\n\n- BCP Soles: 193-XXXX-XXXX\n- Yape/Plin: 908652308\n\nPor favor, envía la captura de tu operación por este medio."
        enviar_mensaje(tel, msg_pago)
        
    # 4. Menú General
    else:
        msg = f"🌟 *Crear Poder Sin Límites*\n\nEscribe:\n*1* para Confirmar asistencia\n*2* si necesitas Apoyo o Información\n*PAGOS* para opciones bancarias."
        enviar_mensaje(tel, msg)

# --- 6. RUTAS WEB ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json(silent=True)
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        cuerpo = msg["text"]["body"] if msg["type"] == "text" else msg.get("button", {}).get("text", "")
        nombre_wa = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        if cuerpo: threading.Thread(target=flujo_principal, args=(msg["from"], cuerpo, nombre_wa)).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial(): return jsonify(get_historial()), 200

@app.route("/chat")
def chat_panel():
    try:
        with open("panel_chat.html", encoding="utf-8") as f: return f.read()
    except: return "Panel no encontrado.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
