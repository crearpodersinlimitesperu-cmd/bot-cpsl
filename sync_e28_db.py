"""
SINCRONIZAR E28 COMPLETO — Portal → torre_control.db
=====================================================
Carga los 183 participantes del scraper al DB.
Busca el DNI 07938881 para debug.
"""
import pandas as pd
import sqlite3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CSV_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\asistencia_e28_20260529_192004.csv'

df = pd.read_csv(CSV_PATH, encoding='utf-8')
print(f"Participantes del scraper: {len(df)}")
print(f"Columnas: {list(df.columns)}")

# Buscar DNI 07938881
target = df[df['identificacion'].astype(str).str.contains('07938881|7938881', na=False)]
print(f"\nDNI 07938881 en scraper: {len(target)}")
if len(target) > 0:
    for _, r in target.iterrows():
        print(f"  {r['nombre']} {r['apellido']} | Tel: {r['telefono']} | Asist: {r['asistencia']}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Insertar/actualizar cada participante del E28
added = 0
updated = 0
for _, row in df.iterrows():
    dni = str(row.get('identificacion', '')).strip()
    nombre = str(row.get('nombre', '')).strip()
    apellido = str(row.get('apellido', '')).strip()
    telefono = str(row.get('telefono', '')).strip()
    asistencia = str(row.get('asistencia', '')).strip().upper()
    sede = str(row.get('sede', '')).strip()
    pago_c2 = str(row.get('pago_c2', '')).strip()
    pago_maestria = str(row.get('pago_maestria', '')).strip()
    tipo_base = str(row.get('tipo_base', '')).strip()
    
    # Limpiar teléfono
    tel_clean = re.sub(r'\D', '', telefono)
    if len(tel_clean) == 9:
        tel_clean = '51' + tel_clean
    
    # Determinar estado
    if asistencia == 'CONFIRMADO':
        estado = 'ACTIVO'
        c1_val = 'SI'
    elif asistencia == 'DESERTOR':
        estado = 'DESERTOR'
        c1_val = 'NO'
    else:
        estado = 'PENDIENTE'
        c1_val = None
    
    # Check if exists by DNI
    c.execute("SELECT id FROM participantes WHERE identificacion=?", (dni,))
    exists = c.fetchone()
    
    if not exists and tel_clean:
        c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{tel_clean[-9:]}%",))
        exists = c.fetchone()
    
    if exists:
        # Update
        updates = ["estado=?", "equipo='EQUIPO 28'"]
        params = [estado]
        if c1_val:
            updates.append("c1=?")
            params.append(c1_val)
        params.append(exists[0])
        c.execute(f"UPDATE participantes SET {', '.join(updates)} WHERE id=?", params)
        updated += 1
    else:
        # Insert new
        imo_nombre = str(row.get('imo_nombre', '') if 'imo_nombre' in df.columns else '').strip()
        imo_tel = str(row.get('imo_tel', '') if 'imo_tel' in df.columns else '').strip()
        
        c.execute("""
            INSERT INTO participantes (nombre, apellido, telefono, identificacion, equipo, estado, c1)
            VALUES (?, ?, ?, ?, 'EQUIPO 28', ?, ?)
        """, (nombre, apellido, tel_clean, dni, estado, c1_val))
        added += 1

conn.commit()

# Verificar DNI 07938881 ahora
c.execute("SELECT id, nombre, apellido, telefono, equipo, estado, c1 FROM participantes WHERE identificacion LIKE '%7938881%'")
rows = c.fetchall()
print(f"\nDNI 07938881 en DB después de sync: {len(rows)}")
for r in rows:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Eq:{r[4]} | Estado:{r[5]} | C1:{r[6]}")

# Total final
total = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
e28_total = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%'").fetchone()[0]
e28_activos = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%' AND estado='ACTIVO'").fetchone()[0]
e28_desertores = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%' AND estado LIKE '%DESERTOR%'").fetchone()[0]

print(f"\n{'='*65}")
print(f"  RESUMEN SYNC")
print(f"{'='*65}")
print(f"  Nuevos agregados: +{added}")
print(f"  Actualizados: {updated}")
print(f"  Total DB: {total}")
print(f"  E28 total: {e28_total}")
print(f"  E28 activos (sentados): {e28_activos}")
print(f"  E28 desertores: {e28_desertores}")
print(f"{'='*65}")

conn.close()
