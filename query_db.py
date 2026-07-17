import os
import sqlite3
import pandas as pd

DB_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"
disc_path = r"C:\Users\josem\Downloads\bot-cpsl-review\deep_scan_discrepancias.csv"

if not os.path.exists(disc_path):
    print("No discrepancies file found!")
    exit(1)

df_disc = pd.read_csv(disc_path)
names = df_disc['Nombre_Completo'].tolist()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=== CURRENT DATABASE STATUS FOR DISCREPANCIES ===")
for name in names:
    # Normalize name to query
    parts = name.split()
    if len(parts) >= 2:
        query = f"SELECT id, nombre, apellido, equipo, c1, c2, maestria, estado, observaciones FROM participantes WHERE nombre LIKE ? AND apellido LIKE ?"
        cursor.execute(query, (f"%{parts[0]}%", f"%{parts[-1]}%"))
    else:
        query = f"SELECT id, nombre, apellido, equipo, c1, c2, maestria, estado, observaciones FROM participantes WHERE nombre LIKE ? OR apellido LIKE ?"
        cursor.execute(query, (f"%{name}%", f"%{name}%"))
        
    rows = cursor.fetchall()
    print(f"\nSearch for: '{name}'")
    if not rows:
        print("  Not found in DB!")
    for r in rows:
        print(f"  ID: {r[0]} | Name: {r[1]} {r[2]} | Equipo: {r[3]} | C1: {r[4]} | C2: {r[5]} | MJ: {r[6]} | Estado: {r[7]} | Obs: {r[8]}")
        
conn.close()
