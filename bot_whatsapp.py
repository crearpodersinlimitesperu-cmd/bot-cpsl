"""
Bot WhatsApp — Creación Cuántica E.I.R.L.
✅ V108: SISTEMA INTEGRAL (Menús por Perfil + Identidad DNI + Staff Directo + Sheets)
"""
import os, json, csv, logging, threading
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- 1. CONFIGURACIÓN MAESTRA ---
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    CSV_ASIG_PATH = os.path.join(DATA_DIR, "Asignacion_C1.xlsx - Hoja1.csv")
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    ASIGNACIONES_PATH = os.path.join(DATA_DIR, "asignaciones.json")
    SESSIONS_PATH = os.path.join(DATA_DIR, "sesiones.json")
    URL_SHEETS = "https://hook.us2.make.com/ii4ut5wjlg1khsaes20coa7cgiom13n6"
    
    # DIRECTORIO DE STAFF
    STAFF = {
        "jmarin": {"nombre": "Joyce Marín", "tel": "51933599903"},
        "lpasquel": {"nombre": "Leyla Pasquel", "tel": "51919502385"},
        "zurteaga": {"nombre": "Zuley Urteaga", "tel": "51933599864"},
        "dmoscoso": {"nombre": "Diana Moscoso", "tel": "51912379744"},
        "lvalencia": {"nombre": "Linid Valencia", "tel": "51912379686"}
    }

