import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')

queries = [
    ("Fredy", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%fredy%'"),
    ("Maria", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%maria%'"),
    ("Richar", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%richar%'")
]

for name, q in queries:
    df = pd.read_sql_query(q, conn)
    print(f"--- Buscando {name} ---")
    if len(df) > 0:
        for i, r in df.iterrows():
            print(f"ID: {r['id']} | {r['nombre']} {r['apellido']} | Email: {r['email']} | CC: {r['cc_nombre']} | C1: {r['c1']} | C2: {r['c2']}")
    else:
        print("No encontrado.")

conn.close()
