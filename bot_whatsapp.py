"""
Bot WhatsApp V200 - Crear Poder Sin Límites Perú
✅ SQLite + Gemini + Panel + Sync Auto
✅ LISTO PARA COPIAR Y PEGAR EN RENDER
"""
import os, re, json, time, csv, logging, threading, sqlite3
from flask import Flask, request, jsonify
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock

# ── IMPORT GEMINI ──
try:
    from google import genai
    GEMINI_OK = True
except:
    GEMINI_OK = False

# ── CONFIGURACIÓN ──
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CPSL-Bot")

app = Flask(__name__)
TZ_LIMA = timezone(timedelta(hours=-5))
DATA_DIR = "/data" if os.path.exists("/data") else "."
DB_PATH = os.path.join(DATA_DIR, "cpsl_bot.db")
EXCEL_PATH = os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx")

# ── COORDINADORAS ──
COORDINADORAS = {
    "Diana": "51912379744",
    "Joyce": "51933599903", 
    "Zuley": "51933599864"
}

# ── INICIALIZAR DB AL CARGAR EL MÓDULO (funciona con Gunicorn) ──
def init_db():
    """Inicializa SQLite con todas las tablas"""
    try:
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else ".", exist_ok=True)
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                tel TEXT PRIMARY KEY, nombre TEXT, user_type TEXT DEFAULT 'prospecto',
                estado TEXT DEFAULT 'activo', coordinadora TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, last_interaction TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_tel TEXT, coord_nombre TEXT,
                coord_tel TEXT, estado TEXT DEFAULT 'activa',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, released_at TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_tel TEXT, direction TEXT,
                content TEXT, timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
            c.execute('''CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT,
                last_sync TIMESTAMP, records_synced INTEGER, errors TEXT)''')
            c.execute('CREATE INDEX IF NOT EXISTS idx_messages_tel ON messages(user_tel)')
            c.execute('CREATE INDEX IF NOT EXISTS idx_assignments_tel ON assignments(user_tel)')
            conn.commit()
        logger.info(f"✅ SQLite listo: {DB_PATH}")
    except Exception as e:
        logger.error(f"❌ Error DB: {e}")

# Ejecutar init_db AHORA (al cargar el módulo, funciona con Gunicorn)
init_db()

# ── HELPERS DE DB ──
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def migrate_from_json():
    """Migra datos históricos de JSON a SQLite (solo primera vez)"""
    asignaciones_file = os.path.join(DATA_DIR, "asignaciones.json")
    historial_file = os.path.join(DATA_DIR, "historial_chat.json")
    if not os.path.exists(asignaciones_file) and not os.path.exists(historial_file):
        return
    logger.info("🔄 Migrando datos históricos...")
    if os.path.exists(asignaciones_file):
        try:
            with open(asignaciones_file, 'r', encoding='utf-8') as f:
                asignaciones = json.load(f)
            conn = get_db()
            c = conn.cursor()
            for tel, data in asignaciones.items():
                c.execute('INSERT OR REPLACE INTO users (tel, coordinadora, user_type, last_interaction) VALUES (?, ?, ?, ?)', 
                         (tel, data.get('nombre'), 'prospecto', datetime.now(TZ_LIMA)))
                c.execute('INSERT INTO assignments (user_tel, coord_nombre, coord_tel, estado) VALUES (?, ?, ?, ?)',
                         (tel, data.get('nombre'), data.get('tel'), 'activa'))
            conn.commit()
            conn.close()
            logger.info(f"✅ Migradas {len(asignaciones)} asignaciones")
        except Exception as e:
            logger.error(f"❌ Error migrando asignaciones: {e}")
    if os.path.exists(historial_file):
        try:
            with open(historial_file, 'r', encoding='utf-8') as f:
                historial = json.load(f)
            conn = get_db()
            c = conn.cursor()
            for msg in historial:
                c.execute('INSERT INTO messages (user_tel, direction, content, timestamp) VALUES (?, ?, ?, ?)',
                         (msg.get('telefono'), msg.get('tipo'), msg.get('texto'), msg.get('hora')))
            conn.commit()
            conn.close()
            logger.info(f"✅ Migrados {len(historial)} mensajes")
        except Exception as e:
            logger.error(f"❌ Error migrando historial: {e}")

