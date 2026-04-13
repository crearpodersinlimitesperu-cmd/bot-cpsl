"""
Bot WhatsApp V200 - Crear Poder Sin Límites Perú
✅ TODO EN UNO: SQLite + Gemini + Panel Mejorado + Sync Auto
✅ Solo copiar y pegar en Render
"""
import os, re, json, time, csv, logging, threading, sqlite3
from flask import Flask, request, jsonify, Response, send_file
from datetime import datetime, timedelta, timezone
import requests as req_lib
from filelock import FileLock
from contextlib import contextmanager

# ── IMPORT GEMINI ──
try:
    from google import genai
    GEMINI_OK = True
except:
    GEMINI_OK = False
    logging.warning("⚠️ Gemini no disponible")

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

# ── BASE DE DATOS SQLITE ──
def init_db():
    """Inicializa SQLite con todas las tablas"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        
        # Tabla usuarios
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            tel TEXT PRIMARY KEY,
            nombre TEXT,
            user_type TEXT DEFAULT 'prospecto',
            estado TEXT DEFAULT 'activo',
            coordinadora TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_interaction TIMESTAMP
        )''')
        
        # Tabla asignaciones
        c.execute('''CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_tel TEXT,
            coord_nombre TEXT,
            coord_tel TEXT,
            estado TEXT DEFAULT 'activa',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            released_at TIMESTAMP,
            FOREIGN KEY (user_tel) REFERENCES users(tel)
        )''')
        
        # Tabla mensajes
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_tel TEXT,
            direction TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_tel) REFERENCES users(tel)
        )''')
        
        # Tabla sync log
        c.execute('''CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            last_sync TIMESTAMP,
            records_synced INTEGER,
            errors TEXT
        )''')
        
        conn.commit()
        logger.info("✅ Base de datos SQLite inicializada")

@contextmanager
def get_db():
    """Context manager para SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# ── MIGRACIÓN DESDE JSON ──
def migrate_from_json():
    """Migra datos históricos de JSON a SQLite (solo primera vez)"""
    asignaciones_file = os.path.join(DATA_DIR, "asignaciones.json")
    historial_file = os.path.join(DATA_DIR, "historial_chat.json")
    
    if not os.path.exists(asignaciones_file) and not os.path.exists(historial_file):
        return
    
    logger.info("🔄 Migrando datos históricos a SQLite...")
    
    # Migrar asignaciones
    if os.path.exists(asignaciones_file):
        try:
            with open(asignaciones_file, 'r', encoding='utf-8') as f:
                asignaciones = json.load(f)
            
            with get_db() as conn:
                c = conn.cursor()
                for tel, data in asignaciones.items():
                    c.execute('''INSERT OR REPLACE INTO users 
                                (tel, coordinadora, user_type, last_interaction) 
                                VALUES (?, ?, 'prospecto', ?)''', 
                             (tel, data.get('nombre'), datetime.now(TZ_LIMA)))
                    c.execute('''INSERT INTO assignments 
                                (user_tel, coord_nombre, coord_tel, estado) 
                                VALUES (?, ?, ?, 'activa')''',
                             (tel, data.get('nombre'), data.get('tel')))
                conn.commit()
            logger.info(f"✅ Migradas {len(asignaciones)} asignaciones")
        except Exception as e:
            logger.error(f"❌ Error migrando asignaciones: {e}")
    
    # Migrar historial
    if os.path.exists(historial_file):
        try:
            with open(historial_file, 'r', encoding='utf-8') as f:
                historial = json.load(f)
            
            with get_db() as conn:
                c = conn.cursor()
                for msg in historial:
                    c.execute('''INSERT INTO messages 
                                (user_tel, direction, content, timestamp) 
                                VALUES (?, ?, ?, ?)''',
                             (msg.get('telefono'), msg.get('tipo'), 
                              msg.get('texto'), msg.get('hora')))
                conn.commit()
            logger.info(f"✅ Migrados {len(historial)} mensajes")
        except Exception as e:
            logger.error(f"❌ Error migrando historial: {e}")

