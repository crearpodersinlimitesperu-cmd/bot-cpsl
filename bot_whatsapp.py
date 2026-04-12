"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V93: THE FINAL STABILIZER (Fix get_historial NameError)
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
# 1. ZONA HORARIA Y DIRECTORIO PERSISTENTE
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
GERENTE_TEL = "51912379744" 

def ahora_lima(): return datetime.now(TZ_LIMA)
def ahora_lima_str(): return ahora_lima().strftime("%Y-%m-%d %H:%M:%S")

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
    BACKUP_CSV          = os.path.join(DATA_DIR, "backup_absoluto_mensajes.csv")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# 2. GESTOR DE PERSISTENCIA (FIX CRÍTICO)
# ══════════════════════════════════════════════════════════════
def get_historial():
    """Función restaurada para el panel de chat."""
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando historial: {e}")
    return []

def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            h = get_historial()
            h.append({
                "telefono": str(telefono),
                "nombre": nombre or "Desconocido",
                "texto": texto,
                "tipo": tipo,
                "hora": ahora_lima().strftime("%d/%m %H:%M")
            })
            if len(h) > 3000: h = h[-3000:]
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f:
                json.dump(h, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error guardando historial: {e}")

def set_sesion(tel, data):
    try:
        with FileLock(Config.SESSIONS_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            all_s = {}
            if os.path.exists(Config.SESSIONS_PATH):
                with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f: all_s = json.load(f)
            all_s[str(tel)] = data
            with open(Config.SESSIONS_PATH, "w", encoding="utf-8") as f:
                json.dump(all_s, f, ensure_ascii=False, indent=2)
    except: pass

def get_sesion(tel):
    try:
        if os.path.exists(Config.SESSIONS_PATH):
            with open(Config.SESSIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f).get(str(tel), {})
    except: pass
    return {}

# ══════════════════════════════════════════════════════════════
# 3. CALENDARIO Y CRM
# ══════════════════════════════════════════════════════════════
def get_fecha_activa(tipo):
    eventos = {
        "C1": "Viernes 01 de Mayo a las 9:00 AM (Equipo 27)",
        "C2": "Jueves 14 de Mayo a las 1:00 PM (Equipo 27)",
        "MJ": "Viernes 17 de Abril a las 5:00 PM (Inicia Equipo 26)"
    }
    return eventos.get(tipo, "Fechas por confirmar.")

def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "PROSPECTO", "nombre": None, "enrolados": []}
    path = Config.CSV_BD_PATH
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if str(row.get('Teléfono',''))[-9:] == tel_norm:
                    perfil["nombre"] = row.get('Nombre','').split()[0].title()
                    c1, c2 = row.get('C1','').upper(), row.get('C2','').upper()
                    perfil["rol"] = "PX_REZAGADO_C1" if c1 != 'SI' else ("PX_UPSELL_C2" if c2 != 'SI' else "PX_UPSELL_MJ")
                if str(row.get('Tel. IMO',''))[-9:] == tel_norm:
                    perfil["rol"] = "IMO"
                    perfil["enrolados"].append(f"• {row.get('Nombre','')} ({'Sentado ✅' if row.get('C1','')=='SI' else 'Pendiente ⏳'})")
    return perfil

# ══════════════════════════════════════════════════════════════
# 4. MOTOR DE MENÚS Y ENVÍO
# ══════════════════════════════════════════════════════════════
INFOS = {
    "c1": "🚀 *Capítulo 1: El Descubrimiento*\nEntrenamiento de 3 días para romper límites.\n📍 Hotel José Antonio Deluxe, Miraflores.",
    "c2": "🔥 *Capítulo 2: La Experiencia*\n4 días inmersivos para rediseñar tu realidad.",
    "mj": "👑 *Maestría del Juego: La Práctica*\n100 días de disciplina para resultados sostenibles."
}

def enviar_mensaje(tel, texto, nombre_log="BOT"):
    if str(tel).startswith("SIM_"):
        append_historial(tel, nombre_log, texto, "out")
        return True
    try:
        url = f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages"
        headers = {"Authorization": f"Bearer {Config.TOKEN}", "Content-Type": "application/json"}
        payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
        r = req_lib.post(url, json=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            append_historial(tel, nombre_log, texto, "out")
            return True
    except Exception as e:
        logger.error(f"Error WA: {e}")
    return False

def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel)
        txt_up = str(texto).strip().upper()
        
        if not sesion or txt_up in {"0","MENU","INICIO"}:
            perfil = obtener_perfil_crm(tel)
            sesion = {"perfil": perfil, "menu_state": "main_imo" if perfil["rol"]=="IMO" else "main_prospecto"}
            set_sesion(tel, sesion)
            saludo = f"🌟 *Hola {perfil.get('nombre','Líder')}*\n\n1️⃣ Información Entrenamientos\n2️⃣ Fechas 2026\n3️⃣ Pagos\n4️⃣ Coordinación\n0️⃣ Salir"
            if perfil["rol"] == "IMO":
                saludo = f"🌟 *Hola Líder IMO {perfil.get('nombre')}*\n\n1️⃣ Ver mis enrolados\n2️⃣ Próximas fechas\n3️⃣ Coordinación\n0️⃣ Salir"
            enviar_mensaje(tel, saludo, f"({perfil['rol']}) {perfil['nombre'] or 'User'}")
            return

        # Lógica simplificada de navegación
        if txt_up == "1":
            if sesion["menu_state"] == "main_imo":
                lista = sesion["perfil"].get("enrolados", [])
                msg = "*Tus enrolados:*\n" + ("\n".join(lista) if lista else "Sin invitados.")
                enviar_mensaje(tel, msg + "\n\n_Escribe 0 para volver_")
            else:
                enviar_mensaje(tel, INFOS["c1"] + "\n\n_Escribe 0 para el menú principal._")
        elif txt_up == "2":
            msg = f"📅 *Fechas*\n🚀 C1: {get_fecha_activa('C1')}\n🔥 C2: {get_fecha_activa('C2')}\n👑 MJ: {get_fecha_activa('MJ')}\n\n_0 para volver_"
            enviar_mensaje(tel, msg)
        elif txt_up == "3":
            enviar_mensaje(tel, "💳 *Pagos*\nBCP Soles: 1934218307060\nCreación Cuántica E.I.R.L.\n\n_0 para volver_")
        else:
            if not txt_up.isnumeric():
                enviar_mensaje(tel, "Derivado con coordinación. Te responderemos pronto. 🙏")
                enviar_mensaje(GERENTE_TEL, f"🚨 TICKET: wa.me/{tel}\nMotivo: {texto}")

    except Exception as e:
        logger.error(f"Error flujo: {e}")

# ══════════════════════════════════════════════════════════════
# 5. ENDPOINTS
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recv():
    try:
        data = request.get_json(silent=True)
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        if msg.get("type") == "text":
            threading.Thread(target=flujo_principal, args=(msg["from"], msg["text"]["body"])).start()
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial(): 
    return jsonify(get_historial()), 200

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
