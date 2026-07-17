"""
TASK SCHEDULER V2.1 — ORCHESTRATION & MONITORING FRAMEWORK
=========================================================
Unifies all scheduling mechanisms across Local and Cloud-native environments.
Supports:
1. One-shot execution of specific pipelines/scripts.
2. Background daemon processing (with APScheduler or thread-based loop fallback).
3. Status logging to the 'logs' table (Caja Negra) using SQLAlchemy/SQLite.
4. FastAPI endpoints integration for remote triggering and monitoring.
"""

import os
import sys
import time
import argparse
import subprocess
import logging
from datetime import datetime
import threading
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURACIÓN DE LOGS DE CONSOLA/ARCHIVO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULER_LOG_FILE = os.path.join(BASE_DIR, "task_scheduler.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(SCHEDULER_LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger("TaskSchedulerV2.1")

# --- MAPPING DE BASE DE DATOS ---
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    # Si no hay env var, busca localmente caja_negra.db
    db_file = os.path.join(BASE_DIR, "caja_negra.db")
    DATABASE_URL = f"sqlite:///{db_file}"

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Inicializar motor de base de datos de manera segura
try:
    if "sqlite" in DATABASE_URL:
        engine = create_engine(DATABASE_URL, connect_args={"timeout": 60})
    else:
        engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10, pool_pre_ping=True)
except Exception as e:
    logger.error(f"Error inicializando SQLAlchemy engine: {e}")
    engine = None

def ensure_logs_table(conn):
    """Asegura que la tabla logs existe en la base de datos, soportando SQLite y PostgreSQL."""
    if "postgresql" in DATABASE_URL:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS logs (
                id SERIAL PRIMARY KEY,
                timestamp VARCHAR(50),
                categoria VARCHAR(100),
                evento VARCHAR(100),
                detalle TEXT,
                estado VARCHAR(50)
            )
        """))
    else:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                categoria TEXT,
                evento TEXT,
                detalle TEXT,
                estado TEXT
            )
        """))

def registrar_log_db(categoria, evento, detalle, estado="OK"):
    """Registra el resultado de la tarea en la Caja Negra (tabla 'logs')."""
    if not engine:
        logger.warning("DB Engine no disponible. Omitiendo registro en log de DB.")
        return

    query = """
        INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
        VALUES (:timestamp, :categoria, :evento, :detalle, :estado)
    """
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Recortar detalles muy largos para evitar desbordar campos
    detalle_truncado = str(detalle)[:500]

    try:
        with engine.connect() as conn:
            ensure_logs_table(conn)
            conn.commit()
            
            conn.execute(text(query), {
                "timestamp": ts,
                "categoria": categoria,
                "evento": evento,
                "detalle": detalle_truncado,
                "estado": estado
            })
            conn.commit()
    except Exception as e:
        logger.error(f"Fallo al registrar log en DB: {e}")

def is_script_already_running(script_name):
    """Verifica si ya existe un proceso de Python ejecutando el script especificado."""
    try:
        import psutil
        my_pid = os.getpid()
        my_ppid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                if name and 'python' in name.lower():
                    pid = proc.info['pid']
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if pid != my_pid and pid != my_ppid and script_name in cmdline_str and "task_scheduler_v2_1.py" not in cmdline_str:
                            logger.warning(f"Conflicto de script encontrado: {script_name} ya corre en PID {pid} ({cmdline_str})")
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except Exception as e:
        logger.error(f"Error comprobando si {script_name} está en ejecución: {e}")
        return False

def is_daemon_already_running():
    """Verifica si ya existe una instancia de task_scheduler_v2_1.py con --daemon."""
    try:
        import psutil
        my_pid = os.getpid()
        my_ppid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                if name and 'python' in name.lower():
                    pid = proc.info['pid']
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if pid != my_pid and pid != my_ppid and "task_scheduler_v2_1.py" in cmdline_str and "--daemon" in cmdline_str:
                            logger.warning(f"Conflicto de demonio encontrado: el scheduler ya corre en PID {pid} ({cmdline_str})")
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except Exception as e:
        logger.error(f"Error comprobando si el demonio ya está en ejecución: {e}")
        return False