# --- 2. MOTOR DE IDENTIDAD (Búsqueda en Asignacion_C1) ---
def obtener_identidad(tel):
    tel_norm = str(tel)[-9:]
    res = {"id_full": "Aliado Nuevo", "nombre": "Aliado", "dni": "S/D", "staff_tel": None, "staff_nom": "Reparto Equitativo", "rol": "NUEVO"}
    
    if os.path.exists(Config.CSV_ASIG_PATH):
        try:
            with open(Config.CSV_ASIG_PATH, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    if str(row.get('TelefonoMovil', ''))[-9:] == tel_norm:
                        dni = row.get('Identificación', 'S/D')
                        n = row.get('NombreCompleto', '').strip()
                        a = row.get('ApellidoCompleto', '').strip()
                        u = row.get('Usuario Registro', '').lower()
                        
                        res["id_full"] = f"{dni} - {n} {a}"
                        res["nombre"] = n.split()[0].title()
                        res["dni"] = dni
                        res["rol"] = "PARTICIPANTE"
                        if u in Config.STAFF:
                            res["staff_tel"] = Config.STAFF[u]["tel"]
                            res["staff_nom"] = Config.STAFF[u]["nombre"]
                        break
        except: pass
    return res

# --- 3. GESTIÓN DE DATOS ---
def enviar_wa(tel, texto):
    url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    req_lib.post(url, json=payload, headers={"Authorization": f"Bearer {Config.TOKEN}"})

def registrar_log(tel, identidad, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=5):
            h = json.load(open(Config.HISTORIAL_PATH)) if os.path.exists(Config.HISTORIAL_PATH) else []
            h.append({"telefono": str(tel), "nombre": identidad, "texto": texto, "tipo": tipo, "hora": datetime.now(TZ_LIMA).strftime("%d/%m %H:%M")})
            with open(Config.HISTORIAL_PATH, "w") as f: json.dump(h[-2000:], f, ensure_ascii=False)
    except: pass

# --- 4. CEREBRO DEL BOT (FLUIDO E INTELIGENTE) ---
def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    info = obtener_identidad(tel)
    identidad_sheets = info["id_full"] if info["id_full"] != "Aliado Nuevo" else f"NUEVO: {nombre_wa}"
    
    registrar_log(tel, identidad_sheets, texto, "in")
    
    # Sincronización con Google Sheets (Make)
    threading.Thread(target=lambda: req_lib.post(Config.URL_SHEETS, json={
        "fecha": datetime.now(TZ_LIMA).strftime("%d/%m/%Y %H:%M:%S"),
        "dni": info["dni"],
        "identidad": identidad_sheets,
        "telefono": str(tel),
        "mensaje": texto,
        "coordinadora": info["staff_nom"]
    })).start()

    # Cargar Sesión
    if os.path.exists(Config.SESSIONS_PATH):
        with open(Config.SESSIONS_PATH, "r") as f: sesiones = json.load(f)
    else: sesiones = {}
    
    estado = sesiones.get(str(tel), "INICIO")
    if txt_up in ["MENU", "0", "SALIR"]: estado = "INICIO"

    # MODO SILENCIO (Para no interrumpir a la coordinadora)
    if estado == "DERIVADO":
        target = info["staff_tel"] or Config.STAFF["jmarin"]["tel"]
        enviar_wa(target, f"💬 *Mensaje de {identidad_sheets}:*\n{texto}")
        return

    # --- LÓGICA DE MENÚS LOGRADOS ---
    respuesta = ""
    if estado == "INICIO":
        if info["rol"] == "PARTICIPANTE":
            respuesta = f"🌟 *Hola {info['nombre']}*\nBienvenido a tu portal de Crear Poder Sin Límites.\n\n1️⃣ Información de mis entrenamientos\n2️⃣ Ver fechas 2026\n3️⃣ Inversión y Pagos\n4️⃣ Hablar con mi Coordinadora\n0️⃣ Salir"
        else:
            respuesta = f"🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial.\n\n1️⃣ Información Entrenamientos\n2️⃣ Pagos e Inversión\n3️⃣ Fechas Disponibles\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar"
        sesiones[str(tel)] = "MENU_ABIERTO"
    
    elif txt_up == "1":
        respuesta = "📘 *Nuestros Entrenamientos:*\n\n🚀 *C1:* 3 días para romper paradigmas.\n🔥 *C2:* 4 días de inmersión total.\n👑 *MJ:* 100 días de maestría.\n\nResponde *4* para hablar con alguien del equipo."
    elif txt_up == "2":
        respuesta = "📅 *FECHAS 2026:*\n🚀 C1: 01 de Mayo\n🔥 C2: 14 de Mayo\n👑 MJ: 17 de Abril\n\n9️⃣ Volver al menú."
    elif txt_up == "3":
        respuesta = "💳 *MÉTODOS DE PAGO:*\n- BCP Soles: 193-XXXX-XXXX\n- Yape/Plin: 908652308\n\nPor favor, envía tu comprobante por este medio."
    elif txt_up == "4":
        target = info["staff_tel"] or Config.STAFF["jmarin"]["tel"]
        respuesta = f"🙏 ¡Hola {info['nombre']}! Soy del equipo de Coordinación. He recibido tu solicitud y te atenderé personalmente."
        enviar_wa(target, f"🚨 *ATENCIÓN:* {identidad_sheets} (wa.me/{tel}) solicita apoyo humano.")
        sesiones[str(tel)] = "DERIVADO"

    if respuesta:
        enviar_wa(tel, respuesta)
        registrar_log(tel, "BOT", respuesta, "out")

    with open(Config.SESSIONS_PATH, "w") as f: json.dump(sesiones, f)

# --- 5. RUTAS WEB (DASHBOARD Y API) ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json()
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        cuerpo = msg["text"]["body"] if "text" in msg else ""
        if cuerpo: threading.Thread(target=flujo_principal, args=(msg["from"], cuerpo, "Aliado")).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    if os.path.exists(Config.HISTORIAL_PATH):
        with open(Config.HISTORIAL_PATH, "r") as f: return jsonify(json.load(f)), 200
    return jsonify([]), 200

@app.route("/chat")
def chat_panel():
    try:
        with open(os.path.join(BASE_DIR, "panel_chat.html"), encoding="utf-8") as f: return f.read()
    except: return "Panel no encontrado en el servidor.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
