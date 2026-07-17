import sqlite3
import pandas as pd
from pathlib import Path

# Rutas
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")
DATA_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\ACTUALIZACIONES_DEEP_SCAN.csv")

def inyeccion_masiva():
    print(f"--- INICIANDO INYECCION MASIVA EN CRM ---")
    if not DATA_PATH.exists():
        print("No se encontro el archivo de actualizaciones.")
        return

    df_upd = pd.read_csv(DATA_PATH)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    actualizados = 0
    for _, row in df_upd.iterrows():
        # Construir query dinamico para no sobreescribir con NULLs
        sets = []
        params = []
        
        if pd.notna(row['email']) and str(row['email']).strip() != '':
            sets.append("email = ?")
            params.append(row['email'])
        
        if pd.notna(row['dni']) and str(row['dni']).strip() != '':
            # Limpiar DNI de decimales si vienen del CSV
            dni_val = str(row['dni']).replace('.0', '').strip()
            sets.append("identificacion = ?")
            params.append(dni_val)
        
        if sets:
            sets.append("observaciones = ?")
            params.append(f"VALIDADO_ETL_{row['origen']}")
            
            params.append(row['id'])
            query = f"UPDATE participantes SET {', '.join(sets)} WHERE id = ?"
            
            try:
                c.execute(query, params)
                actualizados += 1
            except:
                continue

    conn.commit()
    conn.close()
    print(f"SANEAMIENTO COMPLETADO: {actualizados} registros purificados y validados con éxito.")

if __name__ == "__main__":
    inyeccion_masiva()
