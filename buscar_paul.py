import sqlite3
import pandas as pd
import glob
import os

DB_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"

# 1. Search in database
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT id, nombre, apellido, telefono, email, equipo, imo, tel_imo, identificacion, estado FROM participantes WHERE (nombre LIKE '%PAUL%' AND apellido LIKE '%VALENTIN%') OR (nombre LIKE '%YHONADAN%')")
rows = c.fetchall()
print(f"=== DATABASE RESULTS ({len(rows)}) ===")
for r in rows:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Email:{r[4]} | Equipo:{r[5]} | IMO:{r[6]} | TelIMO:{r[7]} | DNI:{r[8]} | Estado:{r[9]}")
conn.close()

# 2. Search in participant CSVs
csv_path = r"C:\Users\josem\Downloads\bot-cpsl-review\participantes_2026-05-26.csv"
if os.path.exists(csv_path):
    df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    matches = df[df['Nombre'].astype(str).str.contains('PAUL', case=False, na=False) & df['Apellido'].astype(str).str.contains('VALENTIN', case=False, na=False)]
    print(f"\n=== CSV RESULTS ({len(matches)}) ===")
    if len(matches) > 0:
        for _, r in matches.iterrows():
            print(f"  {r.get('Nombre','')} {r.get('Apellido','')} | Tel:{r.get('Teléfono','')} | Email:{r.get('Correo','')} | Equipo:{r.get('Equipo','')} | IMO:{r.get('IMO','')} | TelIMO:{r.get('Tel. IMO','')}")

# 3. Search in E28 Cambio de Cupo files
onedrive = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
cupo_files = glob.glob(os.path.join(onedrive, "**", "*Cambio de Cupo*.xlsx"), recursive=True)
cupo_files = [f for f in cupo_files if not os.path.basename(f).startswith("~$")]
print(f"\n=== SEARCHING IN {len(cupo_files)} CAMBIO DE CUPO FILES ===")
for fpath in cupo_files:
    df = pd.read_excel(fpath)
    for col in df.columns:
        matches = df[df[col].astype(str).str.contains('PAUL', case=False, na=False) | df[col].astype(str).str.contains('VALENTIN', case=False, na=False)]
        if len(matches) > 0:
            print(f"  File: {os.path.basename(fpath)} | Col: {col[:40]} | Rows: {len(matches)}")
            for idx, row in matches.iterrows():
                vals = [str(v)[:50] for v in row.values if pd.notna(v) and 'Acepto' not in str(v)]
                print(f"    Row {idx}: {' | '.join(vals[:8])}")
            break
