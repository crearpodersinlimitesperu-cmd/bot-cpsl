"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V100: MASTER SHIELD (Alertas Corporativas + Panel Impecable)
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

def get_csv_bd_path():
    for path in [".", DATA_DIR]:
        archivos = [f for f in os.listdir(path) if f.startswith("campana_") and f.endswith(".csv")]
        if archivos:
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
            return os.path.join(path, archivos[0])
    return "base_datos.csv"

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    CSV_BD_PATH = get_csv_bd_path()
    SESSIONS_PATH = os.path.join(DATA_DIR, "sesiones.json")
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    GERENTE_TEL = "51919563284" # <--- TU NÚMERO CORPORATIVO INTEGRADO

# --- 2. HISTORIAL PARA EL PANEL (/chat) ---
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
    except Exception as e:
        logger.error(f"Error guardando historial: {e}")

# --- 3. LECTURA DE BASE DE DATOS (CRM) ---
def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "PROSPECTO", "nombre": "Aliado", "enrolados_pendientes": []}
    if os.path.exists(Config.CSV_BD_PATH):
        try:
            with open(Config.CSV_BD_PATH, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tel_px = str(row.get('TELÉFONO PX', row.get('Teléfono', '')))[-9:]
                    tel_imo = str(row.get('TEL. IMO', row.get('Tel. IMO', '')))[-9:]
                    nombre_pref = row.get('PREF.', row.get('Nombre', 'Aliado')).strip()
                    nombre_full = f"{row.get('APELLIDO', '')} {row.get('NOMBRE', '')}".strip()
                    
                    if tel_px == tel_norm:
                        perfil["nombre"] = nombre_pref
                        perfil["rol"] = "PROSPECTO"
                    
                    if tel_imo == tel_norm:
                        perfil["rol"] = "IMO"
                        perfil["nombre"] = row.get('NOMBRE IMO', 'Líder').split()[0].title()
                        if nombre_full:
                            perfil["enrolados_pendientes"].append(f"• {nombre_full}")
        except Exception as e:
            logger.error(f"Error leyendo CSV: {e}")
    return perfil

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
def flujo_principal(tel, texto):
    txt_up = str(texto).strip().upper()
    perfil = obtener_perfil_crm(tel)
    nombre = perfil['nombre']
    
    # 🌟 BLINDAJE DE PANEL: Primero guardamos el mensaje en tu panel, pase lo que pase.
    append_historial(tel, nombre, texto, "in")
    
    # 1. PX Confirma (Botón 1 o SÍ)
    if "SÍ" in txt_up or "SI" in txt_up or "CONFIRM" in txt_up or txt_up == "1":
        msg_px = f"¡Excelente elección, {nombre}! 🚀 Registramos tu confirmación.\n\nEn breve nuestro equipo se comunicará contigo para asistirte con el registro formal en el Hotel José Antonio Deluxe.\n\nMientras tanto, si deseas, puedes ver los métodos de inversión escribiendo *PAGOS*."
        enviar_mensaje(tel, msg_px)
        enviar_mensaje(Config.GERENTE_TEL, f"🚨 *CONFIRMACIÓN C1:* {nombre} (wa.me/{tel}) acaba de confirmar asistencia.")
        
    # 2. PX o IMO pide Apoyo (Botón 2, 3 o Dudas)
    elif "DUDA" in txt_up or "APOYO" in txt_up or "INFORMACIÓN" in txt_up or txt_up == "2" or txt_up == "3":
        msg_px = f"Con mucho gusto, {nombre}. Te estamos derivando con nuestro equipo de coordinación para brindarte el apoyo que necesitas. 🙏"
        enviar_mensaje(tel, msg_px)
        enviar_mensaje(Config.GERENTE_TEL, f"🚨 *SOLICITUD DE STAFF:* {nombre} (wa.me/{tel}) requiere asistencia. Dijo: '{texto}'")
        
    # 3. IMO Pide su lista de Pendientes
    elif "PENDIENTES" in txt_up and perfil["rol"] == "IMO":
        lista = perfil["enrolados_pendientes"]
        msg = f"👑 *Radar de Líder IMO - {nombre}*\n\nEstos son tus invitados pendientes para el C1 (E27):\n\n" + ("\n".join(lista) if lista else "🎉 ¡No tienes pendientes en esta lista, excelente gestión!")
        enviar_mensaje(tel, msg)
        
    # 4. Solicitud de Pagos
    elif "PAGO" in txt_up:
        msg_pago = f"💳 *Opciones de Inversión, {nombre}:*\n\n- BCP Soles: 193-XXXX-XXXX\n- Yape/Plin: 908652308\n\nPor favor, envía la captura de tu operación por este mismo medio."
        enviar_mensaje(tel, msg_pago)
        
    # 5. Menú General / Cualquier otra palabra
    else:
        if perfil["rol"] == "IMO":
            msg = f"🌟 *Portal IMO — {nombre}*\n\nEscribe:\n*PENDIENTES* para ver tu lista de enrolados.\n*APOYO* para hablar con nuestro Staff."
        else:
            msg = f"🌟 *Crear Poder Sin Límites — {nombre}*\n\nEscribe:\n*1* para Confirmar asistencia\n*2* si necesitas Apoyo o Información\n*PAGOS* para opciones bancarias."
        enviar_mensaje(tel, msg)

# --- 6. RUTAS WEB (WEBHOOK Y PANEL) ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: 
            return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json(silent=True)
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        cuerpo = msg["text"]["body"] if msg["type"] == "text" else msg.get("button", {}).get("text", "")
        if cuerpo: 
            threading.Thread(target=flujo_principal, args=(msg["from"], cuerpo)).start()
    except: 
        pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial(): 
    return jsonify(get_historial()), 200

@app.route("/chat")
def chat_panel():
    try:
        with open("panel_chat.html", encoding="utf-8") as f: return f.read()
    except: 
        return "Panel no encontrado. Asegúrate de tener el archivo panel_chat.html en tu repositorio.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
