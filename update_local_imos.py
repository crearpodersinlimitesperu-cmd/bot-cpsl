import sqlite3
import pandas as pd

def update_local_db():
    print("--- ACTUALIZANDO BASE DE DATOS LOCAL CON IMOs ENCONTRADOS ---")
    
    csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\update_web_imos.csv'
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    
    if not os.path.exists(csv_path):
        print("No se encontró el archivo update_web_imos.csv")
        return
        
    df_updates = pd.read_csv(csv_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    actualizados = 0
    for _, row in df_updates.iterrows():
        dni_px = str(row['DNI_PX'])
        dni_imo = str(row['DNI_IMO'])
        imo_name = str(row['IMO_Name'])
        
        if dni_imo != "No encontrado":
            cursor.execute("UPDATE participantes SET imo = ?, tel_imo = (SELECT telefono FROM participantes WHERE identificacion = ? LIMIT 1) WHERE identificacion = ?", (dni_imo, dni_imo, dni_px))
            if cursor.rowcount > 0:
                actualizados += 1
                
    conn.commit()
    conn.close()
    print(f"Total participantes actualizados en BD local: {actualizados}")

import os
if __name__ == "__main__":
    update_local_db()
