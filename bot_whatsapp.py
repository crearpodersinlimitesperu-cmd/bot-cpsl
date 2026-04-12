"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V96: CORPORATE EXCELLENCE (Nombres completos para IMOs + Lógica de Flujo Robusta)
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
# 1. CONFIGURACIÓN Y PERSISTENCIA (Disk Render /data)
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
# 2. GESTORES DE DATOS Y SESIÓN
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
# 3. CRM E IDENTIFICACIÓN (PROFESIONALISMO EN NOMBRES)
# ══════════════════════════════════════════════════════════════
def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "PROSPECTO", "nombre": None, "enrolados_todos": [], "enrolados_pendientes": []}
    path = Config.CSV_BD_PATH
    
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    tel_px = str(row.get('Teléfono',''))[-9:]
                    tel_imo = str(row.get('Tel. IMO',''))[-9:]
                    # PROFESIONALISMO: Concatenar nombre y apellido
                    nombre_completo = f"{row.get('Nombre','').strip()} {row.get('Apellido','').strip()}".title()
                    asistio_c1 = row.get('C1','').strip().upper() == 'SI'
                    
                    if tel_px == tel_norm:
                        perfil["nombre"] = row.get('Nombre','').split()[0].title()
                        perfil["rol"] = "PX_REZAGADO_C1" if not asistio_c1 else "PROSPECTO"
                    
                    if tel_imo == tel_norm:
                        perfil["rol"] = "IMO"
                        status = "✅ Sentado" if asistio_c1 else "⏳ Pendiente"
                        perfil["enrolados_todos"].append(f"• {nombre_completo} ({status})")
                        if not asistio_c1:
                            perfil["enrolados_pendientes"].append(f"• {nombre_completo}")
        except: pass
    return perfil

FECHAS_MSG = "📅 *PRÓXIMAS FECHAS 2026*\n\n🚀 *C1:* Vie 01 Mayo (E27)\n🔥 *C2:* Jue 14 Mayo (E27)\n👑 *MJ:* Vie 17 Abril (E26)\n\n_Escribe 0 para volver._"

# ══════════════════════════════════════════════════════════════
# 4. MOTOR DE ENVÍO Y FLUJO
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
        
        # 🟢 GESTIÓN DE PALABRAS DE SALUDO O RESET
        saludos = {"HOLA", "BUENAS", "INICIO", "MENU", "MENÚ", "0"}
        if not sesion or txt_up in saludos:
            perfil = obtener_perfil_crm(tel)
            sesion = {"perfil": perfil, "state": "MAIN"}
            set_sesion(tel, sesion)
            
            if perfil["rol"] == "IMO":
                msg = f"🌟 *Portal del Líder IMO — {perfil['nombre']}*\n\n1️⃣ Ver TODOS mis enrolados\n2️⃣ Ver PENDIENTES de C1\n3️⃣ Consultar próximas fechas\n4️⃣ Hablar con Coordinación IMO\n\n0️⃣ Salir"
            else:
                msg = f"🌟 *Hola {perfil['nombre'] or 'Líder'}*\nBienvenido a CPSL Perú.\n\n1️⃣ Información de Entrenamientos\n2️⃣ Ver fechas 2026\n3️⃣ Inversión y Pagos\n4️⃣ Hablar con Coordinación\n\n0️⃣ Finalizar"
            enviar_mensaje(tel, msg, f"({perfil['rol']}) {perfil['nombre'] or 'User'}")
            return

        perfil = sesion.get("perfil", {})
        state = sesion.get("state", "MAIN")

        # 🔄 LÓGICA DE OPCIÓN "VOLVER" (9)
        if txt_up == "9":
            flujo_principal(tel, "MENU")
            return

        # 📊 RUTA IMO (Excelencia Profesional)
        if perfil["rol"] == "IMO":
            if txt_up == "1":
                lista = perfil.get("enrolados_todos", [])
                msg = "📋 *REPORTE COMPLETO DE ENROLADOS*\n\n" + ("\n".join(lista) if lista else "Sin registros.")
                enviar_mensaje(tel, msg + "\n\n9️⃣ Volver al menú")
            elif txt_up == "2":
                lista = perfil.get("enrolados_pendientes", [])
                msg = "⏳ *ENROLADOS PENDIENTES DE C1*\n\n" + ("\n".join(lista) if lista else "¡Todos tus invitados ya se sentaron! 🎉")
                enviar_mensaje(tel, msg + "\n\n9️⃣ Volver al menú")
            elif txt_up == "3":
                enviar_mensaje(tel, FECHAS_MSG)
            elif txt_up == "4":
                enviar_mensaje(tel, "✅ Ticket generado. Un coordinador te atenderá pronto.")
                enviar_mensaje(GERENTE_TEL, f"🚨 TICKET IMO: wa.me/{tel} ({perfil['nombre']})")
            return

        # 👤 RUTA PROSPECTO
        if state == "MAIN":
            if txt_up == "1":
                sesion["state"] = "INFO"; set_sesion(tel, sesion)
                enviar_mensaje(tel, "📘 *ENTRENAMIENTOS*\n\n1️⃣ Capítulo 1 (Descubrimiento)\n2️⃣ Capítulo 2 (Experiencia)\n3️⃣ Maestría (Práctica)\n\n9️⃣ Volver")
            elif txt_up == "2":
                enviar_mensaje(tel, FECHAS_MSG)
            elif txt_up == "3":
                enviar_mensaje(tel, "💳 *PAGOS*\nBCP Soles: 1934218307060\nCreación Cuántica E.I.R.L.\n\n9️⃣ Volver")
            elif txt_up == "4":
                enviar_mensaje(tel, "🙏 Te estamos derivando con un coordinador humano.")
                enviar_mensaje(GERENTE_TEL, f"🚨 TICKET PX: wa.me/{tel}")
            elif not txt_up.isnumeric():
                enviar_mensaje(tel, "Disculpa, no entendí. Por favor elige un número del menú o escribe 0 para reiniciar.")
        
        elif state == "INFO":
            if txt_up == "1": enviar_mensaje(tel, "🚀 *C1 (Descubrimiento):* Entrenamiento vivencial de 3 días para observar tus límites y romper paradigmas.\n\n9️⃣ Volver")
            elif txt_up == "2": enviar_mensaje(tel, "🔥 *C2 (La Experiencia):* 4 días inmersivos para rediseñar tu realidad desde la responsabilidad.\n\n9️⃣ Volver")
            elif txt_up == "3": enviar_mensaje(tel, "👑 *MJ (Maestría):* 100 días para forjar resultados sostenibles en tu vida.\n\n9️⃣ Volver")

    except Exception as e:
        logger.error(f"Error flujo: {e}")

# ══════════════════════════════════════════════════════════════
# 5. ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
        return "Error", 403
    data = request.get_json(silent=True)
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        if msg.get("type") == "text":
            threading.Thread(target=flujo_principal, args=(msg["from"], msg["text"]["body"])).start()
        else:
            enviar_mensaje(msg["from"], "⚠️ Por políticas corporativas, solo procesamos mensajes de texto. Por favor escribe tu duda. 🙏")
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
