"""
TORRE DE CONTROL CPSL LIMA — Motor Central
Servidor FastAPI con base de datos SQLite persistente.
Todos los datos se cargan una vez y persisten entre reinicios.
"""
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd
import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

load_dotenv()

# Coordinadoras bloqueadas (solo data histórica, NO campañas)
CC_BLOQUEADAS = ['leyla', 'linid']
# Coordinadoras activas para campañas
CC_ACTIVAS = ['joyce', 'diana']

# ============================================================
# CONFIGURACIÓN
# ============================================================
app = FastAPI(title="CPSL TORRE DE CONTROL - BLINDADA")
DB_PATH = os.path.join(os.path.dirname(__file__), "caja_negra.db")
DATA_DIR = os.path.dirname(__file__)

# Horario permitido para comunicaciones
HORA_INICIO = 8   # 8 AM
HORA_FIN = 20     # 8 PM

# ============================================================
# BASE DE DATOS — INICIALIZACIÓN
# ============================================================
def get_db():
    """Establece conexión con la base de datos (PostgreSQL en cloud, SQLite local)."""
    db_url = os.getenv("DATABASE_URL")
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Usar PostgreSQL (Cloud)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(db_url)
        return conn
    else:
        # Usar SQLite (Local)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn

@contextmanager
def db_session():
    """Context manager para conexiones seguras a la DB."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Inicializa el esquema de la base de datos si no existe."""
    conn = get_db()
    conn = get_db()
    c = conn.cursor()
    
    # Determinar si es Postgres o SQLite para la sintaxis de autoincremento
    is_postgres = hasattr(conn, 'cursor_factory') # psycopg2 tiene esto, sqlite3 no
    autoincrement = "SERIAL PRIMARY KEY" if is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    
    # Tabla maestra de participantes
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS participantes (
        id {autoincrement},
        nombre TEXT,
        apellido TEXT,
        nombre_preferido TEXT,
        telefono TEXT,
        email TEXT,
        equipo TEXT,
        imo TEXT,
        tel_imo TEXT,
        cc_asignada TEXT,
        cc_nombre TEXT,
        cc_tel TEXT,
        c1 TEXT DEFAULT 'NO',
        c2 TEXT DEFAULT 'NO',
        maestria TEXT DEFAULT 'NO',
        tipo TEXT,
        identificacion TEXT,
        estado TEXT DEFAULT 'PENDIENTE',
        fecha_registro TEXT,
        fecha_actualizacion TEXT
    )
    """)
    
    # Tabla de desertores históricos
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS desertores (
        id {autoincrement},
        equipo TEXT,
        nombre TEXT,
        motivo TEXT,
        devolucion TEXT DEFAULT 'NO'
    )
    """)
    
    # Caja Negra — registro inmutable de toda acción
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS caja_negra (
        id {autoincrement},
        timestamp TEXT,
        tipo TEXT,
        accion TEXT,
        detalle TEXT,
        canal TEXT,
        px_nombre TEXT,
        px_telefono TEXT,
        resultado TEXT
    )
    """)
    
    # Tabla de comunicaciones programadas
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS comunicaciones (
        id {autoincrement},
        px_id INTEGER,
        nombre_px TEXT,
        telefono TEXT,
        email TEXT,
        canal TEXT,
        plantilla TEXT,
        mensaje_preview TEXT,
        estado TEXT DEFAULT 'PENDIENTE',
        fecha_programada TEXT,
        fecha_enviado TEXT,
        entrenamiento TEXT,
        equipo TEXT,
        cc_nombre TEXT
    )
    """)
    
    # Crear índices para rendimiento (Solo si no es Postgres, que los maneja diferente o requiere sintaxis distinta)
    if not is_postgres:
        c.execute("CREATE INDEX IF NOT EXISTS idx_participantes_telefono ON participantes(telefono)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_participantes_cc ON participantes(cc_nombre)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_participantes_equipo ON participantes(equipo)")
    
    conn.commit()
    conn.close()

