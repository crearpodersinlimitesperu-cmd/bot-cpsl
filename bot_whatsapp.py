"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V102: SMART ROUTING (Diana, Joyce, Zuley + Memoria Permanente)
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

# --- 2. GESTIÓN DE ASIGNACIONES (Memoria) ---
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
        return memoria[tel_str] # Ya tiene coordinadora asignada
    
    # Reparto Equitativo: Contar casos actuales
    conteo = {nombre: 0 for nombre in Config.STAFF.keys()}
    for nombre_asig in memoria.values():
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
    req_lib.post(url, json=payload, headers={"Authorization": f"Bearer {Config.TOKEN}"})

def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    append_historial(tel, nombre_wa, texto, "in")
    
    # Triggers de Derivación (Confirmar o Pedir Apoyo)
    if any(word in txt_up for word in ["SÍ", "SI", "APOYO", "DUDA", "STAFF"]) or txt_up in ["1", "2"]:
        nombre_coord = obtener_o_asignar_staff(tel)
        tel_coord = Config.STAFF[nombre_coord]["tel"]
        
        # Respuesta al Cliente
        resp = f"¡Excelente decisión, {nombre_wa}! 🚀 Soy {nombre_coord}, tu Coordinadora de C1 y C2. He recibido tu solicitud y desde este momento te apoyaré personalmente en tu proceso."
        enviar_wa(tel, resp)
        append_historial(tel, "BOT", f"Derivado a {nombre_coord}", "out")
        
        # Alerta a la Coordinadora
        alerta = f"🚨 *NUEVA ASIGNACIÓN:* {nombre_wa} (wa.me/{tel}) requiere tu apoyo. Dijo: '{texto}'"
        enviar_wa(tel_coord, alerta)
    
    elif "PAGO" in txt_up:
        enviar_wa(tel, "💳 *Cuentas Corporativas:* BCP Soles 193-XXXX-XXXX. Envía tu captura por aquí.")
    else:
        enviar_wa(tel, f"🌟 *Crear Poder Sin Límites*\nHola {nombre_wa}. Escribe:\n*1* para Confirmar asistencia.\n*2* para hablar con Staff.\n*PAGOS* para números de cuenta.")

@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json()
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        nombre = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        cuerpo = msg["text"]["body"] if "text" in msg else msg.get("button", {}).get("text", "")
        threading.Thread(target=flujo_principal, args=(msg["from"], cuerpo, nombre)).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    if os.path.exists(Config.HISTORIAL_PATH):
        with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return jsonify(json.load(f)), 200
    return jsonify([]), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
