import requests
import sqlite3
import time
import random
from datetime import datetime
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

# Gateway Config
MACRODROID_URL = "https://trigger.macrodroid.com/7c051b6b-4231-4c86-8b98-2d9ccc88ccf7/sms_crear"

def registrar_log_caja_negra(px_id, nombre, tel, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (timestamp, categoria, evento, detalle, estado) 
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "SMS_VALIDACION", "ENVIO_CORRECTIVO", 
          f"ID:{px_id} | PX:{nombre} | TEL:{tel} | {detalle}", estado))
    conn.commit()
    conn.close()

def enviar_sms_validacion(nombre, tel, cc_nombre, cc_tel):
    # Plantilla Solicitada por el Usuario
    msg = (f"Hola {nombre}, habla el equipo de Crear Poder Sin Limites Peru.\n\n"
           "Estamos actualizando la informacion de participacion para proximos entrenamientos "
           "y detectamos que algunos datos podrian requerir validacion o actualizacion.\n\n"
           "Por favor responder:\n1. Nombre completo\n2. Correo actualizado\n3. Numero vigente\n\n"
           f"Coordinadora: {cc_nombre} ({cc_tel})\nGracias.")
    
    params = {"numero": tel, "mensaje": msg}
    try:
        r = requests.get(MACRODROID_URL, params=params, timeout=10)
        print(f"SMS VALIDACION ENVIADO: {nombre} ({tel}) | Status: {r.status_code}")
        return True
    except Exception as e:
        print(f"ERROR enviando validacion a {tel}: {e}")
        return False

def ejecutar_campaña_validacion():
    print("--- INICIANDO DESPACHO DE SMS DE VALIDACIÓN CORRECTIVA ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Seleccionar solo aquellos marcados como DUDOSO_RECUPERABLE en la auditoria anterior
    # y que no hayan recibido el SMS aun
    c.execute("""
        SELECT id, nombre, telefono, cc_nombre, cc_tel 
        FROM participantes 
        WHERE observaciones LIKE '%DUDOSO_RECUPERABLE%'
          AND resultado_gestion != 'SMS_VALIDACION_ENVIADO'
          AND telefono != ''
    """)
    
    objetivos = c.fetchall()
    print(f"Total objetivos de validación: {len(objetivos)}")
    
    count = 0
    for px_id, nombre, tel, cc_n, cc_t in objetivos:
        if enviar_sms_validacion(nombre, tel, cc_n, cc_t or "999888777"):
            # Actualizar DB Central
            c.execute("UPDATE participantes SET resultado_gestion = 'SMS_VALIDACION_ENVIADO' WHERE id = ?", (px_id,))
            registrar_log_caja_negra(px_id, nombre, tel, "SMS de Validación de Identidad enviado")
            
            count += 1
            # Ritmo Humano Anti-Bloqueo
            delay = random.uniform(8, 14)
            if count % 15 == 0:
                descanso = random.uniform(60, 150)
                print(f"PAUSA DE SEGURIDAD: {int(descanso)}s para proteger linea...")
                time.sleep(descanso)
            else:
                time.sleep(delay)
                
    conn.commit()
    conn.close()
    print("--- CAMPAÑA DE VALIDACIÓN FINALIZADA ---")

if __name__ == "__main__":
    ejecutar_campaña_validacion()
