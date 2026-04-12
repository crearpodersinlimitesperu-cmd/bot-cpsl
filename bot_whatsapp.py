"""
Bot WhatsApp — Creación Cuántica E.I.R.L. / Crear Poder Sin Límites Perú
✅ V92: CONSOLIDACIÓN TOTAL (Fechas, IMOs, Escudo Humano y Alerta Gerencial)
"""

import os, re, json, time, csv, io, random, logging, threading, queue
from flask import Flask, request, jsonify, Response
from datetime import datetime, timedelta, timezone
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock, Timeout as FileLockTimeout

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("BotCrear")

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════
# 1. ZONA HORARIA Y DIRECTORIO PERSISTENTE
# ══════════════════════════════════════════════════════════════
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
GERENTE_TEL = "51912379744" # Número para alertas de error

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
    SESSIONS_SIM_PATH   = os.path.join(DATA_DIR, "sesiones_sim.json")   
    HISTORIAL_PATH      = os.path.join(DATA_DIR, "historial_chat.json")
    BACKUP_CSV          = os.path.join(DATA_DIR, "backup_absoluto_mensajes.csv")
    SHEET_ID            = os.environ.get("SHEET_ID", "")
    CREDS_JSON          = os.environ.get("GOOGLE_CREDENTIALS", "")
    LOCK_TIMEOUT        = 5   

# ══════════════════════════════════════════════════════════════
# 2. CALENDARIO DINÁMICO CPSL 2026 (RESTAURADO)
# ══════════════════════════════════════════════════════════════
def get_fecha_activa(tipo_evento):
    ahora = ahora_lima()
    eventos = {
        "C1": [
            {"dt": datetime(2026, 5, 1, 9, 0, tzinfo=TZ_LIMA), "txt": "Viernes 01 de Mayo a las 9:00 AM (Equipo 27)"},
            {"dt": datetime(2026, 6, 5, 9, 0, tzinfo=TZ_LIMA), "txt": "Viernes 05 de Junio a las 9:00 AM (Equipo 28)"}
        ],
        "C2": [
            {"dt": datetime(2026, 4, 9, 13, 0, tzinfo=TZ_LIMA), "txt": "Jueves 09 de Abril a las 1:00 PM (Equipo 26)"},
            {"dt": datetime(2026, 5, 14, 13, 0, tzinfo=TZ_LIMA), "txt": "Jueves 14 de Mayo a las 1:00 PM (Equipo 27)"}
        ],
        "MJ": [
            {"dt": datetime(2026, 4, 17, 17, 0, tzinfo=TZ_LIMA), "txt": "Viernes 17 de Abril a las 5:00 PM (Inicia Equipo 26)"}
        ]
    }
    for ev in eventos.get(tipo_evento, []):
        if ahora <= ev["dt"]: return ev["txt"]
    return "Próximas fechas por confirmar por Coordinación."

# ══════════════════════════════════════════════════════════════
# 3. CRM E IDENTIFICACIÓN DE IMO / GRADUADO
# ══════════════════════════════════════════════════════════════
_graduados_phones = set()

def cargar_memoria_graduados():
    global _graduados_phones
    _graduados_phones.clear()
    try:
        path = os.path.join(DATA_DIR, "GRADUADOS.csv") if os.path.exists(os.path.join(DATA_DIR, "GRADUADOS.csv")) else "GRADUADOS.csv"
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Aquí el bot podría buscar el tel si estuviera en el CSV, 
                    # pero por ahora usaremos la lógica de coincidencia de nombres en obtener_perfil
                    pass
    except: pass

