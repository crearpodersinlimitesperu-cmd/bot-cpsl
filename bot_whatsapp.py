"""
Bot WhatsApp — Creación Cuántica E.I.R.L.
✅ V108.2: CORRECCIÓN DE RUTAS + SEGMENTACIÓN TOTAL
"""
import os, json, csv, logging, threading, random
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
app = Flask(__name__)

# --- 1. CONFIGURACIÓN MAESTRA ---
TZ_LIMA = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    # Archivos de Datos
    CSV_ASIG_PATH = os.path.join(BASE_DIR, "Asignacion_C1.xlsx - Hoja1.csv")
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    SESSIONS_PATH = os.path.join(DATA_DIR, "sesiones.json")
    URL_SHEETS = "https://hook.us2.make.com/ii4ut5wjlg1khsaes20coa7cgiom13n6"
    
    # STAFF OFICIAL SEDE LIMA
    STAFF = {
        "jmarin": {"nombre": "Joyce Marín", "tel": "51933599903"},
        "lpasquel": {"nombre": "Leyla Pasquel", "tel": "51919502385"},
        "zurteaga": {"nombre": "Zuley Urteaga", "tel": "51933599864"},
        "dmoscoso": {"nombre": "Diana Moscoso", "tel": "51912379744"},
        "lvalencia": {"nombre": "Linid Valencia", "tel": "51912379686"}
    }

# --- 2. MOTOR DE IDENTIDAD (DNI + STAFF) ---
def obtener_perfil(tel):
    tel_norm = str(tel)[-9:]
    res = {"tipo": "NUEVO", "id_full": "Aliado Nuevo", "nombre": "Aliado", "dni": "S/D", "staff_tel": None, "staff_nom": "Reparto Equitativo", "gente": []}
    
    if os.path.exists(Config.CSV_ASIG_PATH):
        try:
            with open(Config.CSV_ASIG_PATH, 'r', encoding='utf-8-sig') as f:
                filas = list(csv.DictReader(f))
                for row in filas:
                    # Identificar al Participante
                    if str(row.get('TelefonoMovil', ''))[-9:] == tel_norm:
                        dni, n, a, u = row.get('Identificación',''), row.get('NombreCompleto',''), row.get('ApellidoCompleto',''), row.get('Usuario Registro','').lower()
                        res.update({"tipo": "PX", "id_full": f"{dni} - {n} {a}", "nombre": n.split()[0].title(), "dni": dni})
                        if u in Config.STAFF: res.update({"staff_tel": Config.STAFF[u]["tel"], "staff_nom": Config.STAFF[u]["nombre"]})
                    # Identificar si es un IMO y traer su gente
                    if str(row.get('IdentificacionIMO', ''))[-9:] == tel_norm:
                        res["tipo"] = "IMO"
                        res["gente"].append(f"• {row.get('NombreCompleto','')} {row.get('ApellidoCompleto','')}")
        except Exception as e: logger.error(f"Error lectura CSV: {e}")
    return res