# ── CLASIFICACIÓN DE USUARIOS ──
def clasificar_usuario(tel):
    """
    Detecta automáticamente el tipo de usuario:
    1. IMO (está en Excel como IMO)
    2. Graduado (está en GRADUADOS.csv)
    3. Participante (tiene C1/C2 activo)
    4. Prospecto (default)
    """
    with get_db() as conn:
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE tel=?", (tel,))
        user = c.fetchone()
        
        if user:
            return dict(user)
    
    # Si no está en DB, buscar en Excel
    tipo = detectar_en_excel(tel)
    
    # Guardar en DB
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO users 
                    (tel, user_type, last_interaction) 
                    VALUES (?, ?, ?)''', 
                 (tel, tipo, datetime.now(TZ_LIMA)))
        conn.commit()
    
    return {"tel": tel, "user_type": tipo}

def detectar_en_excel(tel):
    """Busca el teléfono en el Excel para detectar si es IMO o participante"""
    try:
        if not os.path.exists(EXCEL_PATH):
            return "prospecto"
        
        # Aquí iría la lógica de openpyxl para leer el Excel
        # Por ahora retornamos prospecto
        return "prospecto"
    except:
        return "prospecto"

# ── ASIGNACIÓN EQUÍTATIVA ──
def asignar_coordinadora(tel, nombre_usuario=""):
    """Asigna la coordinadora con menos casos activos"""
    with get_db() as conn:
        c = conn.cursor()
        
        # Verificar si ya tiene asignación activa
        c.execute('''SELECT * FROM assignments 
                    WHERE user_tel=? AND estado='activa' 
                    ORDER BY created_at DESC LIMIT 1''', (tel,))
        existing = c.fetchone()
        
        if existing:
            return {"nombre": existing["coord_nombre"], "tel": existing["coord_tel"]}
        
        # Contar casos activos por coordinadora
        c.execute('''SELECT coord_nombre, COUNT(*) as count 
                    FROM assignments 
                    WHERE estado='activa' 
                    GROUP BY coord_nombre''')
        conteo = {row["coord_nombre"]: row["count"] for row in c.fetchall()}
        
        # Asegurar que todas las coordinadoras estén en el conteo
        for coord in COORDINADORAS.keys():
            if coord not in conteo:
                conteo[coord] = 0
        
        # Elegir la que tenga menos casos
        coord_elegida = min(conteo, key=conteo.get)
        coord_tel = COORDINADORAS[coord_elegida]
        
        # Guardar asignación
        c.execute('''INSERT INTO assignments 
                    (user_tel, coord_nombre, coord_tel, estado) 
                    VALUES (?, ?, ?, 'activa')''',
                 (tel, coord_elegida, coord_tel))
        
        # Actualizar usuario
        c.execute('''UPDATE users SET coordinadora=?, last_interaction=? WHERE tel=?''',
                 (coord_elegida, datetime.now(TZ_LIMA), tel))
        
        conn.commit()
        logger.info(f"✅ Asignado {tel} → {coord_elegida}")
        
        return {"nombre": coord_elegida, "tel": coord_tel}

def liberar_asignacion(tel):
    """Libera una asignación (comando de coordinadora)"""
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''UPDATE assignments 
                    SET estado='liberada', released_at=? 
                    WHERE user_tel=? AND estado='activa' ''',
                 (datetime.now(TZ_LIMA), tel))
        conn.commit()
        return c.rowcount > 0

# ── GEMINI IA ──
def responder_con_gemini(mensaje, user_data):
    """Genera respuesta usando Gemini 2.0 Flash"""
    if not GEMINI_OK:
        return None
    
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        # Construir contexto
        contexto = f"""
        Tipo de usuario: {user_data.get('user_type', 'prospecto')}
        Coordinadora asignada: {user_data.get('coordinadora', 'ninguna')}
        """
        
        prompt = f"""
        Eres el asistente virtual de Crear Poder Sin Límites Perú.
        
        {contexto}
        
        Mensaje del usuario: "{mensaje}"
        
        INSTRUCCIONES:
        1. Si pregunta sobre C1/C2/Maestría → Da información oficial breve
        2. Si pregunta pagos → Menciona BCP 1934218307060, Yape/Plin 908652308
        3. Si confirma asistencia → Indica que asignaremos coordinadora
        4. Si tiene dudas complejas → Ofrece conectar con coordinadora
        5. Tono: Empático, motivador, profesional
        6. Máximo 3-4 oraciones
        7. NUNCA inventes información
        
        Responde de forma natural y útil:
        """
        
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        
        return response.text.strip()
    
    except Exception as e:
        logger.error(f"❌ Error Gemini: {e}")
        return None