# --- ENCAPSULACIÓN DE EJECUCIÓN DE SCRIPTS LOCALES ---
def ejecutar_script_python(nombre_script):
    """Ejecuta un script de Python de forma local y devuelve (éxito, logs)."""
    script_path = os.path.join(BASE_DIR, nombre_script)
    if not os.path.exists(script_path):
        return False, f"Script {nombre_script} no encontrado en {script_path}"
        
    if is_script_already_running(nombre_script):
        msg = f"El script {nombre_script} ya está en ejecución en otro proceso. Omitiendo ejecución para evitar duplicidad."
        logger.warning(msg)
        return False, msg
    
    logger.info(f"Iniciando ejecución de {nombre_script}...")
    try:
        # Ejecuta usando el mismo python running actual
        res = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="latin1",
            timeout=900 # Timeout de 15 minutos para evitar bloqueos
        )
        if res.returncode == 0:
            logger.info(f"Completado exitosamente: {nombre_script}")
            return True, res.stdout
        else:
            logger.error(f"Error ({res.returncode}) en {nombre_script}: {res.stderr}")
            return False, res.stderr
    except Exception as e:
        logger.error(f"Excepción ejecutando {nombre_script}: {e}")
        return False, str(e)

# --- DEFINICIÓN DE TAREAS OPERATIVAS ---
def task_daily_pipeline():
    """Ejecuta la secuencia completa de sanación y preparación diaria."""
    logger.info("--- [INICIO] TAREA: PIPELINE DIARIO ---")
    registrar_log_db("SCHEDULER", "DAILY_PIPELINE_START", "Iniciando secuencia de 7 scripts de sanación y preparación.")
    
    pipeline = [
        "sanar_caja_negra.py",
        "sanar_logica_jerarquia.py",
        "actualizar_memoria_caja_negra.py",
        "sanar_imo_enrolados.py",
        "procesar_cambios_cupo.py",
        "rescate_imos.py",
        "agenda_mañana_8am.py"
    ]
    
    res_list = []
    failed = False
    
    for script in pipeline:
        ok, out = ejecutar_script_python(script)
        res_list.append(f"{script}: {'OK' if ok else 'FALLIDO'}")
        if not ok:
            failed = True
            registrar_log_db("SCHEDULER", "DAILY_PIPELINE_STEP_FAIL", f"Fallo en paso {script}. Detalle: {out[:200]}", "FAILED")
            break
            
    summary = ", ".join(res_list)
    if failed:
        logger.error(f"Daily pipeline falló en alguno de sus pasos: {summary}")
        registrar_log_db("SCHEDULER", "DAILY_PIPELINE_END", f"Pipeline diario cancelado por errores: {summary}", "FAILED")
    else:
        logger.info(f"Daily pipeline completado con éxito: {summary}")
        registrar_log_db("SCHEDULER", "DAILY_PIPELINE_END", f"Pipeline diario finalizado con éxito: {summary}", "SUCCESS")

def task_monitor_cycle():
    """Ejecuta el escaneo de Gmail para bounces y respuestas de SMS."""
    logger.info("--- [INICIO] TAREA: MONITOREO DE 4 HORAS (SMS & BOUNCES) ---")
    registrar_log_db("SCHEDULER", "MONITOR_4H_START", "Escaneando rebotes de correo y respuestas de SMS.")
    
    ok, out = ejecutar_script_python("ciclo_4h_monitor.py")
    if ok:
        registrar_log_db("SCHEDULER", "MONITOR_4H_END", f"Monitoreo finalizado. Detalle: {out[:200]}", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "MONITOR_4H_END", f"Fallo en monitoreo. Detalle: {out[:200]}", "FAILED")