def es_cc_bloqueada(cc_nombre):
    """Verifica si una coordinadora está bloqueada para campañas."""
    if not cc_nombre:
        return True  # Sin CC = bloqueada
    return any(b in cc_nombre.lower() for b in CC_BLOQUEADAS)

def es_horario_permitido():
    """Verifica si estamos en horario de envío (8AM-8PM Lima)."""
    hora = datetime.now().hour
    return HORA_INICIO <= hora < HORA_FIN

# ============================================================
# CARGA DE DATOS REALES
# ============================================================
def cargar_datos_reales():
    """Carga los CSV reales a la base de datos SQLite (solo si está vacía)."""
    conn = get_db()
    c = conn.cursor()
    
    is_postgres = hasattr(conn, 'cursor_factory')
    
    # Verificar si ya hay datos
    c.execute("SELECT COUNT(*) FROM participantes")
    count = c.fetchone()[0]
    
    if count > 0:
        registrar_caja_negra("SYSTEM", "DB_CHECK", f"Base de datos ya contiene {count} registros. Omitiendo carga.", "", "", "")
        conn.close()
        return
    
    # Si estamos en Postgres, no cargamos CSVs locales automáticamente para evitar lentitud
    if is_postgres:
        print("--- CONECTADO A CLOUD (POSTGRES) ---")
        conn.close()
        return
    
    # Cargar participantes desde Prospectos (tiene CC asignada)
    csv_path = os.path.join(DATA_DIR, "Prospectos_Pendientes_C1_Depurado_Campana.csv")
    if not os.path.exists(csv_path):
        csv_path = os.path.join(DATA_DIR, "E27_participantes_limpio.csv")
    
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        
        now = datetime.now().isoformat()
        inserted = 0
        
        def clean(val):
            """Limpia valores nan, None, 'nan' a cadena vacía."""
            s = str(val).strip()
            return '' if s in ('nan', 'None', 'NaN', '') else s
        
        def clean_phone(val):
            """Limpia teléfonos: quita .0, notación científica, etc."""
            s = str(val).strip()
            if s in ('nan', 'None', 'NaN', ''): return ''
            try:
                n = int(float(s))
                return str(n)
            except (ValueError, TypeError):
                return s

        for _, row in df.iterrows():
            nombre = clean(row.get('Nombre', ''))
            # Apellido: usar 'Apellidos' (con s) si 'Apellido' está vacío
            apellido = clean(row.get('Apellido', ''))
            if not apellido:
                apellido = clean(row.get('Apellidos', ''))
            
            # Nombre preferido: primer nombre solamente, nunca apellido
            nombre_preferido = nombre.split()[0].title() if nombre else ''
            
            # Leer CC con nombres originales (con o sin tildes)
            telefono = clean_phone(row.get('Teléfono', row.get('Telefono', '')))
            maestria = clean(row.get('Maestría', row.get('Maestria', 'NO')))
            identificacion = clean(row.get('Identificación', row.get('Identificacion', '')))
            cc_nombre = clean(row.get('CC_NOMBRE_COMPLETO', ''))
            cc_asignada = clean(row.get('CC_ASIGNADA', ''))
            cc_tel = clean_phone(row.get('CC_TEL', ''))
            
            c.execute("""
                INSERT INTO participantes 
                (nombre, apellido, nombre_preferido, telefono, equipo, imo, tel_imo, 
                 cc_asignada, cc_nombre, cc_tel, c1, c2, maestria, tipo, identificacion,
                 estado, fecha_registro, fecha_actualizacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nombre, apellido, nombre_preferido,
                telefono,
                clean(row.get('Equipo', '')),
                clean(row.get('IMO', '')),
                clean_phone(row.get('Tel. IMO', row.get('Tel IMO', ''))),
                cc_asignada,
                cc_nombre,
                cc_tel,
                clean(row.get('C1', 'NO')) or 'NO',
                clean(row.get('C2', 'NO')) or 'NO',
                maestria or 'NO',
                clean(row.get('Tipo', '')),
                identificacion,
                'ACTIVO' if clean(row.get('C1', 'NO')) == 'SI' else 'PENDIENTE',
                now, now
            ))
            inserted += 1
        
        conn.commit()
        registrar_caja_negra("SYSTEM", "DATA_LOAD", f"Cargados {inserted} participantes desde {os.path.basename(csv_path)}", "", "", "OK")
    
    # Cargar desertores
    csv_des = os.path.join(DATA_DIR, "auditoria_desertores_total.csv")
    if os.path.exists(csv_des):
        df_des = pd.read_csv(csv_des)
        for _, row in df_des.iterrows():
            c.execute("INSERT INTO desertores (equipo, nombre, motivo, devolucion) VALUES (?, ?, ?, ?)",
                      (str(row.get('Equipo', '')), str(row.get('Nombre', '')), 
                       str(row.get('Motivo', 'N/A')), str(row.get('Devolucion', 'NO'))))
        conn.commit()
        registrar_caja_negra("SYSTEM", "DATA_LOAD", f"Cargados {len(df_des)} desertores", "", "", "OK")
    
    conn.close()

def registrar_caja_negra(tipo, accion, detalle, canal="", px_nombre="", resultado=""):
    """Registra un evento en la caja negra (inmutable)."""
    with db_session() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO caja_negra (timestamp, tipo, accion, detalle, canal, px_nombre, px_telefono, resultado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """.replace('?', '%s' if hasattr(conn, 'cursor_factory') else '?'), 
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo, accion, detalle, canal, px_nombre, "", resultado))
        conn.commit()

