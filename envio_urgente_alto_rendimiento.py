import requests
import sqlite3
import time
from datetime import datetime
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

# Gateway Config
MACRODROID_URL = "https://trigger.macrodroid.com/7c051b6b-4231-4c86-8b98-2d9ccc88ccf7/sms_crear"

def registrar_log(px_nombre, tel, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    full_detalle = f"PX: {px_nombre} ({tel}) - {detalle}"
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "SMS_URGENTE", "ENVIO_ALTO_RENDIMIENTO", full_detalle, estado))
    conn.commit()
    conn.close()

def enviar_sms(nombre, tel, cc_nombre):
    msg = f"Hola {nombre}, soy {cc_nombre} de CPSL. El Alto Rendimiento no espera a los que dudan. Hoy cerramos cupos. Tu transformacion vale mas que cualquier excusa. Confirma ahora. ¡Vamos con todo!"
    params = {"numero": tel, "mensaje": msg}
    try:
        r = requests.get(MACRODROID_URL, params=params, timeout=10)
        print(f"SMS ENVIADO: A: {nombre} ({tel}) | Status: {r.status_code}")
        return True
    except Exception as e:
        print(f"ERROR enviando a {tel}: {e}")
        return False

def lanzar_campaña():
    print("--- INICIANDO CAMPAÑA DE ALTO RENDIMIENTO (URGENTE) ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # OBJETIVO PURIFICADO: Rezagados C1 Aptos Reales
    # Excluyendo Devoluciones, Sin Interés y Desertores
    c.execute("""
        SELECT nombre, telefono, cc_nombre 
        FROM participantes 
        WHERE c1 = 'NO' 
          AND es_pendiente_real = 'SI'
          AND cc_nombre IN ('Diana Moscoso', 'Joyce Marín')
          AND telefono != ''
          AND (resultado_gestion IS NULL 
               OR (resultado_gestion NOT LIKE '%INTERES%' 
                   AND resultado_gestion NOT LIKE '%DEVOLU%' 
                   AND resultado_gestion NOT LIKE '%REEMBOL%' 
                   AND resultado_gestion NOT LIKE '%DESERTOR%'
                   AND resultado_gestion NOT LIKE '%NO DESEA%'))
    """)
    
    objetivos = c.fetchall()
    print(f"Total objetivos en esta tanda: {len(objetivos)}")
    
    import random
    
    count = 0
    for nombre, tel, cc in objetivos:
        if enviar_sms(nombre, tel, cc):
            c.execute("UPDATE participantes SET resultado_gestion = 'SMS_ALTO_RENDIMIENTO_ENVIADO', fecha_ultima_interaccion = ? WHERE telefono = ?", 
                      (datetime.now().strftime('%Y-%m-%d'), tel))
            registrar_log(nombre, tel, "SMS Alto Rendimiento enviado vía MacroDroid")
            
            count += 1
            # Delay humano aleatorio entre mensajes (7 a 12 segundos)
            delay = random.uniform(7, 12)
            
            # Cada 15 mensajes, un micro-descanso de 1 a 2 minutos
            if count % 15 == 0:
                descanso = random.uniform(60, 120)
                print(f"PAUSA DE SEGURIDAD: Tomando un respiro de {int(descanso)} segundos para evitar bloqueo...")
                time.sleep(descanso)
            else:
                time.sleep(delay)
            
    conn.commit()
    conn.close()
    print("--- CAMPAÑA FINALIZADA ---")

if __name__ == "__main__":
    lanzar_campaña()
