"""
ACTUALIZAR participantes CSV + torre_control.db
================================================
1. Agregar los 7 nuevos APTOS (cambio de cupo) que faltan en el CSV
2. Agregar Brian y Paul a la DB (los que faltan)
3. Actualizar la DB con todos los participantes del E28 que faltan
"""
import pandas as pd
import sqlite3
import sys
import os

sys.stdout.reconfigure(encoding='utf-8')

CSV_PATH = r'C:\Users\josem\Downloads\participantes_2026-05-28.csv'
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

# ══════════════════════════════════════════════════════════════
# 1. ACTUALIZAR CSV — Agregar 7 cambios de cupo que faltan
# ══════════════════════════════════════════════════════════════
print("=" * 65)
print("  ACTUALIZACIÓN DE PARTICIPANTES — CSV + DB")
print("=" * 65)

df = pd.read_csv(CSV_PATH, encoding='utf-8', on_bad_lines='skip')
print(f"\nCSV original: {len(df)} participantes")

# Los 7 cambios de cupo que faltan en el CSV (Paul ya está)
nuevos_csv = [
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "1523660", "Ident. Cambio Cupo": "",
        "Nombre": "BRIAN STEVENTH", "Apellido": "TORRES YAÑEZ",
        "Teléfono": "910236499", "Eq. IMO": "", 
        "IMO": "RODRIGUEZ LA RIVA DAVID JESUS", "Tel. IMO": "927788191"
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "71942750", "Ident. Cambio Cupo": "",
        "Nombre": "BRYAN IVAN", "Apellido": "DIAZ GUERRA",
        "Teléfono": "927943882", "Eq. IMO": "",
        "IMO": "ALTAMIRANO LLACCHUAS ANTONY LEO", "Tel. IMO": "958110726"
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "10202624", "Ident. Cambio Cupo": "",
        "Nombre": "ERICA MAGALI", "Apellido": "PEREA NOGUNI",
        "Teléfono": "900490075", "Eq. IMO": "",
        "IMO": "MACHADO QUIÑONES YULI INES", "Tel. IMO": "950088740"
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "74591237", "Ident. Cambio Cupo": "",
        "Nombre": "ALEXANDER", "Apellido": "ALVARADO VELASCO",
        "Teléfono": "988494485", "Eq. IMO": "",
        "IMO": "PALOMINO GIOVANA", "Tel. IMO": "993717944"
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "9909616", "Ident. Cambio Cupo": "",
        "Nombre": "MARIZOL ÑANGA", "Apellido": "ESPINOZA EGUIZABAL",
        "Teléfono": "955495024", "Eq. IMO": "",
        "IMO": "PALOMINO MARCOS GIOVANA", "Tel. IMO": "993717944"
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "76522459", "Ident. Cambio Cupo": "",
        "Nombre": "SAMIRA MARGARITA", "Apellido": "BERROSPI CHACHAYMA",
        "Teléfono": "902774466", "Eq. IMO": "",
        "IMO": "CHACHAYMA MARCOS BLANCA LUZ", "Tel. IMO": ""
    },
    {
        "Acciones": "", "C1": "", "C2": "", "Maestría": "", "Tipo": "CAMBIO CUPO",
        "Equipo": "EQUIPO 28", "Identificación": "21428247", "Ident. Cambio Cupo": "",
        "Nombre": "NERY", "Apellido": "ESCALANTE RAMIREZ",
        "Teléfono": "957328767", "Eq. IMO": "",
        "IMO": "MITAC ESCALANTE VANNIA STHEF", "Tel. IMO": "956237980"
    },
]

# Verificar que no existan duplicados antes de agregar
added = 0
for nuevo in nuevos_csv:
    tel = str(nuevo['Teléfono'])
    exists = df[df['Teléfono'].astype(str).str.contains(tel, na=False)]
    if len(exists) == 0:
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        added += 1
        print(f"  [+CSV] Agregado: {nuevo['Nombre']} {nuevo['Apellido']} ({nuevo['Tipo']})")
    else:
        print(f"  [=CSV] Ya existe: {nuevo['Nombre']} {nuevo['Apellido']}")

# Guardar CSV actualizado
df.to_csv(CSV_PATH, index=False, encoding='utf-8')
print(f"\nCSV actualizado: {len(df)} participantes (+{added} nuevos)")

# ══════════════════════════════════════════════════════════════
# 2. ACTUALIZAR DB — Agregar Brian y Paul que faltan
# ══════════════════════════════════════════════════════════════
print(f"\n{'='*65}")
print("  ACTUALIZACIÓN DE BASE DE DATOS")
print(f"{'='*65}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Verificar columnas disponibles en la tabla
c.execute("PRAGMA table_info(participantes)")
cols = [col[1] for col in c.fetchall()]
print(f"Columnas en DB: {cols[:15]}...")

# Datos a insertar en DB
nuevos_db = [
    {
        "nombre": "BRIAN STEVENTH",
        "apellido": "TORRES YAÑEZ",
        "telefono": "51910236499",
        "identificacion": "1523660",
        "equipo": "EQUIPO 28",
        "imo": "RODRIGUEZ LA RIVA DAVID JESUS",
        "tel_imo": "927788191",
        "email": "xdbrian.steventh@gmail.com",
        "estado": "ACTIVO",
    },
    {
        "nombre": "PAUL  YHONADAN",
        "apellido": "VALENTIN VARGAS",
        "telefono": "51989685398",
        "identificacion": "75093610",
        "equipo": "EQUIPO 28",
        "imo": "VALENTIN MARIANO AURELIO",
        "tel_imo": "979310770",
        "email": "paulyhonadan_valentin@gmail.com",
        "estado": "ACTIVO",
    },
]

added_db = 0
for nuevo in nuevos_db:
    # Check if already exists
    c.execute("SELECT id FROM participantes WHERE identificacion = ?", (nuevo['identificacion'],))
    exists = c.fetchone()
    if exists:
        print(f"  [=DB] Ya existe ID {exists[0]}: {nuevo['nombre']} {nuevo['apellido']}")
        continue
    
    # Also check by phone
    c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{nuevo['telefono'][-9:]}%",))
    exists2 = c.fetchone()
    if exists2:
        print(f"  [=DB] Ya existe ID {exists2[0]} (por tel): {nuevo['nombre']} {nuevo['apellido']}")
        continue
    
    # Build dynamic insert based on available columns
    insert_cols = [k for k in nuevo.keys() if k in cols]
    insert_vals = [nuevo[k] for k in insert_cols]
    placeholders = ','.join(['?' for _ in insert_cols])
    col_names = ','.join(insert_cols)
    
    c.execute(f"INSERT INTO participantes ({col_names}) VALUES ({placeholders})", insert_vals)
    added_db += 1
    print(f"  [+DB] Agregado: {nuevo['nombre']} {nuevo['apellido']} (DNI: {nuevo['identificacion']})")

conn.commit()

# Verificación final
total_db = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
e28_db = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%'").fetchone()[0]
print(f"\nDB actualizada: {total_db} total, {e28_db} en E28 (+{added_db} nuevos)")

conn.close()

print(f"\n{'='*65}")
print(f"  RESUMEN DE ACTUALIZACIÓN")
print(f"  CSV: +{added} participantes agregados")
print(f"  DB:  +{added_db} participantes agregados")
print(f"  Total CSV: {len(df)} | Total DB: {total_db}")
print(f"{'='*65}")