# ============================================================
# PLANTILLAS DE COMUNICACIÓN
# ============================================================
PLANTILLAS = {
    "DESERTOR_C1": {
        "asunto": "{nombre}, ¿estás listo para honrar tu visión? | CPSL Lima",
        "cuerpo": """Hola {nombre}.

Hay círculos en la vida que, al quedar abiertos, nos quitan energía. Tu proceso en Capítulo 1 es uno de ellos. 

No se trata solo de un entrenamiento; se trata de tu compromiso contigo mismo y con los resultados que declaraste querer crear. La cancha sigue ahí, esperando por tu fuego y tu determinación.

Hemos abierto una oportunidad exclusiva para que retomes tu lugar y cierres con poder lo que iniciaste.

PRÓXIMO C1:
📅 29 al 31 de mayo, 2026
📍 Sede por confirmar, Lima

Si tu visión sigue viva y estás listo para honrar tu palabra, responde a este mensaje:

ESTOY COMPROMETIDO

Crear Poder Sin Límites Perú
Tu Coordinadora: {cc_nombre}
📞 {cc_tel}""",
        "sms": "{nombre}, los grandes resultados requieren cerrar círculos. Tu C1 te espera este 29 de mayo. ¿Honras tu palabra? Responde: ESTOY COMPROMETIDO"
    },
    "ALTO_RENDIMIENTO_MAÑANA": {
        "asunto": "🔥 ÚLTIMA LLAMADA: Tu compromiso con el Alto Rendimiento",
        "sms": "Hola {nombre}, soy {cc_nombre} de CPSL. El Alto Rendimiento no espera a los que dudan. Mañana cerramos cupos. Tu transformacion vale mas que cualquier excusa. Confirma ahora. ¡Vamos con todo!",
        "cuerpo": "Hola {nombre},\n\nSoy {cc_nombre}. Te escribo porque el compromiso con la excelencia no es negociable. Mañana cerramos la lista oficial y veo que aún no has confirmado tu lugar.\n\nEl Alto Rendimiento requiere decisiones valientes. ¿Estás listo para dar el salto o dejarás que otro ocupe tu lugar?\n\nResponde a este correo o al {cc_tel} para asegurar tu silla.\n\nAtentamente,\n{cc_nombre}"
    },
    "REZAGADO_C2": {
        "asunto": "{nombre}, es hora de consolidar tu poder | CPSL Lima",
        "cuerpo": """Hola {nombre}.

Capítulo 1 fue el despertar. Pero el verdadero juego de la creación de resultados comienza cuando decides dar solidez a lo aprendido y llevarlo a tu vida cotidiana.

Tu silla en Capítulo 2 está reservada, esperando por el líder que decidió no conformarse. Es el momento de adquirir las herramientas avanzadas para cruzar el puente hacia resultados extraordinarios.

PRÓXIMO C2:
📅 14 al 17 de mayo, 2026
📍 Hotel José Antonio Deluxe, Miraflores

Tu visión te está llamando. Responde:
VOY POR TODO

Crear Poder Sin Límites Perú
Tu Coordinadora: {cc_nombre}
📞 {cc_tel}""",
        "sms": "{nombre}, C1 fue el inicio, C2 es la solidez de tus resultados. Tu lugar está listo para este 14 de mayo. ¿Vas por todo? Responde: VOY POR TODO"
    },
    "CONFIRMACION_C2": {
        "asunto": "{nombre}, ¡prepárate para el siguiente nivel! Tu C2 está confirmado | CPSL Lima",
        "cuerpo": """¡Felicidades {nombre}!

Has elegido el camino de la coherencia: el camino de la creación consciente. Tu inscripción para el Equipo 27 de Capítulo 2 es una declaración de poder. 

Estamos listos para recibirte y entregarte las herramientas avanzadas que llevarán tus resultados al siguiente nivel. Aquí tienes tu logística de victoria:

ENTRENAMIENTO: Capítulo 2 — Equipo 27
📅 14 al 17 de mayo, 2026
📍 Hotel José Antonio Deluxe
📍 C. Bellavista 133, Miraflores 15074

CHECKLIST DE PODER (Obligatorio):
✅ Sábana y Almohada (Tu descanso es parte de tu rendimiento)
✅ Ticket Rojo (Tu pase a la experiencia)
✅ Ropa cómoda y mucha hidratación

Tu Coordinadora: {cc_nombre}
📞 {cc_tel}

Confirma que has recibido este llamado a la grandeza respondiendo:
RECIBIDO CON PODER

Crear Poder Sin Límites Perú""",
        "sms": "{nombre}, ¡C2 Confirmado! Prepárate para el 14-17 de mayo en el Hotel José Antonio Deluxe. Lleva tu ticket rojo y tu visión al 100%. Responde: RECIBIDO CON PODER"
    },
    "PENDIENTE_C1": {
        "asunto": "{nombre}, el viaje hacia tu mejor versión comienza aquí | CPSL Lima",
        "cuerpo": """Hola {nombre}.

Tomaste una decisión. Y en el momento en que decides, tu destino comienza a cambiar. Tu lugar en el próximo Capítulo 1 está asegurado y el Equipo 28 ya está vibrando con tu llegada.

Este no es un curso más, es el espacio donde vas a redescubrir de qué eres capaz realmente.

ENTRENAMIENTO: Capítulo 1 — Equipo 28
📅 29 al 31 de mayo, 2026
📍 Sede por confirmar, Lima

Mantente atento. En las próximas horas recibirás la logística que preparará tu mente y cuerpo para esta experiencia transformadora.

Tu Coordinadora: {cc_nombre}
📞 {cc_tel}

Responde para validar que estás en el juego:
ESTOY EN LA CANCHA

Crear Poder Sin Límites Perú""",
        "sms": "{nombre}, el Equipo 28 te espera este 29 de mayo. Es momento de redescubrir tu poder. ¿Estás en la cancha? Responde: ESTOY EN LA CANCHA"
    }
}

