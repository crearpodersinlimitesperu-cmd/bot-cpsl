import pandas as pd
import glob
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1. VERIFICAR BRYAN DIAZ en Cambio de Cupo
f = glob.glob(r'C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\*Cambio*28*')[0]
df = pd.read_excel(f, header=None)

print("="*65)
print("  BÚSQUEDA DE BRYAN DIAZ EN CAMBIO DE CUPO")
print("="*65)

for idx, row in df.iterrows():
    if idx == 0:
        continue  # header
    all_text = ' '.join([str(v).lower() for v in row if pd.notna(v)])
    if 'bryan' in all_text or 'diaz' in all_text.replace('í','i') or 'ivan' in all_text.replace('á','a'):
        print(f"\n  Fila {idx}:")
        for i, v in enumerate(row):
            if pd.notna(v):
                s = str(v).strip()
                if s and len(s) > 1 and 'Acepto' not in s:
                    print(f"    Col[{i}]: {s[:70]}")

# 2. VERIFICAR CRM BUSCADOR - DNI 07938881
print(f"\n{'='*65}")
print("  VERIFICAR DNI 07938881 EN DB")
print("="*65)

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Buscar por DNI exacto
c.execute("SELECT id, nombre, apellido, telefono, email, equipo, identificacion, estado FROM participantes WHERE identificacion LIKE '%07938881%'")
rows = c.fetchall()
print(f"\nBúsqueda por identificacion LIKE '%07938881%': {len(rows)} resultados")
for r in rows:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Email:{r[4]} | Eq:{r[5]} | DNI:{r[6]} | Estado:{r[7]}")

# Buscar sin ceros iniciales
c.execute("SELECT id, nombre, apellido, telefono, email, equipo, identificacion, estado FROM participantes WHERE identificacion LIKE '%7938881%'")
rows2 = c.fetchall()
print(f"\nBúsqueda por '%7938881%': {len(rows2)} resultados")
for r in rows2:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Email:{r[4]} | Eq:{r[5]} | DNI:{r[6]} | Estado:{r[7]}")

# Ver todos los campos disponibles en la tabla
c.execute("PRAGMA table_info(participantes)")
cols = [col[1] for col in c.fetchall()]
print(f"\nColumnas en DB: {cols}")

# Verificar el CRM search query
# The current query: WHERE ... OR COALESCE(identificacion, '') LIKE ?
# Let's test it manually
test_q = "07938881"
sv = f"%{test_q}%"
c.execute("""
    SELECT id, nombre, apellido, identificacion FROM participantes
    WHERE COALESCE(identificacion, '') LIKE ?
    LIMIT 5
""", (sv,))
rows3 = c.fetchall()
print(f"\nCRM search test LIKE '%{test_q}%': {len(rows3)} resultados")
for r in rows3:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | DNI:{r[3]}")

# Check if it exists in the CSV
print(f"\n{'='*65}")
print("  VERIFICAR EN CSV PARTICIPANTES")
print("="*65)
csv_df = pd.read_csv(r'C:\Users\josem\Downloads\participantes_2026-05-28.csv', encoding='utf-8', on_bad_lines='skip')
matches = csv_df[csv_df['Identificación'].astype(str).str.contains('07938881|7938881', na=False)]
print(f"En CSV: {len(matches)} resultados")
for _, r in matches.iterrows():
    print(f"  {r.get('Nombre','')} {r.get('Apellido','')} | DNI: {r.get('Identificación','')} | Eq: {r.get('Equipo','')}")

# Count total in DB vs CSV
total_db = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
print(f"\nTotal DB: {total_db}")
print(f"Total CSV: {len(csv_df)}")

conn.close()
