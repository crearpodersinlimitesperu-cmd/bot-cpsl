"""
Módulo para la sanación y normalización de la base de datos de caja negra.
Asegura que las tablas necesarias existan y registra la operación en los logs.
"""
import sqlite3
from datetime import datetime
from pathlib import Path

# Estandarización de rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "caja_negra.db"

def sanar_caja_negra():
    """
    Realiza la sanación de la base de datos, asegurando la existencia de las tablas
    'logs' y 'caja_negra', e inserta un registro de auditoría.
    """
    print("--- INICIANDO SANACIÓN DE CAJA NEGRA (V2.0) ---")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 1. Asegurar esquema completo de 'logs' (Fuente de verdad del CRM)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            categoria TEXT,
            evento TEXT,
            detalle TEXT,
            estado TEXT
        )
    ''')

    # 2. Asegurar esquema de 'caja_negra' (Trazabilidad extendida opcional)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS caja_negra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            tipo TEXT,
            accion TEXT,
            detalle TEXT,
            canal TEXT,
            px_nombre TEXT,
            px_telefono TEXT,
            cc_nombre TEXT,
            estado TEXT
        )
    ''')

    # 3. Registrar sanación con trazabilidad
    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
        VALUES (?, ?, ?, ?, ?)
    ''', (
        ahora,
        'SYSTEM',
        'SANACION_DB',
        'Infraestructura de logs normalizada y rutas estandarizadas.',
        'COMPLETO'
    ))

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM logs")
    total = cursor.fetchone()[0]
    print(f"Caja Negra sanada. Total registros en 'logs': {total}")

    conn.close()

if __name__ == "__main__":
    sanar_caja_negra()