# ── CLASIFICACIÓN DE USUARIOS ──
def clasificar_usuario(tel):
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE tel=?", (tel,))
        user = c.fetchone()
        if user:
            return dict(user)
    # Default si no existe
    tipo = "prospecto"
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO users (tel, user_type, last_interaction) VALUES (?, ?, ?)', 
             (tel, tipo, datetime.now(TZ_LIMA)))
    conn.commit()
    conn.close()
    return {"tel": tel, "user_type": tipo}

# ── ASIGNACIÓN EQUÍTATIVA ──
def asignar_coordinadora(tel, nombre_usuario=""):
    conn = get_db()
    c = conn.cursor()
    # Verificar asignación existente
    c.execute('SELECT * FROM assignments WHERE user_tel=? AND estado="activa" ORDER BY created_at DESC LIMIT 1', (tel,))
    existing = c.fetchone()
    if existing:
        conn.close()
        return {"nombre": existing["coord_nombre"], "tel": existing["coord_tel"]}
    # Contar casos por coordinadora
    c.execute('SELECT coord_nombre, COUNT(*) as count FROM assignments WHERE estado="activa" GROUP BY coord_nombre')
    conteo = {row["coord_nombre"]: row["count"] for row in c.fetchall()}
    for coord in COORDINADORAS.keys():
        if coord not in conteo:
            conteo[coord] = 0
    coord_elegida = min(conteo, key=conteo.get)
    coord_tel = COORDINADORAS[coord_elegida]
    # Guardar asignación
    c.execute('INSERT INTO assignments (user_tel, coord_nombre, coord_tel, estado) VALUES (?, ?, ?, ?)',
             (tel, coord_elegida, coord_tel, 'activa'))
    c.execute('UPDATE users SET coordinadora=?, last_interaction=? WHERE tel=?',
             (coord_elegida, datetime.now(TZ_LIMA), tel))
    conn.commit()
    conn.close()
    logger.info(f"✅ Asignado {tel} → {coord_elegida}")
    return {"nombre": coord_elegida, "tel": coord_tel}

def liberar_asignacion(tel):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE assignments SET estado="liberada", released_at=? WHERE user_tel=? AND estado="activa"',
             (datetime.now(TZ_LIMA), tel))
    conn.commit()
    liberado = c.rowcount > 0
    conn.close()
    return liberado

# ── GEMINI IA ──
def responder_con_gemini(mensaje, user_data):
    if not GEMINI_OK:
        return None
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        contexto = f"Tipo: {user_data.get('user_type', 'prospecto')}, Coord: {user_data.get('coordinadora', 'ninguna')}"
        prompt = f"""Eres el asistente de Crear Poder Sin Límites Perú.
{contexto}
Mensaje: "{mensaje}"
INSTRUCCIONES:
1. Si pregunta C1/C2/Maestría → Info oficial breve
2. Si pregunta pagos → BCP 1934218307060, Yape/Plin 908652308
3. Si confirma → Indica que asignaremos coordinadora
4. Dudas complejas → Ofrece conectar con coordinadora
5. Tono: Empático, motivador, profesional
6. Máximo 3-4 oraciones, NUNCA inventes información
Responde:"""
        response = client.models.generate_content(model="gemini-2.0-flash", contents=prompt)
        return response.text.strip()
    except Exception as e:
        logger.error(f"❌ Error Gemini: {e}")
        return None