def task_sincronizacion_12h():
    """Sincroniza el estatus local de los participantes con OneDrive."""
    logger.info("--- [INICIO] TAREA: SINCRONIZACIÓN MAESTRA DE ESTATUS (12H) ---")
    registrar_log_db("SCHEDULER", "SYNC_12H_START", "Iniciando cruce y descarga de OneDrive (C1, C2, MJ, Graduados).")
    
    ok, out = ejecutar_script_python("sincronizar_estatus_db.py")
    if ok:
        registrar_log_db("SCHEDULER", "SYNC_12H_END", "Sincronización completada correctamente.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "SYNC_12H_END", f"Fallo de sincronización. Detalle: {out[:200]}", "FAILED")

def task_sync_crearpsl():
    """Sincroniza los endpoints web de CrearPSL a Google Sheets."""
    logger.info("--- [INICIO] TAREA: SCRAPE WEB Y SYNC GOOGLE SHEETS (30 MIN) ---")
    registrar_log_db("SCHEDULER", "SYNC_CREARPSL_START", "Ejecutando volcado de endpoints web php a Google Sheets.")
    
    ok, out = ejecutar_script_python("sync_crearpsl.py")
    if ok:
        registrar_log_db("SCHEDULER", "SYNC_CREARPSL_END", "Sincronización a Sheets realizada con éxito.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "SYNC_CREARPSL_END", f"Fallo en sync a Sheets. Detalle: {out[:200]}", "FAILED")

def task_reporte_gestion():
    """Genera el reporte de gestión por equipos de forma horaria."""
    logger.info("--- [INICIO] TAREA: REPORTE HORARIO DE GESTIÓN ---")
    registrar_log_db("SCHEDULER", "REPORTE_1H_START", "Generando reporte de gestión por equipos con Playwright.")
    
    ok, out = ejecutar_script_python("reporte_gestion_equipos.py")
    if ok:
        registrar_log_db("SCHEDULER", "REPORTE_1H_END", "Reporte de gestión guardado en Excel.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "REPORTE_1H_END", f"Fallo en reporte de gestión. Detalle: {out[:200]}", "FAILED")

def task_asistencia_e28():
    """Realiza la extracción del reporte definitivo de asistencia para el Equipo 28."""
    logger.info("--- [INICIO] TAREA: SCRAPER ASISTENCIA REAL E28 (12H) ---")
    registrar_log_db("SCHEDULER", "ASISTENCIA_12H_START", "Actualizando asistencia de E28 con la fuente real.")
    
    ok, out = ejecutar_script_python("scraper_asistencia_real_e28.py")
    if ok:
        registrar_log_db("SCHEDULER", "ASISTENCIA_12H_END", "Asistencia de Equipo 28 sincronizada.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "ASISTENCIA_12H_END", f"Fallo en scraper de asistencia. Detalle: {out[:200]}", "FAILED")

def task_vigilante_aliados_completo():
    """Ejecuta el agente vigilante de aliados completo (C1 y C2)."""
    logger.info("--- [INICIO] TAREA: VIGILANTE ALIADOS COMPLETO (C1 Y C2) ---")
    registrar_log_db("SCHEDULER", "VIGILANTE_ALIADOS_COMPLETO_START", "Ejecutando script de sincronización unificada de aliados C1 y C2.")
    
    ok, out = ejecutar_script_python("agente_vigilante_aliados_completo.py")
    if ok:
        registrar_log_db("SCHEDULER", "VIGILANTE_ALIADOS_COMPLETO_END", f"Sincronización de aliados C1 y C2 completada.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "VIGILANTE_ALIADOS_COMPLETO_END", f"Fallo en sincronización de aliados C1 y C2. Detalle: {out[:200]}", "FAILED")

def task_vigilante_graduados_completo():
    """Ejecuta el agente vigilante de graduados y staff completo."""
    logger.info("--- [INICIO] TAREA: VIGILANTE GRADUADOS Y STAFF COMPLETO ---")
    registrar_log_db("SCHEDULER", "VIGILANTE_GRADUADOS_Y_STAFF_START", "Ejecutando script de normalización de graduados e historial de staff.")
    
    ok, out = ejecutar_script_python("agente_vigilante_graduados_completo.py")
    if ok:
        registrar_log_db("SCHEDULER", "VIGILANTE_GRADUADOS_Y_STAFF_END", f"Sincronización de graduados y staff completada.", "SUCCESS")
    else:
        registrar_log_db("SCHEDULER", "VIGILANTE_GRADUADOS_Y_STAFF_END", f"Fallo en sincronización de graduados y staff. Detalle: {out[:200]}", "FAILED")

def task_organizar_descargas():
    """Ejecuta el script de organización de descargas."""
    logger.info("--- [INICIO] TAREA: ORGANIZADOR DE DESCARGAS ---")
    registrar_log_db("SCHEDULER", "ORGANIZAR_DESCARGAS_START", "Ejecutando script de organización de Downloads.")
    
    script_path = os.path.join(os.path.dirname(BASE_DIR), "Código y Scripts", "organizar_carpeta.py")
    if not os.path.exists(script_path):
        msg = f"Script no encontrado en {script_path}"
        logger.error(msg)
        registrar_log_db("SCHEDULER", "ORGANIZAR_DESCARGAS_END", msg, "FAILED")
        return
        
    logger.info(f"Iniciando ejecución de organizar_carpeta.py...")
    try:
        res = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=300
        )
        if res.returncode == 0:
            logger.info("Completado exitosamente: organizar_carpeta.py")
            registrar_log_db("SCHEDULER", "ORGANIZAR_DESCARGAS_END", "Organización de descargas realizada con éxito.", "SUCCESS")
        else:
            logger.error(f"Error ({res.returncode}) en organizar_carpeta.py: {res.stderr}")
            registrar_log_db("SCHEDULER", "ORGANIZAR_DESCARGAS_END", f"Error en organización. Detalle: {res.stderr[:200]}", "FAILED")
    except Exception as e:
        logger.error(f"Excepción ejecutando organizar_carpeta.py: {e}")
        registrar_log_db("SCHEDULER", "ORGANIZAR_DESCARGAS_END", f"Fallo al ejecutar. Detalle: {str(e)[:200]}", "FAILED")

def task_optimizador_zoom():
    """Asegura que el optimizador de recursos de Zoom esté en ejecución."""
    logger.info("--- [INICIO] TAREA: OPTIMIZADOR ZOOM ---")
    
    if is_script_already_running("zoom_optimizer.py"):
        logger.info("El optimizador de Zoom ya está en ejecución.")
        return
        
    logger.info("El optimizador de Zoom no está corriendo. Iniciándolo...")
    optimizer_path = os.path.join(os.path.dirname(BASE_DIR), "ZoomOptimizer", "zoom_optimizer.py")
    if not os.path.exists(optimizer_path):
        logger.error(f"No se encontró el script de ZoomOptimizer en {optimizer_path}")
        registrar_log_db("SCHEDULER", "ZOOM_OPTIMIZER_ERROR", f"No se encontró el script en {optimizer_path}", "FAILED")
        return
        
    pythonw_path = "C:\\Users\\josem\\AppData\\Local\\Python\\pythoncore-3.14-64\\pythonw.exe"
    if not os.path.exists(pythonw_path):
        pythonw_path = "pythonw"
        
    try:
        subprocess.Popen([pythonw_path, optimizer_path], creationflags=0x08000000, cwd=os.path.dirname(optimizer_path))
        logger.info(f"ZoomOptimizer iniciado en segundo plano usando {pythonw_path}")
        registrar_log_db("SCHEDULER", "ZOOM_OPTIMIZER_START", "Optimizador de Zoom iniciado en segundo plano.", "SUCCESS")
    except Exception as e:
        logger.error(f"Error al iniciar ZoomOptimizer: {e}")
        registrar_log_db("SCHEDULER", "ZOOM_OPTIMIZER_ERROR", f"Error al iniciar: {e}", "FAILED")

# --- REPOSITORIO DE TAREAS MAPEADO ---
TAREAS = {
    "daily_pipeline": {
        "func": task_daily_pipeline,
        "desc": "Pipeline diario (Sanación de caja negra, lógica jerárquica, cambios de cupo, rescates, agenda)",
        "default_schedule": {"trigger": "cron", "hour": 7, "minute": 45} # 7:45 AM Lima
    },
    "monitor_cycle": {
        "func": task_monitor_cycle,
        "desc": "Monitoreo cada 4 horas de correos Gmail, buscando rebotes y respuestas de SMS",
        "default_schedule": {"trigger": "interval", "hours": 4}
    },
    "sincronizacion_12h": {
        "func": task_sincronizacion_12h,
        "desc": "Sincronizador maestro local OneDrive (Carpeta Aliados, MJ, Graduados) a torre_control.db",
        "default_schedule": {"trigger": "interval", "hours": 12}
    },
    "sync_crearpsl": {
        "func": task_sync_crearpsl,
        "desc": "Scrape de PHP Admin y volcado a Google Sheets",
        "default_schedule": {"trigger": "interval", "minutes": 30}
    },
    "reporte_gestion": {
        "func": task_reporte_gestion,
        "desc": "Scrape Playwright de reportes IMO por equipo",
        "default_schedule": {"trigger": "interval", "hours": 1}
    },
    "asistencia_e28": {
        "func": task_asistencia_e28,
        "desc": "Scraper de Asistencia definitiva del Equipo 28",
        "default_schedule": {"trigger": "interval", "hours": 12}
    },
    "vigilante_aliados_completo": {
        "func": task_vigilante_aliados_completo,
        "desc": "Supervisor y sincronizador horario de relaciones de aliados C1 y C2 en OneDrive",
        "default_schedule": {"trigger": "interval", "hours": 1}
    },
    "vigilante_graduados_completo": {
        "func": task_vigilante_graduados_completo,
        "desc": "Agente normalizador de graduados e historial de staff (visibles y ocultas) en OneDrive",
        "default_schedule": {"trigger": "interval", "hours": 24}
    },
    "organizar_descargas": {
        "func": task_organizar_descargas,
        "desc": "Organizador periódico de la carpeta Downloads de Windows",
        "default_schedule": {"trigger": "interval", "hours": 4}
    },
    "optimizador_zoom": {
        "func": task_optimizador_zoom,
        "desc": "Asegura que el optimizador de recursos de Zoom esté en ejecución",
        "default_schedule": {"trigger": "interval", "minutes": 5}
    }
}

# --- REGISTRO DINÁMICO DE TAREAS ---
def registrar_tarea(nombre: str, func, desc: str, schedule: dict):
    """
    Permite registrar tareas dinámicas en tiempo de ejecución (por ejemplo, desde main.py).
    """
    TAREAS[nombre] = {
        "func": func,
        "desc": desc,
        "default_schedule": schedule
    }
    logger.info(f"Tarea dinámica registrada en el orquestador: {nombre} ({desc})")

# --- CONTROLADORES DEL SCHEDULER ACTIVO ---
class UnifiedScheduler:
    def __init__(self):
        self.scheduler = None
        self._init_backend()

    def _init_backend(self):
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
            self.scheduler = BackgroundScheduler()
            logger.info("Scheduler Backend: APScheduler inicializado.")
        except ImportError:
            logger.warning("APScheduler no está instalado. Se utilizará el loop de fallback.")
            self.scheduler = None

    def start(self, blocking=True):
        if self.scheduler:
            # Registrar trabajos en APScheduler
            for name, task in TAREAS.items():
                sched = task["default_schedule"]
                if sched["trigger"] == "cron":
                    self.scheduler.add_job(
                        task["func"], 
                        'cron', 
                        hour=sched.get("hour"), 
                        minute=sched.get("minute"),
                        id=name,
                        coalesce=True,
                        misfire_grace_time=None
                    )
                elif sched["trigger"] == "interval":
                    self.scheduler.add_job(
                        task["func"], 
                        'interval', 
                        hours=sched.get("hours", 0), 
                        minutes=sched.get("minutes", 0),
                        id=name,
                        coalesce=True,
                        misfire_grace_time=None
                    )
            self.scheduler.start()
            logger.info("APScheduler iniciado.")
            registrar_log_db("SCHEDULER", "START", "Orquestador de Tareas (UnifiedScheduler) iniciado correctamente.", "SUCCESS")
            
            if blocking:
                # Mantener vivo el hilo principal
                try:
                    while True:
                        time.sleep(1)
                except (KeyboardInterrupt, SystemExit):
                    self.scheduler.shutdown()
        else:
            if blocking:
                self._start_fallback_loop()
            else:
                t = threading.Thread(target=self._start_fallback_loop, daemon=True, name="fallback_scheduler_loop")
                t.start()

    def _start_fallback_loop(self):
        logger.info("Iniciando loop de fallback básico (monitoreo de tiempos)...")
        # Estructura simple para almacenar la última vez que corrió cada tarea
        last_runs = {name: 0.0 for name in TAREAS}
        
        # Al arrancar, si es necesario, podemos forzar alguna corrida o esperar el intervalo
        try:
            while True:
                ahora = time.time()
                for name, task in TAREAS.items():
                    sched = task["default_schedule"]
                    if sched["trigger"] == "interval":
                        # Convertir a segundos
                        intervalo_seg = sched.get("hours", 0) * 3600 + sched.get("minutes", 0) * 60
                        if ahora - last_runs[name] >= intervalo_seg:
                            # Lanzar en un hilo nuevo para no congelar el loop
                            threading.Thread(target=task["func"]).start()
                            last_runs[name] = ahora
                    elif sched["trigger"] == "cron":
                        # Simular cron diario básico a la hora indicada (Lima aprox)
                        ahora_dt = datetime.now()
                        if ahora_dt.hour == sched.get("hour") and ahora_dt.minute == sched.get("minute"):
                            # Ejecutar una vez en esta ventana de minuto
                            if ahora - last_runs[name] > 120: 
                                threading.Thread(target=task["func"]).start()
                                last_runs[name] = ahora
                
                time.sleep(30)
        except (KeyboardInterrupt, SystemExit):
            logger.info("Deteniendo loop de fallback...")


# --- INTEGRACIÓN CON FASTAPI (DASHBOARD ENDPOINTS) ---
def register_scheduler_endpoints(app):
    """
    Registra endpoints en una aplicación FastAPI existente 
    para poder auditar y disparar tareas desde la web o webhook.
    """
    from fastapi import BackgroundTasks
    
    @app.get("/scheduler/status")
    def get_scheduler_status():
        history = []
        if engine:
            try:
                with engine.connect() as conn:
                    res = conn.execute(text("""
                        SELECT timestamp, categoria, evento, detalle, estado 
                        FROM logs 
                        WHERE categoria = 'SCHEDULER' 
                        ORDER BY id DESC LIMIT 20
                    """))
                    for row in res:
                        # Soporta tupla ordinaria o mapeada
                        history.append({
                            "timestamp": row[0],
                            "categoria": row[1],
                            "evento": row[2],
                            "detalle": row[3],
                            "estado": row[4]
                        })
            except Exception as e:
                history = [f"Error leyendo historial: {e}"]
        
        # Preparar info de tareas disponibles
        tasks_info = {name: {"description": info["desc"], "schedule": info["default_schedule"]} for name, info in TAREAS.items()}
        
        return {
            "status": "OPERATIONAL",
            "backend": "APScheduler" if "apscheduler" in sys.modules else "Fallback Loop",
            "tasks_registered": list(TAREAS.keys()),
            "tasks_details": tasks_info,
            "recent_executions": history
        }

    @app.post("/scheduler/trigger/{task_name}")
    def trigger_scheduler_task(task_name: str, bg_tasks: BackgroundTasks):
        if task_name not in TAREAS:
            return {"status": "ERROR", "message": f"Tarea '{task_name}' no registrada."}
        
        # Encolar en segundo plano de FastAPI
        bg_tasks.add_task(TAREAS[task_name]["func"])
        return {"status": "TRIGGERED", "message": f"Tarea '{task_name}' iniciada en segundo plano."}

# --- CLI ENTRYPOINT ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="CREAR GLOBAL — Unified Task Scheduler V2.1")
    parser.add_argument("--daemon", action="store_true", help="Iniciar scheduler continuo en segundo plano.")
    parser.add_argument("--run", type=str, choices=list(TAREAS.keys()), help="Ejecutar una tarea específica inmediatamente y salir.")
    parser.add_argument("--list", action="store_true", help="Listar todas las tareas registradas con su cronograma.")
    parser.add_argument("--status", action="store_true", help="Mostrar el estado de las últimas ejecuciones registradas en DB.")
    
    args = parser.parse_args()
    
    if args.list:
        print("="*80)
        print(" TAREAS DISPONIBLES EN TASK SCHEDULER V2.1")
        print("="*80)
        for name, task in TAREAS.items():
            print(f"- NOMBRE: {name}")
            print(f"  Descripción: {task['desc']}")
            print(f"  Programación: {task['default_schedule']}")
            print("-"*80)
            
    elif args.status:
        print("="*80)
        print(" HISTORIAL DE EJECUCIONES RECUPERADO DE LA CAJA NEGRA")
        print("="*80)
        if engine:
            try:
                with engine.connect() as conn:
                    ensure_logs_table(conn)
                    conn.commit()
                    res = conn.execute(text("""
                        SELECT timestamp, evento, estado, detalle 
                        FROM logs 
                        WHERE categoria = 'SCHEDULER' 
                        ORDER BY id DESC LIMIT 15
                    """))
                    found = False
                    for row in res:
                        found = True
                        print(f"[{row[0]}] {row[1]} -> Estado: {row[2]}")
                        print(f"      Detalle: {row[3]}")
                        print("-"*80)
                    if not found:
                        print("No se encontraron registros de ejecuciones del scheduler.")
            except Exception as ex:
                print(f"Error consultando la base de datos: {ex}")
        else:
            print("No se pudo conectar a la base de datos.")
            
    elif args.run:
        task_name = args.run
        logger.info(f"Trigger manual unitario: {task_name}")
        TAREAS[task_name]["func"]()
        
    elif args.daemon:
        if is_daemon_already_running():
            logger.error("El demonio del Task Scheduler ya se encuentra en ejecución en otro proceso. Cancelando inicio.")
            sys.exit(1)
        logger.info("Iniciando modo demonio persistente...")
        scheduler = UnifiedScheduler()
        scheduler.start()
        
    else:
        parser.print_help()
