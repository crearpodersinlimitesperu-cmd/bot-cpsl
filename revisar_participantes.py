import pandas as pd
import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = r'C:\Users\josem\Downloads\participantes_2026-05-28.csv'
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

df = pd.read_csv(CSV_PATH, encoding='utf-8', on_bad_lines='skip')
print(f"Total participantes en CSV: {len(df)}")
print(f"Columnas: {list(df.columns)}")

# Equipos
print(f"\n{'='*60}")
print("DISTRIBUCIÓN POR EQUIPO")
print(f"{'='*60}")
print(df['Equipo'].value_counts().to_string())

# E28 detallado
e28 = df[df['Equipo'].astype(str).str.contains('28', na=False)]
print(f"\n{'='*60}")
print(f"EQUIPO 28 — {len(e28)} participantes")
print(f"{'='*60}")

# Verificar 8 APTOS de bienvenida
aptos_data = [
    {"nombre": "Brian Steventh Torres", "apellido": "Yañez", "tel": "910236499", "tipo": "Cambio de Cupo"},
    {"nombre": "Bryan Ivan Diaz", "apellido": "Guerra", "tel": "927943882", "tipo": "Cambio de Cupo"},
    {"nombre": "Erica Magali Perea", "apellido": "Noguni", "tel": "900490075", "tipo": "Cambio de Cupo"},
    {"nombre": "Alexander Alvarado", "apellido": "Velasco", "tel": "988494485", "tipo": "Cambio de Cupo"},
    {"nombre": "Marizol", "apellido": "Espinoza", "tel": "955495024", "tipo": "Cambio de Cupo"},
    {"nombre": "Samira", "apellido": "Berrospi", "tel": "902774466", "tipo": "Cambio de Cupo"},
    {"nombre": "Nery Escalante", "apellido": "Ramirez", "tel": "957328767", "tipo": "Cambio de Cupo"},
    {"nombre": "Paul Yhonadan", "apellido": "Valentin Vargas", "tel": "989685398", "tipo": "Nueva Inscripción"},
]

# Participantes que SALIERON por cambio de cupo (deben marcarse si aún están)
salieron = [
    "José Enrique Díaz López",
    "Gilmer Mesias Fernández Castillo",
    "Ponciano Curilla Lazo",
    "Jhan Hamlet Palma",
    "Misael Rivera Lecarnaque",
    "Chachayma Cardenas Alejandro",
]

print(f"\n--- VERIFICACIÓN DE 8 APTOS (deben estar) ---")
for a in aptos_data:
    found = e28[e28.apply(lambda r: 
        a['apellido'].upper().split()[0] in str(r.get('Apellido','')).upper() and
        a['nombre'].upper().split()[0] in str(r.get('Nombre','')).upper(), axis=1)]
    if len(found) > 0:
        for _, r in found.iterrows():
            print(f"  [OK] {r['Nombre']} {r['Apellido']} | Tel: {r.get('Teléfono','')} | IMO: {r.get('IMO','')} | Tipo: {a['tipo']}")
    else:
        print(f"  [FALTA] {a['nombre']} {a['apellido']} | Tel: {a['tel']} | {a['tipo']}")

print(f"\n--- VERIFICACIÓN DE SALIENTES (cambio de cupo - no deberían estar activos) ---")
for s in salieron:
    parts = s.upper().split()
    found = e28[e28.apply(lambda r: 
        any(p in str(r.get('Nombre','')).upper() + ' ' + str(r.get('Apellido','')).upper() for p in parts[:2]), axis=1)]
    if len(found) > 0:
        for _, r in found.iterrows():
            print(f"  [AUN EN LISTA] {r['Nombre']} {r['Apellido']} | Tel: {r.get('Teléfono','')} | IMO: {r.get('IMO','')}")
    else:
        print(f"  [YA REMOVIDO] {s}")

# Cruzar con DB
print(f"\n{'='*60}")
print("CRUCE CON BASE DE DATOS torre_control.db")
print(f"{'='*60}")
conn = sqlite3.connect(DB_PATH)
db_count = conn.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
db_e28 = conn.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%'").fetchone()[0]
print(f"Total en DB: {db_count}")
print(f"E28 en DB: {db_e28}")
print(f"E28 en CSV: {len(e28)}")
print(f"Diferencia: {abs(len(e28) - db_e28)} participantes")

# Verificar si los nuevos están en la DB
print(f"\n--- APTOS en torre_control.db ---")
for a in aptos_data:
    first = a['nombre'].split()[0].upper()
    ape = a['apellido'].split()[0].upper()
    rows = conn.execute(
        "SELECT id, nombre, apellido, telefono, equipo, estado FROM participantes WHERE nombre LIKE ? AND apellido LIKE ?",
        (f"%{first}%", f"%{ape}%")
    ).fetchall()
    if rows:
        for r in rows:
            print(f"  [DB OK] ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Eq:{r[4]} | Estado:{r[5]}")
    else:
        print(f"  [DB FALTA] {a['nombre']} {a['apellido']} — NO está en la DB, DEBE AGREGARSE")

conn.close()
