import sqlite3
import pandas as pd
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

def get_confirmed():
    conn = sqlite3.connect(DB_PATH)
    # PX confirmados en C1
    query = "SELECT id, nombre, apellido, telefono, equipo, cc_nombre FROM participantes WHERE c1 = 'SI'"
    df = pd.read_sql(query, conn)
    print(f"Total confirmados C1: {len(df)}")
    print(df.head(10))
    conn.close()

if __name__ == "__main__":
    get_confirmed()