# ── ENVÍO DE MENSAJES ──
def enviar_mensaje(tel, texto, direction="out"):
    # Guardar en DB
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_tel, direction, content, timestamp) VALUES (?, ?, ?, ?)',
             (tel, direction, texto, datetime.now(TZ_LIMA)))
    c.execute('UPDATE users SET last_interaction=? WHERE tel=?', (datetime.now(TZ_LIMA), tel))
    conn.commit()
    conn.close()
    # Enviar por WhatsApp API
    url = f"https://graph.facebook.com/v20.0/{os.environ.get('WA_PHONE_ID')}/messages"
    headers = {"Authorization": f"Bearer {os.environ.get('WA_TOKEN')}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": str(tel), "type": "text", "text": {"body": texto}}
    try:
        resp = req_lib.post(url, json=payload, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"❌ Error enviando: {e}")
        return False

# ── FLUJO PRINCIPAL ──
def procesar_mensaje(tel, texto, nombre_wa=""):
    logger.info(f"📨 {tel}: {texto[:50]}")
    user_data = clasificar_usuario(tel)
    txt_up = texto.strip().upper()
    
    # Comandos de coordinadora
    if texto.startswith("/"):
        procesar_comando_coordinadora(tel, texto)
        return
    
    # IA para mensajes no estructurados
    if txt_up not in ["1", "2", "3", "MENU", "PAGOS", "SÍ", "SI", "CONFIRMO"]:
        respuesta_ia = responder_con_gemini(texto, user_data)
        if respuesta_ia:
            enviar_mensaje(tel, respuesta_ia)
            return
    
    # Flujos estructurados
    if txt_up in ["SÍ", "SI", "CONFIRMO", "1"]:
        coord = asignar_coordinadora(tel, nombre_wa)
        msg_px = f"¡Excelente! 🚀 Confirmamos tu asistencia.\n\nTu coordinadora será *{coord['nombre']}*. Ella te contactará pronto.\n\n¿Dudas de pago? Escribe *PAGOS*"
        enviar_mensaje(tel, msg_px)
        msg_coord = f"🚨 *NUEVA CONFIRMACIÓN C1*\n\nProspecto: {nombre_wa}\nTel: wa.me/{tel}\n\nYa le informé que eres su coordinadora."
        enviar_mensaje(coord['tel'], msg_coord)
    elif txt_up in ["APOYO", "AYUDA", "DUDA", "2"]:
        coord = asignar_coordinadora(tel, nombre_wa)
        msg_px = f"Con gusto te ayudo. Soy {coord['nombre']} de Coordinación. ¿Qué necesitas?"
        enviar_mensaje(tel, msg_px)
        msg_coord = f"🚨 *SOLICITUD DE APOYO*\n\n{nombre_wa} (wa.me/{tel}) necesita ayuda.\nMensaje: '{texto}'"
        enviar_mensaje(coord['tel'], msg_coord)
    elif "PAGO" in txt_up or "PAGOS" in txt_up:
        msg = f"💳 *MÉTODOS DE PAGO:*\n\n🏦 *BCP Soles:* 1934218307060\n📱 *Yape/Plin:* 908652308\n\nEnvía la captura por este chat ✅"
        enviar_mensaje(tel, msg)
    elif txt_up in ["MENU", "MENÚ", "0"]:
        mostrar_menu(tel, user_data)
    else:
        mostrar_menu(tel, user_data)

def mostrar_menu(tel, user_data):
    tipo = user_data.get('user_type', 'prospecto')
    if tipo == "imo":
        msg = "🌟 *Portal IMO*\n\n1️⃣ Ver mis prospectos\n2️⃣ Reportar avance\n3️⃣ Soporte técnico\n\nEscribe el número"
    elif tipo == "graduado":
        msg = "🎓 *Comunidad Maestría*\n\n1️⃣ Próximo evento MJ\n2️⃣ Beneficios graduados\n3️⃣ Referir amigo\n\nEscribe el número"
    else:
        msg = "🌟 *Crear Poder Sin Límites Perú*\n\n1️⃣ Confirmar asistencia C1\n2️⃣ Información del entrenamiento\n3️⃣ Hablar con coordinadora\n💳 *PAGOS* para opciones bancarias\n\nEscribe el número o palabra clave"
    enviar_mensaje(tel, msg)

