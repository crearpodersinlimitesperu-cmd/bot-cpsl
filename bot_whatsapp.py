"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V96: PROFESSIONAL IMO PORTAL (Full Names + Stable Navigation)
"""

import os, re, json, time, csv, io, random, logging, threading, queue
from flask import Flask, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN Y PERSISTENCIA
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
GERENTE_TEL = "51912379744" 

def ahora_lima(): return datetime.now(TZ_LIMA)

def get_csv_bd_path():
    for path in [".", DATA_DIR]:
        archivos = [f for f in os.listdir(path) if f.startswith("participantes_") and f.endswith(".csv")]
        if archivos:
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
            return os.path.join(path, archivos[0])
    return "base_datos.csv"

class Config:
    TOKEN               = os.environ.get("WA_TOKEN", "")
    PHONE_ID            = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN        = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    CSV_BD_PATH         = get_csv_bd_path()
    SESSIONS_PATH       = os.path.join(DATA_DIR, "sesiones.json")
    HISTORIAL_PATH      = os.path.join(DATA_DIR, "historial_chat.json")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# 2. GESTORES DE DATOS
# ══════════════════════════════════════════════════════════════
def set_sesion(tel, data):
    try:
        with FileLock(Config.SESSIONS_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            all_s = {}
            if os.path.exists(Config.SESSIONS_PATH):
                with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: all_s = json.load(f)
            all_s[str(tel)] = data
            with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f: json.dump(all_s, f, ensure_ascii=False, indent=2)
    except: pass

def get_sesion(tel):
    try:
        if os.path.exists(Config.SESSIONS_PATH):
            with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: return json.load(f).get(str(tel), {})
    except: pass
    return {}

def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            h = []
            if os.path.exists(Config.HISTORIAL_PATH):
                with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: h = json.load(f)
            h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": ahora_lima().strftime("%d/%m %H:%M")})
            if len(h) > 2000: h = h[-2000:]
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, indent=2)
    except: pass

# ══════════════════════════════════════════════════════════════
# 3. CRM E INTELIGENCIA (PROFESIONALIZACIÓN DE NOMBRES)
# ══════════════════════════════════════════════════════════════
def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "PROSPECTO", "nombre": None, "enrolados_todos": [], "enrolados_pendientes": []}
    if os.path.exists(Config.CSV_BD_PATH):
        with open(Config.CSV_BD_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                tel_px = str(row.get('Teléfono',''))[-9:]
                tel_imo = str(row.get('Tel. IMO',''))[-9:]
                # REGLA DE EXCELENCIA: Nombre Completo (Apellido + Nombre)
                nombre_completo = f"{row.get('Apellido','')}, {row.get('Nombre','')}".strip().title()
                
                asistio_c1 = row.get('C1','').strip().upper() == 'SI'
                if tel_px == tel_norm:
                    perfil["nombre"] = row.get('Nombre','').split()[0].title()
                    perfil["rol"] = "PX_REZAGADO_C1" if not asistio_c1 else "PROSPECTO"
                if tel_imo == tel_norm:
                    perfil["rol"] = "IMO"
                    status = "✅ Sentado" if asistio_c1 else "⏳ Pendiente"
                    perfil["enrolados_todos"].append(f"• {nombre_completo} ({status})")
                    if not asistio_c1: perfil["enrolados_pendientes"].append(f"• {nombre_completo} (Falta C1)")
    return perfil

FECHAS = "📅 *FECHAS 2026*\n🚀 C1: Vie 01 Mayo\n🔥 C2: Jue 14 Mayo\n👑 MJ: Vie 17 Abril"

# ══════════════════════════════════════════════════════════════
# 4. MOTOR DE FLUJO
# ══════════════════════════════════════════════════════════════
def enviar_mensaje(tel, texto, nombre_log="BOT"):
    if str(tel).startswith("SIM_"): append_historial(tel, nombre_log, texto, "out"); return True
    try:
        req_lib.post(f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages", 
                     json={"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}, 
                     headers={"Authorization": f"Bearer {Config.TOKEN}"}, timeout=10)
        append_historial(tel, nombre_log, texto, "out")
        return True
    except: return False

def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel)
        txt_up = str(texto).strip().upper()
        
        # 🟢 GESTIÓN DE SALUDOS O RESET
        if not sesion or txt_up in {"HOLA", "BUENAS", "MENU", "MENÚ", "0", "INICIO"}:
            perfil = obtener_perfil_crm(tel)
            sesion = {"perfil": perfil, "state": "MAIN"}
            set_sesion(tel, sesion)
            
            if perfil["rol"] == "IMO":
                msg = f"🌟 *Portal IMO — {perfil['nombre']}*\n\n1️⃣ Ver TODOS mis enrolados\n2️⃣ Ver PENDIENTES de C1\n3️⃣ Próximas fechas\n4️⃣ Coordinación IMO\n0️⃣ Salir"
            else:
                msg = f"🌟 *Hola {perfil['nombre'] or 'Líder'}*\n¡Bienvenido a CPSL Perú!\n\n1️⃣ Info Entrenamientos\n2️⃣ Ver fechas 2026\n3️⃣ Inversión y Pagos\n4️⃣ Coordinación\n0️⃣ Finalizar"
            enviar_mensaje(tel, msg, f"({perfil['rol']}) {perfil['nombre'] or 'User'}")
            return

        state = sesion.get("state", "MAIN")
        perfil = sesion.get("perfil", {})

        # 📊 LÓGICA IMO
        if perfil["rol"] == "IMO":
            if txt_up == "1":
                enviar_mensaje(tel, "📋 *TODOS TUS ENROLADOS:*\n\n" + ("\n".join(perfil['enrolados_todos']) if perfil['enrolados_todos'] else "Sin registros.") + "\n\n9️⃣ Volver")
            elif txt_up == "2":
                enviar_mensaje(tel, "⏳ *PENDIENTES DE C1:*\n\n" + ("\n".join(perfil['enrolados_pendientes']) if perfil['enrolados_pendientes'] else "¡Todos sentados! 🎉") + "\n\n9️⃣ Volver")
            elif txt_up == "3": enviar_mensaje(tel, FECHAS + "\n\n9️⃣ Volver")
            elif txt_up == "4":
                enviar_mensaje(tel, "✅ Ticket generado. Un coordinador de IMOs te escribirá pronto.")
                enviar_mensaje(Config.GERENTE_TEL, f"🚨 TICKET IMO: wa.me/{tel}")
            elif txt_up == "9": flujo_principal(tel, "MENU")
            return

        # 👤 LÓGICA PROSPECTO
        if state == "MAIN":
            if txt_up == "1":
                sesion["state"] = "INFO"; set_sesion(tel, sesion)
                enviar_mensaje(tel, "🚀 *C1:* 3 días de descubrimiento.\n🔥 *C2:* 4 días de inmersión.\n👑 *MJ:* 100 días de práctica.\n\n9️⃣ Volver")
            elif txt_up == "2": enviar_mensaje(tel, FECHAS + "\n\n9️⃣ Volver")
            elif txt_up == "3": enviar_mensaje(tel, "💳 *Pagos:* BCP 1934218307060 (Soles)\n\n9️⃣ Volver")
            elif txt_up == "4":
                enviar_mensaje(tel, "🙏 Derivando con un coordinador humano...")
                enviar_mensaje(Config.GERENTE_TEL, f"🚨 TICKET PX: wa.me/{tel}")
            elif txt_up == "9": flujo_principal(tel, "MENU")
            elif not txt_up.isnumeric():
                enviar_mensaje(tel, "Escribe *MENU* para ver las opciones disponibles.")
        
        elif state == "INFO":
            if txt_up == "9": sesion["state"] = "MAIN"; set_sesion(tel, sesion); flujo_principal(tel, "MENU")

    except Exception as e: logger.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════
# 5. ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
        return "Error", 403
    try:
        data = request.get_json(silent=True)
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        if msg.get("type") == "text": threading.Thread(target=flujo_principal, args=(msg["from"], msg["text"]["body"])).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return jsonify(json.load(f)), 200
    except: pass
    return jsonify([]), 200

@app.route("/api/mensaje_simulador", methods=["POST"])
def api_simulador():
    d = request.json
    tel, txt = d.get("telefono"), d.get("texto")
    append_historial(tel, "SIMULACIÓN", txt, "in")
    threading.Thread(target=flujo_principal, args=(tel, txt)).start()
    return jsonify({"status":"ok"}), 200

@app.route("/chat")
def chat_panel():
    with open("panel_chat.html", encoding="utf-8") as f: return f.read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
