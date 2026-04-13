"""
Bot WhatsApp — Creación Cuántica E.I.R.L.
✅ V108.1: ESTRUCTURA SEGMENTADA (IMOs, PX y Nuevos) + ASIGNACIÓN POR STAFF
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
    
    # DIRECTORIO OFICIAL DE STAFF (Actualizado)
    STAFF = {
        "jmarin": {"nombre": "Joyce Marín", "tel": "51933599903", "rol": "C1/C2"},
        "lpasquel": {"nombre": "Leyla Pasquel", "tel": "51919502385", "rol": "MJ"},
        "zurteaga": {"nombre": "Zuley Urteaga", "tel": "51933599864", "rol": "C1/C2"},
        "dmoscoso": {"nombre": "Diana Moscoso", "tel": "51912379744", "rol": "C1/C2"},
        "lvalencia": {"nombre": "Linid Valencia", "tel": "51912379686", "rol": "MJ"}
    }

# --- 2. MOTOR DE IDENTIFICACIÓN Y SEGMENTACIÓN ---
def obtener_perfil_detallado(tel):
    tel_norm = str(tel)[-9:]
    res = {
        "tipo": "NUEVO", 
        "id_full": "Aliado por Identificar", 
        "nombre": "Aliado", 
        "dni": "S/D", 
        "staff_tel": None, 
        "staff_nom": "Pendiente",
        "gente_pendiente": []
    }
    
    if os.path.exists(Config.CSV_ASIG_PATH):
        try:
            with open(Config.CSV_ASIG_PATH, 'r', encoding='utf-8-sig') as f:
                filas = list(csv.DictReader(f))
                # 1. Buscar si el que escribe es un PX o un Staff
                for row in filas:
                    if str(row.get('TelefonoMovil', ''))[-9:] == tel_norm:
                        dni = row.get('Identificación', 'S/D')
                        n = row.get('NombreCompleto', '').strip()
                        a = row.get('ApellidoCompleto', '').strip()
                        u = row.get('Usuario Registro', '').lower()
                        
                        res["tipo"] = "PX" # Prospecto Identificado
                        res["id_full"] = f"{dni} - {n} {a}"
                        res["nombre"] = n.split()[0].title()
                        res["dni"] = dni
                        if u in Config.STAFF:
                            res["staff_tel"] = Config.STAFF[u]["tel"]
                            res["staff_nom"] = Config.STAFF[u]["nombre"]
                
                # 2. Buscar si el que escribe es un IMO (Graduado) y su gente
                for row in filas:
                    if str(row.get('IdentificacionIMO', ''))[-9:] == tel_norm:
                        res["tipo"] = "IMO"
                        n_px = row.get('NombreCompleto', '')
                        a_px = row.get('ApellidoCompleto', '')
                        res["gente_pendiente"].append(f"• {n_px} {a_px}")
        except: pass
    return res

# --- 3. FUNCIONES DE COMUNICACIÓN ---
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

# --- 4. FLUJO DE TRABAJO (LA TORRE DE CONTROL) ---
def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    perfil = obtener_perfil_detallado(tel)
    
    # Identidad Impecable para Historial y Sheets
    id_historial = perfil["id_full"] if perfil["tipo"] != "NUEVO" else f"NUEVO: {nombre_wa}"
    registrar_log(tel, id_historial, texto, "in")
    
    # Sincronización Google Sheets
    threading.Thread(target=lambda: req_lib.post(Config.URL_SHEETS, json={
        "fecha": datetime.now(TZ_LIMA).strftime("%d/%m/%Y %H:%M:%S"),
        "dni": perfil["dni"],
        "identidad": id_historial,
        "tipo": perfil["tipo"],
        "mensaje": texto,
        "coordinadora": perfil["staff_nom"]
    })).start()

    # Manejo de Sesión
    if os.path.exists(Config.SESSIONS_PATH):
        with open(Config.SESSIONS_PATH, "r") as f: sesiones = json.load(f)
    else: sesiones = {}
    
    estado = sesiones.get(str(tel), "INICIO")
    if txt_up in ["MENU", "0"]: estado = "INICIO"

    # MODO SILENCIO (Cuidado del Staff)
    if estado == "DERIVADO":
        target = perfil["staff_tel"] or Config.STAFF["jmarin"]["tel"]
        enviar_wa(target, f"💬 *Mensaje de {id_historial}:*\n{texto}")
        return

    # --- SEGMENTACIÓN DE RESPUESTAS ---
    resp = ""
    
    # A. FLUJO PARA GRADUADOS (IMOs)
    if perfil["tipo"] == "IMO":
        if estado == "INICIO":
            resp = f"👑 *Portal Líder IMO — {perfil['nombre']}*\n\n1️⃣ Ver mi gente pendiente de C1\n2️⃣ Solicitar ser ALIADO en próximo C1\n3️⃣ Fechas Próximas\n4️⃣ Hablar con mi Coordinadora\n0️⃣ Salir"
            sesiones[str(tel)] = "MENU_IMO"
        elif txt_up == "1":
            lista = "\n".join(perfil["gente_pendiente"][:10])
            resp = f"👥 *Tu gente pendiente:*\n{lista}\n\n9️⃣ Volver"
        elif txt_up == "2":
            resp = "✅ ¡Excelente decisión, Líder! He notificado a tu coordinadora que deseas ser ALIADO. Se pondrán en contacto contigo."
            target = perfil["staff_tel"] or Config.STAFF["jmarin"]["tel"]
            enviar_wa(target, f"⭐ *SOLICITUD DE ALIADO:* {id_historial} quiere ser aliado en el próximo C1.")

    # B. FLUJO PARA PROSPECTOS (PX)
    elif perfil["tipo"] == "PX":
        if estado == "INICIO":
            resp = f"🌟 *Hola {perfil['nombre']}*\n¡Estamos listos para tu siguiente paso!\n\n1️⃣ Información C1/C2\n2️⃣ Fechas Disponibles\n3️⃣ Inversión y Pagos\n4️⃣ Hablar con Coordinación\n0️⃣ Salir"
            sesiones[str(tel)] = "MENU_PX"
        elif txt_up == "2":
            resp = "📅 *FECHAS ACTIVAS 2026:*\n🚀 C1: 01 de Mayo\n🔥 C2: 14 de Mayo\n👑 MJ: 17 de Abril\n\nResponde con tu fecha de interés o *4* para asistencia."

    # C. PROTOCOLO PARA NUEVOS (Perfilamiento)
    else:
        if estado == "INICIO":
            resp = "🌟 *Bienvenido a Crear Poder Sin Límites*\nPara brindarte una atención premium, por favor confírmanos:\n\n1️⃣ Ya he llevado entrenamientos antes (Cambio de número)\n2️⃣ Soy nuevo y quiero información\n3️⃣ Soy graduado IMO"
            sesiones[str(tel)] = "PERFILAMIENTO"
        elif txt_up == "1":
            resp = "Entendido. Por favor, indícanos tu *DNI* para recuperar tu perfil y asignarte a tu coordinadora."
            sesiones[str(tel)] = "ESPERANDO_DNI"

    # DERIVACIÓN Y CUIDADO DEL STAFF
    if txt_up == "4" or "AYUDA" in txt_up:
        target = perfil["staff_tel"] or random.choice([s["tel"] for s in Config.STAFF.values() if s["rol"] == "C1/C2"])
        resp = f"🙏 {perfil['nombre']}, he avisado a Coordinación. Te atenderán personalmente por aquí."
        enviar_wa(target, f"🚨 *SOLICITUD DE APOYO:* {id_historial} (wa.me/{tel}) requiere atención.")
        sesiones[str(tel)] = "DERIVADO"

    if resp:
        enviar_wa(tel, resp)
        registrar_log(tel, "BOT", resp, "out")

    with open(Config.SESSIONS_PATH, "w") as f: json.dump(sesiones, f)

# --- 5. RUTAS WEB ---
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
