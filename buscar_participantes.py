import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')

queries = [
    ("Greace", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%greace%' OR email LIKE '%greacedm%'"),
    ("Joseph", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%joseph%' AND apellido LIKE '%garibay%'"),
    ("Fredy", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE nombre LIKE '%fredy%' AND email LIKE '%innovacionesfullhouse%'"),
    ("Maria / Ivon", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE email LIKE '%ivonlizanotaype%'"),
    ("Richar / Elena", "SELECT id, nombre, apellido, email, c1, c2, estado, cc_nombre FROM participantes WHERE email LIKE '%multiservicioszavaleta%'")
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
