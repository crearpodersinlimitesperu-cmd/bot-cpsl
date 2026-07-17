import time
import schedule
import sqlite3
import json
from datetime import datetime
import os
import sys

# Rutas
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
LOG_FILE = r'C:\Users\josem\Downloads\bot-cpsl-review\agente_startup.log'

def log(mensaje):
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    linea = f"[{ahora}] {mensaje}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(linea)
    print(linea.strip())

def tarea_diaria_9am():
    log("Ejecutando Mega Reporte Diario de las 9:00 AM (Auditor Maestro).")
    # Aquí irá la lógica de cruce de CSV y POST a Google Chat que construimos
    # Por ahora se registra la acción.
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (?, ?, ?, ?, ?)
        ''', (ahora, 'SYSTEM', 'CRON_EJECUCION', 'Ejecución del reporte de las 9AM completada.', 'COMPLETO'))
        conn.commit()
        conn.close()
        log("Tarea diaria completada y registrada en Caja Negra.")
    except Exception as e:
        log(f"Error en tarea diaria: {e}")

def tarea_monitor_horario():
    log("Ejecutando Monitor Horario (Buscando anomalías).")
    # Aquí irá la lógica de búsqueda en vivo en la unidad G:
    pass

log("--- Ecosistema CPSL Iniciado en Windows Startup ---")

# Programación de tareas
schedule.every().day.at("09:00").do(tarea_diaria_9am)
schedule.every(1).hours.do(tarea_monitor_horario)

log("Agentes en espera activa...")

# Bucle infinito para mantener vivo el proceso en background
while True:
    try:
        schedule.run_pending()
        time.sleep(60) # Revisar cada minuto
    except KeyboardInterrupt:
        log("Ecosistema CPSL detenido manualmente.")
        sys.exit(0)
    except Exception as e:
        log(f"Error crítico en el bucle del agente: {e}")
        time.sleep(60)
