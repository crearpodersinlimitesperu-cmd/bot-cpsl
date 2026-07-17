import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def buscar():
    conn = sqlite3.connect(DB_PATH)
    # Busqueda amplia
    query = "SELECT * FROM participantes WHERE (nombre LIKE '%CESAR%') OR (apellido LIKE '%CESAR%')"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Filtrar por MIRKO en el dataframe (mas flexible)
    mask = df.apply(lambda row: row.astype(str).str.contains('MIRKO', case=False).any(), axis=1)
    results = df[mask]
    
    if not results.empty:
        print("RESULTADOS ENCONTRADOS:")
        print(results.to_string())
    else:
        print("No se encontro ningun registro que coincida con 'Cesar Mirko' en la base de datos central.")

if __name__ == "__main__":
    buscar()
