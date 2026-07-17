import pandas as pd
import sqlite3
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"
CSV_PATH = Path(r"C:\Users\josem\Downloads\participantes_2026-05-11.csv")

def registrar_log(evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB, timeout=30.0)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'TRANSFERENCIA', evento, detalle, estado))
    conn.commit()
    conn.close()

def procesar_logica_cupo():
    print("--- INICIANDO PROCESAMIENTO DE CAMBIOS DE CUPO (FUZZY) ---")
    
    if not CSV_PATH.exists():
        return

    try:
        df = pd.read_csv(CSV_PATH, on_bad_lines='skip', encoding='latin1')
    except:
        return

    col_cambio = 'Ident. Cambio Cupo'
    col_nombre = 'Nombre'
    col_apellido = 'Apellido'

    df_transfers = df[df[col_cambio].astype(str).str.contains(r'^\d{8,9}$', na=False)].copy()
    
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    transfers_ok = 0
    for idx, row in df_transfers.iterrows():
        nombre = str(row[col_nombre]).strip().upper()
        apellido = str(row[col_apellido]).strip().upper()
        nuevo_dni = str(row[col_cambio]).strip()

        # Usamos LIKE para ser un poco mas flexibles con espacios o variaciones menores
        cursor.execute("""
            UPDATE participantes 
            SET estado = 'TRANSFERIDO', nuevo_titular_dni = ?, tiene_cambio_cupo = 'SI'
            WHERE (nombre LIKE ? AND apellido LIKE ?) AND estado != 'TRANSFERIDO'
        """, (nuevo_dni, f"%{nombre}%", f"%{apellido}%"))
        
        if cursor.rowcount > 0:
            transfers_ok += 1
            registrar_log('CUPO_TRANSFERIDO', f"PX: {nombre} {apellido} -> Nuevo DNI: {nuevo_dni}", "EXITO")
            print(f"Transferido: {nombre} {apellido}")

    conn.commit()
    conn.close()
    print(f"Proceso finalizado. {transfers_ok} transferencias ejecutadas.")

if __name__ == "__main__":
    procesar_logica_cupo()