# ============================================================
# SQL HELPERS — COMPATIBILIDAD UNIVERSAL
# ============================================================
def execute_query(sql, params=None, fetch_one=False):
    """Ejecuta una consulta SQL detectando automáticamente si es Postgres o SQLite."""
    with db_session() as conn:
        c = conn.cursor()
        placeholder = '%s' if hasattr(conn, 'cursor_factory') else '?'
        final_sql = sql.replace('?', placeholder)
        
        c.execute(final_sql, params or ())
        
        if fetch_one:
            row = c.fetchone()
            if not row: return None
            # Soporte para Row objects de SQLite o dicts de Postgres
            if hasattr(row, 'keys'): return dict(row)
            cols = [desc[0] for desc in c.description]
            return dict(zip(cols, row))
        
        rows = c.fetchall()
        if not rows: return []
        if hasattr(rows[0], 'keys'): return [dict(r) for r in rows]
        cols = [desc[0] for desc in c.description]
        return [dict(zip(cols, r)) for r in rows]

# ============================================================
# API ENDPOINTS
# ============================================================

@app.on_event("startup")
async def startup():
    """Tarea de inicio: inicializa la DB, carga datos y registra el arranque."""
    init_db()
    cargar_datos_reales()
    registrar_caja_negra("SYSTEM", "STARTUP", "Torre de Control iniciada")

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Sirve el dashboard premium de la aplicación."""
    with open(os.path.join(os.path.dirname(__file__), "templates", "dashboard_premium.html"), "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/stats")
async def get_stats():
    """KPIs en tiempo real con seguridad NULL."""
    def q_val(sql):
        res = execute_query(sql, fetch_one=True)
        return list(res.values())[0] if res else 0

    return {
        "total_participantes": q_val("SELECT COUNT(*) FROM usuarios"),
        "total_aptos": q_val("SELECT COUNT(*) FROM usuarios WHERE graduado = 0"),
        "total_graduados": q_val("SELECT COUNT(*) FROM usuarios WHERE graduado = 1"),
        "total_decisiones": q_val("SELECT COUNT(*) FROM decisiones_ia"),
        "reputacion_gmail": q_val("SELECT (100 - bounces_recientes) FROM reputacion_canales WHERE canal='GMAIL'"),
        "envios_hoy": q_val("SELECT envios_dia FROM reputacion_canales WHERE canal='GMAIL'"),
        "bloqueos_forenses": q_val("SELECT COUNT(*) FROM trazabilidad_px WHERE tipo_evento='BOUNCE'"),
        "hora_actual": datetime.now().strftime("%H:%M"),
        "envio_permitido": es_horario_permitido()
    }

@app.get("/api/decisiones")
async def get_decisiones():
    """Ultimas decisiones de la IA para el panel visual."""
    sql = "SELECT entidad_id as px_id, agente, decision, justificacion, timestamp FROM decisiones_ia ORDER BY id DESC LIMIT 10"
    return execute_query(sql)

@app.get("/api/buscar")
async def buscar_participante(q: str = Query(..., min_length=2)):
    """Buscador optimizado con soporte NULL-safe y Ranking."""
    sql = """
        SELECT id, nombre, apellido, telefono, email, equipo, c1, c2, maestria, imo, tel_imo
        FROM participantes
        WHERE (LOWER(COALESCE(nombre, '')) || ' ' || LOWER(COALESCE(apellido, ''))) LIKE LOWER(?)
           OR telefono LIKE ?
           OR email LIKE ?
           OR equipo LIKE ?
           OR LOWER(COALESCE(imo, '')) LIKE LOWER(?)
        ORDER BY 
          CASE WHEN (LOWER(COALESCE(nombre, '')) || ' ' || LOWER(COALESCE(apellido, ''))) LIKE LOWER(?) THEN 0 ELSE 1 END,
          id DESC
        LIMIT 50
    """
    sv = f"%{q}%"
    st = f"{q}%"
    results = execute_query(sql, (sv, sv, sv, sv, sv, st))
    registrar_caja_negra("BUSQUEDA", "BUSCAR_PX", f"Búsqueda: '{q}' -> {len(results)} resultados")
    return results

@app.get("/api/pendientes")
async def pendientes_coordinadoras(cc: str = Query(None), entrenamiento: str = Query(None)):
    sql = """
        SELECT id, nombre, apellido, telefono, equipo, cc_nombre, c1, c2, tipo, estado
        FROM participantes 
        WHERE cc_nombre != '' AND cc_nombre IS NOT NULL
          AND (LOWER(cc_nombre) LIKE '%joyce%' OR LOWER(cc_nombre) LIKE '%diana%')
          AND NOT (c1 = 'SI' AND c2 = 'SI')
          AND COALESCE(es_pendiente_real, 'SI') = 'SI'
    """
    params = []
    if cc:
        sql += " AND LOWER(cc_nombre) LIKE ?"
        params.append(f"%{cc.lower()}%")
    if entrenamiento == "C1": sql += " AND c1 = 'NO'"
    elif entrenamiento == "C2": sql += " AND c1 = 'SI' AND c2 = 'NO'"
    
    sql += " ORDER BY cc_nombre, equipo, apellido LIMIT 500"
    return execute_query(sql, params)

@app.get("/api/participante/{px_id}")
async def detalle_participante(px_id: int):
    px = execute_query("SELECT * FROM participantes WHERE id = ?", (px_id,), fetch_one=True)
    if not px: return JSONResponse(status_code=404, content={"error": "PX no encontrado"})
    
    comms = execute_query("SELECT * FROM comunicaciones WHERE px_id = ? ORDER BY fecha_programada DESC", (px_id,))
    logs = execute_query("SELECT * FROM caja_negra WHERE px_nombre LIKE ? ORDER BY timestamp DESC LIMIT 20", (f"%{px['nombre']}%",))
    
    alertas = []
    if es_cc_bloqueada(px.get('cc_nombre')): alertas.append("⚠️ CC BLOQUEADA")
    if px.get('c1') == 'SI' and px.get('c2') == 'SI': alertas.append("✅ GRADUADO")
    
    return {"participante": px, "comunicaciones": comms, "historial": logs, "alertas": alertas}

@app.get("/api/stats/imo")
async def get_imo_stats():
    sql = """
        SELECT imo as nombre_imo, COUNT(*) as total_enrolados,
               SUM(CASE WHEN c1 = 'SI' THEN 1 ELSE 0 END) as sentados_c1,
               SUM(CASE WHEN c2 = 'SI' THEN 1 ELSE 0 END) as sentados_c2,
               SUM(CASE WHEN maestria = 'SI' THEN 1 ELSE 0 END) as graduados_mj
        FROM participantes
        WHERE imo IS NOT NULL AND imo != ''
        GROUP BY imo ORDER BY total_enrolados DESC LIMIT 100
    """
    return execute_query(sql)

@app.get("/api/caja_negra")
async def ver_caja_negra(limit: int = Query(50)):
    return execute_query("SELECT timestamp, categoria as tipo, evento as accion, detalle, estado as resultado FROM logs ORDER BY id DESC LIMIT ?", (limit,))

@app.get("/api/plantillas")
async def listar_plantillas():
    return {k: {"asunto": v["asunto"], "sms": v["sms"]} for k, v in PLANTILLAS.items()}

@app.get("/api/desertores")
async def listar_desertores(equipo: str = Query(None)):
    sql = "SELECT * FROM desertores"
    params = []
    if equipo:
        sql += " WHERE equipo LIKE ?"
        params.append(f"%{equipo}%")
    return execute_query(sql + " ORDER BY equipo, nombre", params)

@app.get("/api/salud")
async def salud_sistema():
    def q_val(sql):
        res = execute_query(sql, fetch_one=True)
        return list(res.values())[0] if res else 0

    return {
        "estado": "OPERATIVO",
        "total_px": q_val("SELECT COUNT(*) FROM participantes"),
        "sin_cc": q_val("SELECT COUNT(*) FROM participantes WHERE COALESCE(cc_nombre, '') = ''"),
        "graduados": q_val("SELECT COUNT(*) FROM participantes WHERE c1='SI' AND c2='SI'"),
        "envio_permitido": es_horario_permitido()
    }

# ============================================================
# ARRANQUE
# ============================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  TORRE DE CONTROL CPSL LIMA")
    print("  Auditoría aplicada: Fase 1 + Fase 2")
    print("  http://localhost:10000")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=10000)
