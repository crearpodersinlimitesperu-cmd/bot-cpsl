"""
SYNC COMPLETO CSV → DB — Cargar todos los faltantes del CSV más reciente
=========================================================================
"""
import pandas as pd
import sqlite3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CSV_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\participantes_2026-05-28.csv'

df = pd.read_csv(CSV_PATH, encoding='latin-1')
print(f"CSV rows: {len(df)}")
print(f"Columnas: {list(df.columns)}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Total before
before = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
print(f"DB antes: {before}")

added = 0
updated = 0
skipped = 0

for _, row in df.iterrows():
    # Normalize column names (encoding issues)
    nombre = str(row.get('Nombre', '')).strip()
    apellido = str(row.get('Apellido', '')).strip()
    telefono = str(row.get('Teléfono', row.get('Tel\xe9fono', ''))).strip()
    equipo = str(row.get('Equipo', '')).strip()
    
    # Get identificacion - may have encoding issues
    ident_col = None
    for col in df.columns:
        if 'dentificac' in str(col) and 'Cambio' not in str(col):
            ident_col = col
            break
    
    identificacion = str(row.get(ident_col, '')).strip() if ident_col else ''
    if identificacion == 'nan':
        identificacion = ''
    # Remove decimal point if it's a float
    if '.' in identificacion:
        identificacion = identificacion.split('.')[0]
    
    # Normalize DNI - pad with leading zeros if needed (8 digits for Peru)
    if identificacion and identificacion.isdigit() and len(identificacion) < 8:
        identificacion = identificacion.zfill(8)
    
    c1 = str(row.get('C1', '')).strip()
    c2 = str(row.get('C2', '')).strip()
    
    # Maestria col
    maestria_col = None
    for col in df.columns:
        if 'aestr' in str(col):
            maestria_col = col
            break
    maestria = str(row.get(maestria_col, 'NO')).strip() if maestria_col else 'NO'
    
    tipo = str(row.get('Tipo', '')).strip()
    imo = str(row.get('IMO', '')).strip()
    tel_imo = str(row.get('Tel. IMO', '')).strip()
    eq_imo = str(row.get('Eq. IMO', '')).strip()
    
    # Skip if no name
    if not nombre or nombre == 'nan':
        skipped += 1
        continue
    
    # Clean telefono
    tel_clean = re.sub(r'\D', '', telefono)
    
    # Check if exists by identificacion
    exists = None
    if identificacion:
        c.execute("SELECT id FROM participantes WHERE identificacion=?", (identificacion,))
        exists = c.fetchone()
        
        # Also check without leading zeros
        if not exists:
            stripped = identificacion.lstrip('0')
            c.execute("SELECT id FROM participantes WHERE CAST(identificacion AS TEXT) = CAST(? AS TEXT)", (stripped,))
            exists = c.fetchone()
    
    # Check by phone
    if not exists and tel_clean and len(tel_clean) >= 9:
        c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{tel_clean[-9:]}%",))
        exists = c.fetchone()
    
    # Determine estado
    if tipo == 'DESERTOR':
        estado = 'DESERTOR'
    elif tipo == 'REZAGADO':
        estado = 'PENDIENTE'
    elif c1 == 'SI':
        estado = 'ACTIVO'
    else:
        estado = 'PENDIENTE'
    
    if exists:
        # Update identificacion if empty
        c.execute("UPDATE participantes SET identificacion=COALESCE(NULLIF(identificacion,''), ?) WHERE id=?",
                  (identificacion, exists[0]))
        updated += 1
    else:
        c.execute("""
            INSERT INTO participantes (nombre, apellido, telefono, identificacion, equipo, 
                                       imo, tel_imo, c1, c2, maestria, estado)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (nombre, apellido, tel_clean, identificacion, equipo, imo, tel_imo, c1, c2, maestria, estado))
        added += 1

conn.commit()

# Verify
after = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]

# Check DNI 07938881
c.execute("SELECT id, nombre, apellido, telefono, equipo, estado FROM participantes WHERE identificacion LIKE '%7938881%'")
rows = c.fetchall()
print(f"\nDNI 07938881: {len(rows)} resultados")
for r in rows:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Eq:{r[4]} | Estado:{r[5]}")

print(f"\n{'='*65}")
print(f"  RESULTADO SYNC CSV → DB")
print(f"{'='*65}")
print(f"  CSV filas: {len(df)}")
print(f"  DB antes: {before}")
print(f"  DB después: {after}")
print(f"  Nuevos: +{added}")
print(f"  Actualizados: {updated}")
print(f"  Saltados: {skipped}")
print(f"{'='*65}")

conn.close()
