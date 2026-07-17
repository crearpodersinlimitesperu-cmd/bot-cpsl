import sqlite3
import pandas as pd

def check_luzmila():
    conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
    # Buscar por nombre o apellido
    df = pd.read_sql_query("SELECT nombre, apellido, email FROM participantes WHERE nombre LIKE '%LUZMILA%' OR apellido LIKE '%FLORES%'", conn)
    print(df)
    conn.close()

if __name__ == "__main__":
    check_luzmila()
