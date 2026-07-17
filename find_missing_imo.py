import sqlite3
import pandas as pd

def find_missing_imo():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    conn = sqlite3.connect(db_path)
    query = "SELECT identificacion, nombre, apellido, imo FROM participantes WHERE (imo IS NULL OR imo = '' OR imo = '-' OR imo = 'None') AND es_pendiente_real = 'SI'"
    df = pd.read_sql_query(query, conn)
    print(f"Total participantes sin IMO: {len(df)}")
    print(df.head(20))
    conn.close()

if __name__ == "__main__":
    find_missing_imo()