def obtener_perfil_crm(telefono):
    tel_norm = str(telefono)[-9:]
    perfil = {"rol": "PROSPECTO", "nombre": None, "enrolados": []}
    
    if os.path.exists(Config.CSV_BD_PATH):
        with open(Config.CSV_BD_PATH, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 1. Identificar si es el participante mismo
                if str(row.get('Teléfono',''))[-9:] == tel_norm:
                    perfil["nombre"] = row.get('Nombre','').split()[0].title()
                    c1, c2 = row.get('C1','').upper(), row.get('C2','').upper()
                    if c1 == 'SI' and c2 == 'SI': perfil["rol"] = "PX_UPSELL_MJ"
                    elif c1 == 'SI': perfil["rol"] = "PX_UPSELL_C2"
                    else: perfil["rol"] = "PX_REZAGADO_C1"
                
                # 2. Cargar sus enrolados (Si este teléfono es el de su IMO)
                if str(row.get('Tel. IMO',''))[-9:] == tel_norm:
                    perfil["rol"] = "IMO"
                    status = "Sentado ✅" if row.get('C1','') == 'SI' else "Pendiente ⏳"
                    perfil["enrolados"].append(f"• {row.get('Nombre','')} ({status})")
    
    return perfil

# ══════════════════════════════════════════════════════════════
# 4. MOTOR DE MENÚS (CONTENEDOR DE INFORMACIÓN)
# ══════════════════════════════════════════════════════════════
INFOS = {
    "c1": "🚀 *Capítulo 1: El Descubrimiento*\nUn entrenamiento vivencial de 3 días para observar tus mecanismos de defensa automáticos y romper los límites que te impiden avanzar. \n📍 Hotel José Antonio Deluxe, Miraflores.",
    "c2": "🔥 *Capítulo 2: La Experiencia*\n4 días de inmersión total para dar un salto cuántico. Diseñado para atravesar tus barreras y rediseñar tu realidad desde la responsabilidad absoluta.",
    "mj": "👑 *Maestría del Juego: La Práctica*\nUn programa de 100 días donde el liderazgo se lleva a la cancha real (familia, finanzas y metas). Forjarás la disciplina para resultados sostenibles."
}

MENU_STR = {
    "main_prospecto": {
        "text": "🌟 *Bienvenido a Crear Poder Sin Límites*\nPara brindarte la mejor info, elige una opción:\n\n1️⃣ Información de los Entrenamientos\n2️⃣ Ver fechas y horarios\n3️⃣ Inversión y Métodos de Pago\n4️⃣ Hablar con Coordinación\n0️⃣ Finalizar",
        "options": {"1":"menu_info","2":"menu_fechas","3":"menu_pagos","4":"pre_humano_gral","0":"salir"}
    },
    "main_px_rezagado_c1": {
        "text": "🌟 *Hola {nombre}!*\nDetectamos que tienes pendiente tu *Capítulo 1*.\n\n1️⃣ Confirmar mi asistencia para la próxima fecha\n2️⃣ Información del entrenamiento (C1)\n3️⃣ Hablar con Coordinación\n0️⃣ Salir",
        "options": {"1":"pre_humano_asistencia","2":"menu_info_c1","3":"pre_humano_gral","0":"salir"}
    },
    "main_imo": {
        "text": "🌟 *Hola Líder IMO {nombre}*\n\n1️⃣ Ver el estado de mis enrolados (C1)\n2️⃣ Consultar próximas fechas\n3️⃣ Hablar con Coordinación IMO\n0️⃣ Salir",
        "options": {"1":"ver_enrolados","2":"menu_fechas","3":"pre_humano_imo","0":"salir"}
    }
}

# ══════════════════════════════════════════════════════════════
# 5. LÓGICA DE ENVÍO Y ALERTA DE ERRORES
# ══════════════════════════════════════════════════════════════
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
            SessionManager.guardar_backup_absoluto(tel, nombre_log, texto, "OUT", "ENVIADO")
            return True
        else:
            # Notificar al Gerente si Meta falla
            if tel != GERENTE_TEL:
                enviar_mensaje(GERENTE_TEL, f"⚠️ ERROR API META: {r.text}")
    except Exception as e:
        if tel != GERENTE_TEL: enviar_mensaje(GERENTE_TEL, f"⚠️ ERROR CRÍTICO BOT: {str(e)}")
    return False

# ══════════════════════════════════════════════════════════════
# 6. FLUJO PRINCIPAL (EL CEREBRO)
# ══════════════════════════════════════════════════════════════
def flujo_principal(tel, texto):
    try:
        sesion = get_sesion(tel) or {}
        txt_up = str(texto).strip().upper()
        
        # Reset o Inicio
        if "perfil" not in sesion or txt_up in {"0","MENU","INICIO"}:
            perfil = obtener_perfil_crm(tel)
            sesion["perfil"] = perfil
            rol = perfil.get("rol", "PROSPECTO")
            # Elegir menú según rol
            m_key = "main_imo" if rol == "IMO" else ("main_px_rezagado_c1" if "PX_REZ" in rol else "main_prospecto")
            sesion["menu_state"] = m_key
            set_sesion(tel, sesion)
            
            saludo = MENU_STR[m_key]["text"].format(nombre=perfil.get("nombre","Líder"))
            enviar_mensaje(tel, saludo, f"({rol}) {perfil.get('nombre','User')}")
            return

        perfil = sesion.get("perfil", {})
        estado = sesion.get("menu_state", "main_prospecto")
        
        # Lógica de Opciones
        if txt_up == "1":
            if estado == "main_prospecto":
                msg = "📘 *Entrenamientos CPSL*\n1️⃣ C1: El Descubrimiento\n2️⃣ C2: La Experiencia\n3️⃣ MJ: La Práctica\n9️⃣ Volver"
                sesion["menu_state"] = "info_gral"
                set_sesion(tel, sesion)
                enviar_mensaje(tel, msg)
            elif estado == "info_gral": enviar_mensaje(tel, INFOS["c1"])
            elif estado == "main_imo":
                lista = perfil.get("enrolados", [])
                msg = "*Estatus de tus invitados:*\n\n" + ("\n".join(lista) if lista else "No tienes invitados registrados aún.")
                enviar_mensaje(tel, msg + "\n\n_Presiona 0 para volver_")
            elif estado == "main_px_rezagado_c1":
                enviar_mensaje(tel, "🚀 Excelente elección. Te derivamos con un coordinador para validar tu cupo de C1.")
                notificar_coordinacion(tel, perfil.get("nombre"), "Desea confirmar asistencia C1")

        elif txt_up == "2":
            if estado == "main_prospecto" or estado == "main_imo":
                msg = f"📅 *Próximas Fechas 2026*\n\n🚀 *C1:* {get_fecha_activa('C1')}\n🔥 *C2:* {get_fecha_activa('C2')}\n👑 *MJ:* {get_fecha_activa('MJ')}\n\n_Escribe 0 para volver._"
                enviar_mensaje(tel, msg)
            elif estado == "info_gral": enviar_mensaje(tel, INFOS["c2"])

        elif txt_up == "3":
            if estado == "main_prospecto":
                msg = "💳 *Métodos de Pago*\nBCP Soles: 1934218307060\nA nombre de: Creación Cuántica E.I.R.L.\n\n_Envía el voucher por este medio para validarlo._"
                enviar_mensaje(tel, msg)
            elif estado == "info_gral": enviar_mensaje(tel, INFOS["mj"])

        # Default fallback
        else:
            if not txt_up.isnumeric():
                enviar_mensaje(tel, "Para darte una atención personalizada, describe brevemente tu duda y un coordinador te atenderá.")
                notificar_coordinacion(tel, perfil.get("nombre"), texto)

    except Exception as e:
        logger.error(f"Error flujo {tel}: {e}")
        enviar_mensaje(GERENTE_TEL, f"🚨 ERROR PROCESANDO {tel}: {str(e)}")

def notificar_coordinacion(tel, nom, motivo):
    msg = f"🚨 *NUEVO TICKET*\n*Usuario:* {nom}\n*Tel:* wa.me/{tel}\n*Motivo:* {motivo}"
    enviar_mensaje("51912379744", msg, "SISTEMA")

# ══════════════════════════════════════════════════════════════
# ENDPOINTS (V92)
# ══════════════════════════════════════════════════════════════
@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == Config.VERIFY_TOKEN: return request.args.get("hub.challenge"), 200
    return "Error", 403

@app.route("/webhook", methods=["POST"])
def recv():
    data = request.get_json(silent=True)
    try:
        val = data["entry"][0]["changes"][0]["value"]
        msg = val["messages"][0]
        tel, tipo = msg["from"], msg.get("type")
        
        if tipo == "text":
            threading.Thread(target=flujo_principal, args=(tel, msg["text"]["body"])).start()
        else:
            # ESCUDO ANTI-MULTIMEDIA
            enviar_mensaje(tel, "⚠️ Por ahora solo puedo procesar mensajes de texto. Por favor escribe tu consulta. 🙏")
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
