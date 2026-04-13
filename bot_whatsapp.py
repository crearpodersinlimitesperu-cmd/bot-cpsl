"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V103: AUTO-FIX (GPS para Panel + Lector de Memoria Avanzado)
"""
import os, re, json, time, csv, logging, threading
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# --- 1. CONFIGURACIÓN ---
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # GPS para encontrar el panel

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    ASIGNACIONES_PATH = os.path.join(DATA_DIR, "asignaciones.json")
    
    # EQUIPO DE COORDINACIÓN OFICIAL
    STAFF = {
        "Diana": {"tel": "51912379744", "casos": 0},
        "Joyce": {"tel": "51933599903", "casos": 0},
        "Zuley": {"tel": "51933599864", "casos": 0}
    }

# --- 2. GESTIÓN DE ASIGNACIONES (Memoria con Auto-Fix) ---
def cargar_asignaciones():
    if os.path.exists(Config.ASIGNACIONES_PATH):
        try:
            with open(Config.ASIGNACIONES_PATH, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {}

def guardar_asignaciones(data):
    try:
        with FileLock(Config.ASIGNACIONES_PATH + ".lock", timeout=5):
            with open(Config.ASIGNACIONES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"Error en asignación: {e}")

def obtener_o_asignar_staff(tel_cliente):
    memoria = cargar_asignaciones()
    tel_str = str(tel_cliente)
    
    if tel_str in memoria:
        asig = memoria[tel_str]
        # Si el rompehielo lo guardó como diccionario, sacamos solo el nombre
        return asig.get("nombre", asig) if isinstance(asig, dict) else asig
    
    # Reparto Equitativo
    conteo = {nombre: 0 for nombre in Config.STAFF.keys()}
    for asig in memoria.values():
        nombre_asig = asig.get("nombre", asig) if isinstance(asig, dict) else asig
        if nombre_asig in conteo: conteo[nombre_asig] += 1
    
    # Elegir a la coordinadora con menos carga
    nombre_elegida = min(conteo, key=conteo.get)
    memoria[tel_str] = nombre_elegida
    guardar_asignaciones(memoria)
    return nombre_elegida

# --- 3. HISTORIAL Y PANEL ---
def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=5):
            if os.path.exists(Config.HISTORIAL_PATH):
                with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: h = json.load(f)
            else: h = []
            h.append({
                "telefono": str(telefono),
                "nombre": nombre or "Aliado",
                "texto": texto,
                "tipo": tipo,
                "hora": datetime.now(TZ_LIMA).strftime("%d/%m %H:%M")
            })
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h[-2000:], f, ensure_ascii=False)
    except: pass

# --- 4. MOTOR DE RESPUESTAS ---
def enviar_wa(tel, texto):
    url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    try:
        req_lib.post(url, json=payload, headers={"Authorization": f"Bearer {Config.TOKEN}"})
    except: pass

def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    append_historial(tel, nombre_wa, texto, "in")
    
    # Triggers de Derivación (Confirmar o Pedir Apoyo)
    if any(word in txt_up for word in ["SÍ", "SI", "APOYO", "DUDA", "STAFF", "INFORMACIÓN"]) or txt_up in ["1", "2", "3"]:
        nombre_coord = obtener_o_asignar_staff(tel)
        tel_coord = Config.STAFF[nombre_coord]["tel"]
        
        # Respuesta al Cliente
        resp = f"¡Excelente decisión! 🚀 Soy {nombre_coord}, tu Coordinadora de C1 y C2. He recibido tu solicitud y desde este momento te apoyaré personalmente en tu proceso."
        enviar_wa(tel, resp)
        append_historial(tel, "BOT", f"Derivado a {nombre_coord}", "out")
        
        # Alerta a la Coordinadora
        alerta = f"🚨 *NUEVA ASIGNACIÓN:* {nombre_wa} (wa.me/{tel}) requiere tu apoyo. Dijo: '{texto}'"
        enviar_wa(tel_coord, alerta)
    
    elif "PAGO" in txt_up:
        enviar_wa(tel, "💳 *Cuentas Corporativas:* BCP Soles 193-XXXX-XXXX. Envía tu captura por aquí.")
        append_historial(tel, "BOT", "Envió opciones de pago.", "out")
    else:
        msg = f"🌟 *Crear Poder Sin Límites*\n\nEscribe:\n*1* para Confirmar asistencia\n*2* si necesitas Apoyo o Información\n*PAGOS* para opciones bancarias."
        enviar_wa(tel, msg)
        append_historial(tel, "BOT", "Envió Menú Principal", "out")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json()
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        
        try:
            nombre = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        except:
            nombre = "Aliado"
            
        cuerpo = msg["text"]["body"] if "text" in msg else msg.get("button", {}).get("text", "")
        if cuerpo: threading.Thread(target=flujo_principal, args=(msg["from"], cuerpo, nombre)).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    if os.path.exists(Config.HISTORIAL_PATH):
        with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return jsonify(json.load(f)), 200
    return jsonify([]), 200

@app.route("/chat")
def chat_panel():
    try:
        # GPS Activado: Buscando el archivo en la misma ruta exacta del script
        html_path = os.path.join(BASE_DIR, "panel_chat.html")
        with open(html_path, encoding="utf-8") as f: 
            return f.read()
    except Exception as e: 
        logger.error(f"Error abriendo HTML: {e}")
        return "Panel no encontrado. Por favor, asegúrate de haber subido 'panel_chat.html' a GitHub.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
