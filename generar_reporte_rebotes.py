"""
Módulo para la generación de reportes en Excel sobre los rebotes detectados en el sistema.
Consolida información de la caja negra y de la base de datos de participantes.
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"
OUTPUT_XLSX = BASE_DIR / "REPORTE_REBOTES_SISTEMA_CREAR.xlsx"

def extract_email(text):
    """Extrae una dirección de correo electrónico de una cadena de texto."""
    match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return match.group(0) if match else "Desconocido"

def generar_reporte_rebotes():
    """
    Genera un archivo Excel con dos pestañas: participantes marcados como rebotados
    y el historial de detecciones de la caja negra.
    """
    print("--- GENERANDO REPORTE DE REBOTES ---")

    # 1. Obtener datos de la Caja Negra (historial de detección)
    conn_log = sqlite3.connect(LOG_DB)
    df_logs = pd.read_sql("SELECT timestamp, detalle FROM logs WHERE categoria LIKE '%BOUNCE%'", conn_log)
    conn_log.close()

    df_logs['email_fallido'] = df_logs['detalle'].apply(extract_email)

    # 2. Obtener datos de Participantes (contactos para corrección)
    conn_main = sqlite3.connect(DB_PATH)
    # Buscamos a los participantes que tienen estado de rebote
    query = """
        SELECT nombre, apellido, telefono, email as estado_email, cc_nombre, equipo
        FROM participantes
        WHERE email = 'REBOTE' OR estado_respuesta_sms = 'EMAIL_BOUNCED'
    """
    df_px = pd.read_sql(query, conn_main)
    conn_main.close()

    print(f"Rebotes detectados en historial: {len(df_logs)}")
    print(f"Participantes marcados en DB: {len(df_px)}")

    # Guardar a Excel
    with pd.ExcelWriter(OUTPUT_XLSX) as writer:
        df_px.to_excel(writer, sheet_name='Participantes_a_Corregir', index=False)
        df_logs.to_excel(writer, sheet_name='Historial_Detecciones', index=False)

    print(f"✅ Reporte generado: {OUTPUT_XLSX.name}")

if __name__ == "__main__":
    generar_reporte_rebotes()
