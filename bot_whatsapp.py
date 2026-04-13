"""
Bot WhatsApp — Creación Cuántica E.I.R.L.
✅ V105: EVOLUCIÓN TOTAL + CONEXIÓN A GOOGLE SHEETS
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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    TOKEN = os.environ.get("WA_TOKEN", "")
    PHONE_ID = os.environ.get("WA_PHONE_ID", "")
    VERIFY_TOKEN = "cpsl2026"
    CSV_BD_PATH = os.path.join(DATA_DIR, "base_datos.csv")
    HISTORIAL_PATH = os.path.join(DATA_DIR, "historial_chat.json")
    ASIGNACIONES_PATH = os.path.join(DATA_DIR, "asignaciones.json")
    SESSIONS_PATH = os.path.join(DATA_DIR, "sesiones.json")
    
    # 🌟 AQUÍ PEGARÁS TU ENLACE DE MAKE.COM PARA GOOGLE SHEETS
    URL_SHEETS = os.environ.get("URL_MAKE", "PEGA_AQUI_TU_WEBHOOK_DE_MAKE")
    
    STAFF = {
        "Diana": {"tel": "51912379744"},
        "Joyce": {"tel": "51933599903"},
        "Zuley": {"tel": "51933599864"}
    }

def get_csv_bd_path():
    for path in [".", DATA_DIR]:
        archivos = [f for f in os.listdir(path) if f.startswith("campana_") and f.endswith(".csv")]
        if archivos:
            archivos.sort(key=lambda x: os.path.getmtime(os.path.join(path, x)), reverse=True)
            return os.path.join(path, archivos[0])
    return "base_datos.csv"
Config.CSV_BD_PATH = get_csv_bd_path()

# --- 2. MOTORES DE MEMORIA Y ESTADO ---
def gestionar_json(ruta, accion, data=None):
    try:
        if accion == "leer":
            if os.path.exists(ruta):
                with open(ruta, "r", encoding="utf-8") as f: return json.load(f)
            return {}
        elif accion == "guardar":
            with FileLock(ruta + ".lock", timeout=5):
                with open(ruta, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e: logger.error(f"Error JSON en {ruta}: {e}")
    return {}

def obtener_o_asignar_staff(tel_cliente):
    memoria = gestionar_json(Config.ASIGNACIONES_PATH, "leer")
    tel_str = str(tel_cliente)
    if tel_str in memoria:
        asig = memoria[tel_str]
        return asig.get("nombre", asig) if isinstance(asig, dict) else asig
    conteo = {nombre: 0 for nombre in Config.STAFF.keys()}
    for asig in memoria.values():
        nombre_asig = asig.get("nombre", asig) if isinstance(asig, dict) else asig
        if nombre_asig in conteo: conteo[nombre_asig] += 1
    nombre_elegida = min(conteo, key=conteo.get)
    memoria[tel_str] = nombre_elegida
    gestionar_json(Config.ASIGNACIONES_PATH, "guardar", memoria)
    return nombre_elegida

def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "NUEVO", "nombre": "Aliado", "enrolados": []}
    if os.path.exists(Config.CSV_BD_PATH):
        try:
            with open(Config.CSV_BD_PATH, 'r', encoding='utf-8-sig') as f:
                for row in csv.DictReader(f):
                    tel_px = str(row.get('TELÉFONO PX', row.get('Teléfono', '')))[-9:]
                    tel_imo = str(row.get('TEL. IMO', row.get('Tel. IMO', '')))[-9:]
                    nombre_pref = row.get('PREF.', row.get('Nombre', 'Aliado')).strip()
                    nombre_full = f"{row.get('APELLIDO', '')} {row.get('NOMBRE', '')}".strip()
                    if tel_px == tel_norm: perfil["nombre"], perfil["rol"] = nombre_pref, "PROSPECTO"
                    if tel_imo == tel_norm:
                        perfil["rol"] = "IMO"
                        perfil["nombre"] = row.get('NOMBRE IMO', 'Líder').split()[0].title()
                        if nombre_full: perfil["enrolados"].append(f"• {nombre_full}")
        except: pass
    return perfil

# --- 3. GOOGLE SHEETS & HISTORIAL ---
def enviar_a_sheets(telefono, nombre, rol, mensaje, estado):
    if "PEGA_AQUI" in Config.URL_SHEETS: return # Si no hay webhook, no hace nada
    datos = {
        "fecha": datetime.now(TZ_LIMA).strftime("%d/%m/%Y %H:%M:%S"),
        "telefono": str(telefono),
        "nombre": nombre,
        "rol": rol,
        "mensaje": mensaje,
        "coordinadora": obtener_o_asignar_staff(telefono),
        "estado_bot": estado
    }
    try: req_lib.post(Config.URL_SHEETS, json=datos, timeout=3)
    except: pass

def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=5):
            h = []
            if os.path.exists(Config.HISTORIAL_PATH):
                with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: h = json.load(f)
            h.append({"telefono": str(telefono), "nombre": nombre, "texto": texto, "tipo": tipo, "hora": datetime.now(TZ_LIMA).strftime("%d/%m %H:%M")})
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h[-2000:], f, ensure_ascii=False)
    except: pass

def enviar_wa(tel, texto, log_name="BOT"):
    url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    try:
        req_lib.post(url, json=payload, headers={"Authorization": f"Bearer {Config.TOKEN}"})
        append_historial(tel, log_name, texto, "out")
    except: pass

# --- 4. CEREBRO DEL BOT (V104 INTACTO) ---
def flujo_principal(tel, texto, nombre_wa):
    txt_up = str(texto).strip().upper()
    perfil = obtener_perfil_crm(tel)
    nombre = perfil["nombre"] if perfil["nombre"] != "Aliado" else nombre_wa
    rol = perfil["rol"]
    
    append_historial(tel, nombre, texto, "in")
    sesiones = gestionar_json(Config.SESSIONS_PATH, "leer")
    estado = sesiones.get(str(tel), "INICIO")
    
    # DISPARO A GOOGLE SHEETS
    threading.Thread(target=enviar_a_sheets, args=(tel, nombre, rol, texto, estado)).start()
    
    if txt_up in ["MENU", "MENÚ", "0", "SALIR", "VOLVER"]: estado = "INICIO"
        
    # MODO SILENCIO
    if estado == "DERIVADO":
        coord_name = obtener_o_asignar_staff(tel)
        tel_coord = Config.STAFF[coord_name]["tel"]
        enviar_wa(tel_coord, f"💬 *Mensaje de {nombre} (wa.me/{tel}):*\n{texto}", "ALERTA_STAFF")
        return 

    respuesta = ""
    derivar = False

    if estado == "INICIO":
        if rol == "IMO":
            respuesta = f"👑 *Portal de Graduados IMO — {nombre}*\n\n1️⃣ Ver TODOS mis enrolados\n2️⃣ Ver PENDIENTES de C1\n3️⃣ Próximas fechas\n4️⃣ Hablar con Coordinación\n0️⃣ Salir"
            estado = "MENU_IMO"
        elif rol == "PROSPECTO":
            respuesta = f"🌟 *Hola {nombre}*\n¡Bienvenido a CPSL Perú!\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Ver fechas 2026\n3️⃣ Inversión y Pagos\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar"
            estado = "MENU_PX"
        else:
            respuesta = f"🌟 *Bienvenido a Crear Poder Sin Límites Perú*\nCanal Corporativo Oficial. Responde con el número de tu elección:\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Inversión y Métodos de Pago\n3️⃣ Fechas Disponibles\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar"
            estado = "MENU_NUEVO"

    elif estado == "MENU_IMO":
        if txt_up == "1" or txt_up == "2":
            lista = perfil["enrolados"]
            respuesta = "*Tus prospectos:*\n" + ("\n".join(lista) if lista else "Aún no tienes registros.") + "\n\n9️⃣ Menú Principal"
        elif txt_up == "3": respuesta = "📅 *FECHAS 2026*\n🚀 C1: Vie 01 Mayo\n🔥 C2: Jue 14 Mayo\n👑 MJ: Vie 17 Abril\n\n9️⃣ Volver"
        elif txt_up == "4": derivar = True
        elif txt_up == "9": estado = "INICIO"; respuesta = "Escribe *MENU* para ver tus opciones."
        else: respuesta = "Opción no reconocida. Escribe *0* para menú principal."

    elif estado in ["MENU_PX", "MENU_NUEVO"]:
        if txt_up == "1":
            respuesta = "📘 *Crear Poder Sin Límites*\nSelecciona el nivel que estás listo para explorar:\n\n1️⃣ C1 (Capítulo Uno) - Descubrimiento\n2️⃣ C2 (Capítulo Dos) - La Experiencia\n3️⃣ MJ (Maestría del Juego)\n9️⃣ Regresar"
            estado = "MENU_NIVELES"
        elif txt_up == "2" and estado == "MENU_PX": respuesta = "📅 *FECHAS 2026*\n🚀 C1: Vie 01 Mayo\n🔥 C2: Jue 14 Mayo\n👑 MJ: Vie 17 Abril\n\n9️⃣ Volver"
        elif txt_up == "2" and estado == "MENU_NUEVO": respuesta = "💳 *Opciones de Inversión:*\n- BCP Soles: 193-XXXX-XXXX\n- Yape/Plin: 908652308\n\nEnvía la captura por este medio.\n\n9️⃣ Volver"
        elif txt_up == "3" and estado == "MENU_PX": respuesta = "💳 *Opciones de Inversión:*\n- BCP Soles: 193-XXXX-XXXX\n- Yape/Plin: 908652308\n\nEnvía la captura por este medio.\n\n9️⃣ Volver"
        elif txt_up == "3" and estado == "MENU_NUEVO": respuesta = "📅 *FECHAS 2026*\n🚀 C1: Vie 01 Mayo\n🔥 C2: Jue 14 Mayo\n👑 MJ: Vie 17 Abril\n\n9️⃣ Volver"
        elif txt_up == "4": derivar = True
        elif txt_up == "9": estado = "INICIO"; respuesta = "Escribe *MENU* para ver tus opciones."
        else: respuesta = "Opción no reconocida. Escribe *0* para menú principal."
        
    elif estado == "MENU_NIVELES":
        if txt_up == "1": respuesta = "🚀 *C1 (Capítulo Uno) - El Descubrimiento*\nUn entrenamiento vivencial de 3 días diseñado para romper paradigmas.\n\n4️⃣ Hablar con Coordinación para registro\n9️⃣ Regresar"
        elif txt_up == "2": respuesta = "🔥 *C2 (Capítulo Dos) - La Experiencia*\n4 días de inmersión total para estirar tus límites.\n\n4️⃣ Hablar con Coordinación\n9️⃣ Regresar"
        elif txt_up == "3": respuesta = "👑 *MJ (Maestría del Juego)*\n100 días de práctica llevándolo a tu vida real.\n\n4️⃣ Hablar con Coordinación\n9️⃣ Regresar"
        elif txt_up == "4": derivar = True
        elif txt_up == "9": estado = "INICIO"; respuesta = "Escribe *MENU* para volver."
        else: respuesta = "Opción no reconocida. Escribe *0* para menú principal."

    if derivar or "APOYO" in txt_up or "HUMANO" in txt_up:
        coord_name = obtener_o_asignar_staff(tel)
        tel_coord = Config.STAFF[coord_name]["tel"]
        respuesta = f"🙏 Derivando...\n\n¡Hola {nombre}! Soy {coord_name}, tu coordinadora asignada de Crear Poder Sin Límites. He recibido tu solicitud y desde este momento te atiendo yo personalmente por aquí. ¿En qué te ayudo?"
        estado = "DERIVADO" 
        enviar_wa(tel_coord, f"🚨 *NUEVA ASIGNACIÓN:* {nombre} (wa.me/{tel}) requiere apoyo. Perfil: {rol}.", "ALERTA_STAFF")

    if respuesta:
        sesiones[str(tel)] = estado
        gestionar_json(Config.SESSIONS_PATH, "guardar", sesiones)
        enviar_wa(tel, respuesta)

# --- 5. RUTAS WEB ---
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    try:
        data = request.get_json()
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        try: nombre = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        except: nombre = "Aliado"
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
        html_path = os.path.join(BASE_DIR, "panel_chat.html")
        with open(html_path, encoding="utf-8") as f: return f.read()
    except: return "Panel no encontrado.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