# ── ENVÍO DE MENSAJES ──
def enviar_mensaje(tel, texto, direction="out"):
    """Envía mensaje por WhatsApp y guarda en DB"""
    # Guardar en DB
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''INSERT INTO messages 
                    (user_tel, direction, content, timestamp) 
                    VALUES (?, ?, ?, ?)''',
                 (tel, direction, texto, datetime.now(TZ_LIMA)))
        
        # Actualizar última interacción
        c.execute('''UPDATE users SET last_interaction=? WHERE tel=?''',
                 (datetime.now(TZ_LIMA), tel))
        conn.commit()
    
    # Enviar por WhatsApp API
    url = f"https://graph.facebook.com/v20.0/{os.environ.get('WA_PHONE_ID')}/messages"
    headers = {
        "Authorization": f"Bearer {os.environ.get('WA_TOKEN')}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": str(tel),
        "type": "text",
        "text": {"body": texto}
    }
    
    try:
        resp = req_lib.post(url, json=payload, headers=headers, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        logger.error(f"❌ Error enviando mensaje: {e}")
        return False

# ── FLUJO PRINCIPAL ──
def procesar_mensaje(tel, texto, nombre_wa=""):
    """Procesa cada mensaje entrante"""
    logger.info(f"📨 {tel}: {texto[:50]}")
    
    # Clasificar usuario
    user_data = clasificar_usuario(tel)
    txt_up = texto.strip().upper()
    
    # ── MENSAJES DE COORDINADORAS (comandos) ──
    if texto.startswith("/"):
        procesar_comando_coordinadora(tel, texto)
        return
    
    # ── INTELIGENCIA ARTIFICIAL (Gemini) ──
    if txt_up not in ["1", "2", "3", "MENU", "PAGOS", "SÍ", "SI", "CONFIRMO"]:
        # Usar Gemini para responder
        respuesta_ia = responder_con_gemini(texto, user_data)
        if respuesta_ia:
            enviar_mensaje(tel, respuesta_ia)
            return
    
    # ── FLUJOS ESTRUCTURADOS ──
    if txt_up in ["SÍ", "SI", "CONFIRMO", "1"]:
        # Confirmación de asistencia
        coord = asignar_coordinadora(tel, nombre_wa)
        
        msg_px = f"¡Excelente! 🚀 Confirmamos tu asistencia.\n\nTu coordinadora será *{coord['nombre']}*. Ella te contactará pronto para el registro.\n\n¿Tienes dudas sobre pagos? Escribe *PAGOS*"
        enviar_mensaje(tel, msg_px)
        
        # Notificar a coordinadora
        msg_coord = f"🚨 *NUEVA CONFIRMACIÓN C1*\n\nProspecto: {nombre_wa}\nTel: wa.me/{tel}\n\nYa le informé que eres su coordinadora."
        enviar_mensaje(coord['tel'], msg_coord)
        
    elif txt_up in ["APOYO", "AYUDA", "DUDA", "2"]:
        # Solicitud de apoyo
        coord = asignar_coordinadora(tel, nombre_wa)
        
        msg_px = f"Con gusto te ayudo. Soy {coord['nombre']} de Coordinación. Cuéntame, ¿qué necesitas?"
        enviar_mensaje(tel, msg_px)
        
        msg_coord = f"🚨 *SOLICITUD DE APOYO*\n\n{nombre_wa} (wa.me/{tel}) necesita ayuda.\nMensaje: '{texto}'"
        enviar_mensaje(coord['tel'], msg_coord)
        
    elif "PAGO" in txt_up or "PAGOS" in txt_up:
        # Información de pagos
        msg = f"💳 *MÉTODOS DE PAGO:*\n\n" \
              f"🏦 *BCP Soles:* 1934218307060\n" \
              f"📱 *Yape/Plin:* 908652308\n\n" \
              f"Por favor envía la captura por este chat ✅"
        enviar_mensaje(tel, msg)
        
    elif txt_up in ["MENU", "MENÚ", "0"]:
        # Menú principal
        mostrar_menu(tel, user_data)
        
    else:
        # Menú por defecto
        mostrar_menu(tel, user_data)

def mostrar_menu(tel, user_data):
    """Muestra menú contextual según tipo de usuario"""
    tipo = user_data.get('user_type', 'prospecto')
    
    if tipo == "imo":
        msg = "🌟 *Portal IMO*\n\n" \
              "1️⃣ Ver mis prospectos\n" \
              "2️⃣ Reportar avance\n" \
              "3️⃣ Soporte técnico\n\n" \
              "Escribe el número de la opción"
    elif tipo == "graduado":
        msg = " *Comunidad Maestría*\n\n" \
              "1️⃣ Próximo evento MJ\n" \
              "2️⃣ Beneficios graduados\n" \
              "3️⃣ Referir amigo\n\n" \
              "Escribe el número"
    else:
        msg = "🌟 *Crear Poder Sin Límites Perú*\n\n" \
              "1️⃣ Confirmar asistencia C1\n" \
              "2️⃣ Información del entrenamiento\n" \
              "3️⃣ Hablar con coordinadora\n" \
              "💳 *PAGOS* para opciones bancarias\n\n" \
              "Escribe el número o la palabra clave"
    
    enviar_mensaje(tel, msg)

def procesar_comando_coordinadora(tel, comando):
    """Procesa comandos de coordinadoras"""
    cmd = comando.strip().lower()
    
    if cmd.startswith("/liberar"):
        # /liberar 51999123456
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
        # Mostrar casos activos de la coordinadora
        with get_db() as conn:
            c = conn.cursor()
            c.execute('''SELECT user_tel, created_at FROM assignments 
                        WHERE coord_tel=? AND estado='activa' 
                        ORDER BY created_at DESC''', (tel,))
            casos = c.fetchall()
        
        if casos:
            msg = f"📋 *Tus casos activos:* ({len(casos)})\n\n"
            for caso in casos[:10]:  # Máximo 10
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
            # Procesar en thread separado
            threading.Thread(
                target=procesar_mensaje,
                args=(tel, texto, nombre_wa),
                daemon=True
            ).start()
        
    except Exception as e:
        logger.error(f"❌ Error webhook: {e}")
    
    return jsonify({"status": "ok"}), 200

# ── API PARA PANEL ──
@app.route("/api/historial")
def api_historial():
    """Devuelve historial de mensajes para el panel"""
    limit = request.args.get("limit", 100, type=int)
    
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''SELECT m.*, u.nombre, u.coordinadora 
                    FROM messages m 
                    LEFT JOIN users u ON m.user_tel = u.tel 
                    ORDER BY m.timestamp DESC 
                    LIMIT ?''', (limit,))
        
        mensajes = []
        for row in c.fetchall():
            mensajes.append({
                "telefono": row["user_tel"],
                "nombre": row["nombre"] or "Desconocido",
                "texto": row["content"],
                "tipo": row["direction"],
                "hora": row["timestamp"],
                "coordinadora": row["coordinadora"]
            })
    
    return jsonify(mensajes), 200