def procesar_comando_coordinadora(tel, comando):
    cmd = comando.strip().lower()
    if cmd.startswith("/liberar"):
        partes = cmd.split()
        if len(partes) >= 2:
            tel_a_liberar = partes[1]
            if liberar_asignacion(tel_a_liberar):
                enviar_mensaje(tel, f"✅ Caso {tel_a_liberar} liberado")
            else:
                enviar_mensaje(tel, "❌ No se encontró asignación activa")
        else:
            enviar_mensaje(tel, "❌ Uso: /liberar 51999123456")
    elif cmd == "/ver_mis_casos":
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT user_tel, created_at FROM assignments WHERE coord_tel=? AND estado="activa" ORDER BY created_at DESC', (tel,))
        casos = c.fetchall()
        conn.close()
        if casos:
            msg = f"📋 *Tus casos activos:* ({len(casos)})\n\n"
            for caso in casos[:10]:
                msg += f"• {caso['user_tel']}\n"
            enviar_mensaje(tel, msg)
        else:
            enviar_mensaje(tel, "✅ No tienes casos activos")
    else:
        enviar_mensaje(tel, "❌ Comando no reconocido. Usa /liberar o /ver_mis_casos")

# ── WEBHOOK WHATSAPP ──
@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    if request.method == "GET":
        if request.args.get("hub.verify_token") == "cpsl2026":
            return request.args.get("hub.challenge"), 200
        return "Token inválido", 403
    try:
        data = request.get_json(silent=True)
        msg = data["entry"][0]["changes"][0]["value"]["messages"][0]
        tel = msg["from"]
        texto = msg["text"]["body"] if msg["type"] == "text" else ""
        nombre_wa = data["entry"][0]["changes"][0]["value"]["contacts"][0]["profile"]["name"]
        if texto:
            threading.Thread(target=procesar_mensaje, args=(tel, texto, nombre_wa), daemon=True).start()
    except Exception as e:
        logger.error(f"❌ Error webhook: {e}")
    return jsonify({"status": "ok"}), 200

# ── API PARA PANEL ──
@app.route("/api/historial")
def api_historial():
    limit = request.args.get("limit", 100, type=int)
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT m.*, u.nombre, u.coordinadora FROM messages m LEFT JOIN users u ON m.user_tel = u.tel ORDER BY m.timestamp DESC LIMIT ?', (limit,))
    mensajes = []
    for row in c.fetchall():
        mensajes.append({"telefono": row["user_tel"], "nombre": row["nombre"] or "Desconocido", "texto": row["content"], "tipo": row["direction"], "hora": row["timestamp"], "coordinadora": row["coordinadora"]})
    conn.close()
    return jsonify(mensajes), 200

@app.route("/api/estadisticas")
def api_estadisticas():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total = c.fetchone()[0]
    c.execute("SELECT user_type, COUNT(*) FROM users GROUP BY user_type")
    por_tipo = dict(c.fetchall())
    c.execute('SELECT coord_nombre, COUNT(*) FROM assignments WHERE estado="activa" GROUP BY coord_nombre')
    por_coord = dict(c.fetchall())
    hoy = datetime.now(TZ_LIMA).strftime("%Y-%m-%d")
    c.execute('SELECT COUNT(*) FROM messages WHERE timestamp LIKE ?', (f"{hoy}%",))
    mensajes_hoy = c.fetchone()[0]
    conn.close()
    return jsonify({"total_usuarios": total, "por_tipo": por_tipo, "por_coordinadora": por_coord, "mensajes_hoy": mensajes_hoy}), 200

@app.route("/chat")
def chat_panel():
    try:
        with open("panel_chat.html", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Panel no encontrado</h1><p>Sube panel_chat.html</p>", 404

@app.route("/status")
def status():
    db_ok = os.path.exists(DB_PATH)
    return jsonify({"status": "ok", "version": "V200-Quantum", "gemini": "✅" if GEMINI_OK else "❌", "db": "✅" if db_ok else "❌"}), 200

# ── MIGRACIÓN AL INICIAR (solo para ejecuciones locales) ──
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot CPSL V200...")
    migrate_from_json()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
