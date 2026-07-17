import sqlite3
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import premium_templates as pt

# Configuración
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
LOG_DB = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
SMS_PENDING_FILE = r'C:\Users\josem\Downloads\bot-cpsl-review\sms_manana_8am.json'

def log_caja_negra(tipo, accion, detalle):
    try:
        conn = sqlite3.connect(LOG_DB, timeout=30.0)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)", 
                       (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), tipo, accion, detalle, 'PREPARADO'))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging to Caja Negra: {e}")

def preparar_agenda():
    print("--- PREPARANDO AGENDA PREMIUM MAÑANA 8 AM ---")
    if not os.path.exists(DB_PATH):
        print("DB no encontrada.")
        return

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    
    # 1. Rebotes (PX)
    query_rebotes = "SELECT nombre, telefono FROM participantes WHERE email = 'REBOTE' AND telefono IS NOT NULL"
    df_rebotes = pd.read_sql(query_rebotes, conn)
    
    # 2. IMOs de Rebotes
    query_imos = """
        SELECT DISTINCT imo as nombre_imo, tel_imo as telefono_imo, nombre as nombre_px 
        FROM participantes 
        WHERE email = 'REBOTE' AND tel_imo IS NOT NULL
    """
    df_imos = pd.read_sql(query_imos, conn)
    
    # 3. Confirmados (Muestra prioritaria para evitar saturación)
    # Seleccionamos los últimos 50 confirmados para no saturar el gateway de golpe
    query_confirmados = "SELECT nombre, telefono FROM participantes WHERE c1 = 'SI' AND telefono IS NOT NULL ORDER BY id DESC LIMIT 50"
    df_confirmados = pd.read_sql(query_confirmados, conn)
    
    conn.close()

    mensajes_pendientes = []

    # Generar mensajes para PX Rebote
    for _, row in df_rebotes.iterrows():
        msg = pt.get_message("BOUNCE_PX", nombre=row['nombre'])
        mensajes_pendientes.append({"telefono": row['telefono'], "mensaje": msg, "tipo": "REBOTE_PX"})

    # Generar mensajes para IMOs
    for _, row in df_imos.iterrows():
        msg = pt.get_message("BOUNCE_IMO", nombre_imo=row['nombre_imo'], nombre_px=row['nombre_px'])
        mensajes_pendientes.append({"telefono": row['telefono_imo'], "mensaje": msg, "tipo": "REBOTE_IMO"})

    # Generar mensajes para Confirmados
    for _, row in df_confirmados.iterrows():
        msg = pt.get_message("CONFIRMATION_RESPONSE", nombre=row['nombre'])
        mensajes_pendientes.append({"telefono": row['telefono'], "mensaje": msg, "tipo": "CONFIRMACION"})

    # Guardar en JSON para ejecución mañana
    with open(SMS_PENDING_FILE, 'w', encoding='utf-8') as f:
        json.dump(mensajes_pendientes, f, indent=4, ensure_ascii=False)

    log_caja_negra('SYSTEM', 'AGENDA', f'Agenda de {len(mensajes_pendientes)} SMS preparada para mañana 8 AM.')
    print(f"Agenda preparada: {len(mensajes_pendientes)} mensajes listos.")

if __name__ == "__main__":
    preparar_agenda()
