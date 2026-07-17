import sqlite3
import pandas as pd
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

def check_imos():
    conn = sqlite3.connect(DB_PATH)
    # Query para agrupar por IMO y listar sus PX rebotados
    query = """
        SELECT imo, tel_imo, GROUP_CONCAT(nombre || ' ' || apellido, ', ') as px_rebotados
        FROM participantes 
        WHERE email = 'REBOTE' AND imo IS NOT NULL AND imo != '' AND imo != 'nan'
        GROUP BY imo, tel_imo
    """
    df = pd.read_sql(query, conn)
    print("--- IMOS CON PARTICIPANTES REBOTADOS ---")
    print(df)
    conn.close()

if __name__ == "__main__":
    check_imos()
