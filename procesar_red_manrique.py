import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("torre_control.db")

def procesar_red_manrique():
    print("--- PROCESANDO RED DE CAROLINA MANRIQUE ---")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Identificar a los graduados confirmados por ella
    graduados = ["OSCAR LEIVA MANRIQUE", "ERIKA ANTICONA AMES"]
    actualizados = 0
    
    for nombre in graduados:
        query = "UPDATE participantes SET c1 = 'SI', observaciones = 'GRADUADO_CONFIRMADO_IMO_CAROLINA' WHERE (nombre || ' ' || apellido) LIKE ?"
        conn.execute(query, (f"%{nombre}%",))
        actualizados += conn.execute("SELECT changes()").fetchone()[0]
    
    conn.commit()
    print(f"Participantes marcados como GRADUADOS: {actualizados}")
    
    # 2. Buscar a los otros 2 participantes de su red (segun el correo eran 4)
    # Buscamos en la base por IMO = Carolina Manrique
    query_pendientes = "SELECT id, nombre, apellido, telefono, c1 FROM participantes WHERE (imo LIKE '%MANRIQUE%' OR tel_imo LIKE '%99174092%') AND c1 = 'NO'"
    df_pend = pd.read_sql_query(query_pendientes, conn)
    
    print("\nOtros participantes de la Red Manrique que figuran como PENDIENTES:")
    if not df_pend.empty:
        print(df_pend.to_string())
    else:
        print("No se encontraron otros pendientes en su red.")
        
    conn.close()

if __name__ == "__main__":
    procesar_red_manrique()