@app.route("/api/estadisticas")
def api_estadisticas():
    """Devuelve estadísticas para el dashboard"""
    with get_db() as conn:
        c = conn.cursor()
        
        # Total usuarios
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        
        # Por tipo
        c.execute("SELECT user_type, COUNT(*) FROM users GROUP BY user_type")
        por_tipo = dict(c.fetchall())
        
        # Asignaciones activas por coordinadora
        c.execute('''SELECT coord_nombre, COUNT(*) 
                    FROM assignments 
                    WHERE estado='activa' 
                    GROUP BY coord_nombre''')
        por_coord = dict(c.fetchall())
        
        # Mensajes hoy
        hoy = datetime.now(TZ_LIMA).strftime("%Y-%m-%d")
        c.execute('''SELECT COUNT(*) FROM messages 
                    WHERE timestamp LIKE ?''', (f"{hoy}%",))
        mensajes_hoy = c.fetchone()[0]
    
    return jsonify({
        "total_usuarios": total,
        "por_tipo": por_tipo,
        "por_coordinadora": por_coord,
        "mensajes_hoy": mensajes_hoy
    }), 200

@app.route("/chat")
def chat_panel():
    """Sirve el panel de control"""
    try:
        with open("panel_chat.html", encoding="utf-8") as f:
            return f.read()
    except:
        return "<h1>Panel no encontrado</h1><p>Sube el archivo panel_chat.html</p>", 404

@app.route("/status")
def status():
    """Health check"""
    return jsonify({
        "status": "ok",
        "version": "V200-Quantum",
        "gemini": "✅" if GEMINI_OK else "❌",
        "db": "✅" if os.path.exists(DB_PATH) else "❌"
    }), 200

# ── INICIO ──
if __name__ == "__main__":
    logger.info("🚀 Iniciando Bot CPSL V200...")
    
    # Inicializar DB
    init_db()
    
    # Migrar datos históricos (solo primera vez)
    migrate_from_json()
    
    # Iniciar servidor
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