# --- 3. FUNCIONES DE CORE ---
def enviar_wa(tel, texto):
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    req_lib.post(f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages", json=payload, headers={"Authorization": f"Bearer {Config.TOKEN}"})

def registrar_log(tel, identidad, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=5):
            h = json.load(open(Config.HISTORIAL_PATH)) if os.path.exists(Config.HISTORIAL_PATH) else []
            h.append({"telefono": str(tel), "nombre": identidad, "texto": texto, "tipo": tipo, "hora": datetime.now(TZ_LIMA).strftime("%d/%m %H:%M")})
            with open(Config.HISTORIAL_PATH, "w") as f: json.dump(h[-2000:], f, ensure_ascii=False)
    except: pass

# --- 4. FLUJO DE MENÚS (IMO / PX / NUEVO) ---
def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    p = obtener_perfil(tel)
    id_h = p["id_full"] if p["tipo"] != "NUEVO" else f"NUEVO: {nombre_wa}"
    
    registrar_log(tel, id_h, texto, "in")
    
    # Enviar a Google Sheets
    threading.Thread(target=lambda: req_lib.post(Config.URL_SHEETS, json={
        "fecha": datetime.now(TZ_LIMA).strftime("%d/%m/%Y %H:%M:%S"), "dni": p["dni"], "identidad": id_h, "tipo": p["tipo"], "mensaje": texto, "staff": p["staff_nom"]
    })).start()

    sesiones = json.load(open(Config.SESSIONS_PATH)) if os.path.exists(Config.SESSIONS_PATH) else {}
    estado = sesiones.get(str(tel), "INICIO")
    if txt_up in ["MENU", "0"]: estado = "INICIO"

    if estado == "DERIVADO":
        enviar_wa(p["staff_tel"] or Config.STAFF["jmarin"]["tel"], f"💬 *Mensaje de {id_h}:*\n{texto}")
        return

    resp = ""
    if p["tipo"] == "IMO": # MENÚ GRADUADOS
        if estado == "INICIO":
            resp = f"👑 *Portal Líder IMO — {p['nombre']}*\n\n1️⃣ Ver mi gente pendiente (C1)\n2️⃣ Solicitar ser ALIADO\n3️⃣ Fechas 2026\n4️⃣ Hablar con Coordinación\n0️⃣ Salir"
            sesiones[str(tel)] = "MENU_IMO"
        elif txt_up == "1": resp = f"👥 *Gente pendiente de C1:*\n" + "\n".join(p["gente"][:10]) + "\n\n9️⃣ Volver"
    
    elif p["tipo"] == "PX": # MENÚ PROSPECTOS
        if estado == "INICIO":
            resp = f"🌟 *Hola {p['nombre']}*\n¡Listo para tu siguiente nivel!\n\n1️⃣ Información C1/C2\n2️⃣ Fechas Disponibles\n3️⃣ Inversión y Pagos\n4️⃣ Hablar con Coordinación\n0️⃣ Salir"
            sesiones[str(tel)] = "MENU_PX"
        elif txt_up == "2": resp = "📅 *FECHAS 2026:*\n🚀 C1: 01 Mayo\n🔥 C2: 14 Mayo\n👑 MJ: 17 Abril"

    else: # PROTOCOLO NUEVOS
        if estado == "INICIO":
            resp = "🌟 *Bienvenido a Crear Poder Sin Límites*\n\n1️⃣ Ya he llevado entrenamientos\n2️⃣ Soy nuevo y quiero info"
            sesiones[str(tel)] = "PERFILAMIENTO"

    if txt_up == "4":
        resp = f"🙏 {p['nombre']}, he avisado a tu coordinadora. Te atenderán personalmente."
        enviar_wa(p["staff_tel"] or Config.STAFF["jmarin"]["tel"], f"🚨 *APOYO:* {id_h} solicita atención.")
        sesiones[str(tel)] = "DERIVADO"

    if resp:
        enviar_wa(tel, resp)
        registrar_log(tel, "BOT", resp, "out")
    
    with open(Config.SESSIONS_PATH, "w") as f: json.dump(sesiones, f)

# --- 5. RUTAS DE INTERFAZ ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    data = request.get_json()
    try:
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        threading.Thread(target=flujo_principal, args=(msg["from"], msg["text"]["body"], "Aliado")).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial():
    if os.path.exists(Config.HISTORIAL_PATH):
        with open(Config.HISTORIAL_PATH, "r") as f: return jsonify(json.load(f)), 200
    return jsonify([]), 200

@app.route("/chat")
def chat_panel():
    # Buscamos el archivo en varias rutas para evitar el 404
    for nombre in ["panel_chat.html", "index.html", "templates/panel_chat.html"]:
        ruta = os.path.join(BASE_DIR, nombre)
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f: return f.read()
    return f"❌ ERROR: No se encontró el archivo HTML en {BASE_DIR}. Verifica el nombre en GitHub.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
