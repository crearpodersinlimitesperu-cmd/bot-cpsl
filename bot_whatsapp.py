"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V94: THE IMO AUTHORITY (Portal IMO con Segmentación de Pendientes)
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
    BACKUP_CSV          = os.path.join(DATA_DIR, "backup_absoluto_mensajes.csv")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# 2. GESTORES DE DATOS
# ══════════════════════════════════════════════════════════════
def get_historial():
    try:
        if os.path.exists(Config.HISTORIAL_PATH):
            with open(Config.HISTORIAL_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: pass
    return []

def append_historial(telefono, nombre, texto, tipo):
    try:
        with FileLock(Config.HISTORIAL_PATH + ".lock", timeout=Config.LOCK_TIMEOUT):
            h = get_historial()
            h.append({"telefono": str(telefono), "nombre": nombre or "Desconocido", "texto": texto, "tipo": tipo, "hora": ahora_lima().strftime("%d/%m %H:%M")})
            if len(h) > 3000: h = h[-3000:]
            with open(Config.HISTORIAL_PATH, "w", encoding="utf-8") as f: json.dump(h, f, ensure_ascii=False, indent=2)
    except: pass

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

# ══════════════════════════════════════════════════════════════
# 3. CRM IMO E INTELIGENCIA DE DATOS
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
                    nombre_px = row.get('Nombre','').strip() + " " + row.get('Apellido','').strip()
                    asistio_c1 = row.get('C1','').strip().upper() == 'SI'
                    
                    # ¿Es el participante?
                    if tel_px == tel_norm:
                        perfil["nombre"] = row.get('Nombre','').split()[0].title()
                        perfil["rol"] = "PX_REZAGADO_C1" if not asistio_c1 else "PX_SENTADO"
                    
                    # ¿Es el IMO de alguien?
                    if tel_imo == tel_norm:
                        perfil["rol"] = "IMO"
                        status = "✅ Sentado" if asistio_c1 else "⏳ Pendiente"
                        linea = f"• {nombre_px.title()} ({status})"
                        perfil["enrolados_todos"].append(linea)
                        if not asistio_c1:
                            perfil["enrolados_pendientes"].append(f"• {nombre_px.title()} (Falta C1)")
        except Exception as e:
            logger.error(f"Error leyendo CSV: {e}")
            
    return perfil

def get_fecha_activa(tipo):
    evs = {"C1": "Viernes 01 de Mayo (E27)", "C2": "Jueves 14 de Mayo (E27)", "MJ": "Viernes 17 de Abril (E26)"}
    return evs.get(tipo, "TBC")

# ══════════════════════════════════════════════════════════════
# 4. MOTOR DE COMUNICACIÓN
# ══════════════════════════════════════════════════════════════
def enviar_mensaje(tel, texto, nombre_log="BOT"):
    if str(tel).startswith("SIM_"):
        append_historial(tel, nombre_log, texto, "out")
        return True
    try:
        r = req_lib.post(f"https://graph.facebook.com/v19.0/{Config.PHONE_ID}/messages", 
                         json={"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}, 
                         headers={"Authorization": f"Bearer {Config.TOKEN}"}, timeout=10)
        if r.status_code == 200:
            append_historial(tel, nombre_log, texto, "out")
            return True
        else: logger.error(f"Error API WA: {r.text}")
    except Exception as e:
        logger.error(f"Error enviando: {e}")
        if tel != GERENTE_TEL: enviar_mensaje(GERENTE_TEL, f"🚨 ALERTA: Error enviando a {tel}")
    return False

def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel)
        txt_up = str(texto).strip().upper()
        
        # INICIO / MENU
        if not sesion or txt_up in {"0","MENU","MENÚ","INICIO"}:
            perfil = obtener_perfil_crm(tel)
            sesion = {"perfil": perfil}
            
            if perfil["rol"] == "IMO":
                saludo = (f"🌟 *Portal del Líder IMO — {perfil.get('nombre','Líder')}*\n\n"
                          "¿Qué información elijes consultar hoy?\n\n"
                          "1️⃣ Ver *TODOS* mis enrolados (Lista completa)\n"
                          "2️⃣ Ver enrolados *PENDIENTES* de C1\n"
                          "3️⃣ Consultar próximas fechas\n"
                          "4️⃣ Hablar con Coordinación IMO\n"
                          "0️⃣ Salir")
            else:
                saludo = (f"🌟 *Hola {perfil.get('nombre','Líder')}*\n"
                          "¡Bienvenido a CPSL Perú!\n\n"
                          "1️⃣ Información Entrenamientos\n"
                          "2️⃣ Fechas 2026\n"
                          "3️⃣ Inversión y Pagos\n"
                          "4️⃣ Hablar con Coordinación\n"
                          "0️⃣ Finalizar")
            
            set_sesion(tel, sesion)
            enviar_mensaje(tel, saludo, f"({perfil['rol']}) {perfil['nombre'] or 'User'}")
            return

        perfil = sesion.get("perfil", {})
        
        # LÓGICA IMO
        if perfil["rol"] == "IMO":
            if txt_up == "1":
                lista = perfil.get("enrolados_todos", [])
                msg = "📋 *LISTA COMPLETA DE ENROLADOS*\n\n" + ("\n".join(lista) if lista else "No tienes invitados registrados.")
                enviar_mensaje(tel, msg + "\n\n_Escribe 0 para el menú principal_")
            elif txt_up == "2":
                lista = perfil.get("enrolados_pendientes", [])
                msg = "⏳ *ENROLADOS PENDIENTES DE C1*\n(Aún no se han sentado)\n\n" + ("\n".join(lista) if lista else "🎉 ¡Todos tus invitados ya se sentaron en C1!")
                enviar_mensaje(tel, msg + "\n\n_Escribe 0 para el menú principal_")
            elif txt_up == "3":
                msg = f"📅 *PRÓXIMAS FECHAS 2026*\n\n🚀 C1: {get_fecha_activa('C1')}\n🔥 C2: {get_fecha_activa('C2')}\n👑 MJ: {get_fecha_activa('MJ')}\n\n_Escribe 0 para volver_"
                enviar_mensaje(tel, msg)
            elif txt_up == "4":
                enviar_mensaje(tel, "✅ He generado un ticket para ti. Un coordinador de IMOs te escribirá pronto.")
                enviar_mensaje(GERENTE_TEL, f"🚨 TICKET IMO: wa.me/{tel} ({perfil.get('nombre')}) requiere soporte.")
            return

        # LÓGICA PROSPECTO
        if txt_up == "1":
            enviar_mensaje(tel, "🚀 *Capítulo 1:* Entrenamiento vivencial de 3 días para romper paradigmas.\n🔥 *Capítulo 2:* 4 días de inmersión total.\n👑 *MJ:* 100 días de práctica.\n\n_Escribe 0 para volver_")
        elif txt_up == "2":
            enviar_mensaje(tel, f"📅 *FECHAS:* C1: {get_fecha_activa('C1')}, C2: {get_fecha_activa('C2')}.\n\n_Escribe 0 para volver_")
        elif txt_up == "3":
            enviar_mensaje(tel, "💳 *Pagos:* BCP Soles 1934218307060 a nombre de Creación Cuántica E.I.R.L.\n\n_Escribe 0 para volver_")
        elif txt_up == "4":
            enviar_mensaje(tel, "🙏 Te estamos derivando con un coordinador. Danos unos minutos.")
            enviar_mensaje(GERENTE_TEL, f"🚨 TICKET PX: wa.me/{tel} solicita atención humana.")

    except Exception as e:
        logger.error(f"Error flujo: {e}")
        if tel != GERENTE_TEL: enviar_mensaje(GERENTE_TEL, f"🚨 ERROR CRÍTICO BOT en {tel}: {str(e)}")

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
        else:
            enviar_mensaje(msg["from"], "⚠️ Solo puedo procesar texto. Por favor escribe tu consulta. 🙏")
    except: pass
    return jsonify({"status":"ok"}), 200

@app.route("/api/historial")
def api_historial(): return jsonify(get_historial()), 200

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
