"""
ACTUALIZAR C1='SI' PARA TODOS LOS SENTADOS E28
=================================================
Cruza los 96 CONFIRMADOS del scraper con la DB por DNI
y actualiza c1='SI' + estado='ACTIVO'.
"""
import pandas as pd
import sqlite3
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CSV_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\asistencia_e28_20260529_192004.csv'

df = pd.read_csv(CSV_PATH, encoding='utf-8')
confirmados = df[df['asistencia'].str.upper() == 'CONFIRMADO']
desertores = df[df['asistencia'].str.upper() == 'DESERTOR']
pendientes = df[df['asistencia'].str.upper() == 'PENDIENTE']

print(f"Total scraper: {len(df)}")
print(f"CONFIRMADOS: {len(confirmados)}")
print(f"DESERTORES: {len(desertores)}")
print(f"PENDIENTES: {len(pendientes)}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

updated_c1 = 0
updated_desertor = 0
not_found = []

for _, row in df.iterrows():
    dni = str(row['identificacion']).strip()
    nombre = str(row['nombre']).strip()
    apellido = str(row['apellido']).strip()
    asist = str(row['asistencia']).strip().upper()
    telefono = re.sub(r'\D', '', str(row['telefono']).strip())
    
    # Buscar por DNI (con y sin ceros)
    found_id = None
    
    if dni:
        # Exacto
        c.execute("SELECT id FROM participantes WHERE identificacion=?", (dni,))
        r = c.fetchone()
        if r:
            found_id = r[0]
        else:
            # Sin ceros iniciales
            stripped = dni.lstrip('0')
            c.execute("SELECT id FROM participantes WHERE REPLACE(LTRIM(identificacion,'0'),' ','') = ?", (stripped,))
            r = c.fetchone()
            if r:
                found_id = r[0]
    
    # Si no, por teléfono
    if not found_id and telefono and len(telefono) >= 9:
        tel_suffix = telefono[-9:]
        c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{tel_suffix}%",))
        r = c.fetchone()
        if r:
            found_id = r[0]
    
    # Si no, por nombre+apellido
    if not found_id:
        c.execute("""
            SELECT id FROM participantes 
            WHERE UPPER(COALESCE(nombre,'')) = UPPER(?) 
              AND UPPER(COALESCE(apellido,'')) = UPPER(?)
        """, (nombre, apellido))
        r = c.fetchone()
        if r:
            found_id = r[0]
    
    if found_id:
        if asist == 'CONFIRMADO':
            c.execute("UPDATE participantes SET c1='SI', estado='ACTIVO' WHERE id=?", (found_id,))
            updated_c1 += 1
        elif asist == 'DESERTOR':
            c.execute("UPDATE participantes SET c1='NO', estado='DESERTOR' WHERE id=?", (found_id,))
            updated_desertor += 1
    else:
        not_found.append(f"{nombre} {apellido} | DNI:{dni} | Tel:{telefono}")

conn.commit()

# Verificar Eliana Rocío Jara
c.execute("SELECT id, nombre, apellido, c1, estado, equipo FROM participantes WHERE identificacion LIKE '%7938881%'")
jara = c.fetchall()
print(f"\n--- ELIANA ROCIO JARA ---")
for r in jara:
    print(f"  ID:{r[0]} | {r[1]} {r[2]} | C1:{r[3]} | Estado:{r[4]} | Eq:{r[5]}")

# Stats finales E28
e28_c1_si = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%' AND c1='SI'").fetchone()[0]
e28_activos = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%' AND estado='ACTIVO'").fetchone()[0]
e28_desertores = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo LIKE '%28%' AND estado='DESERTOR'").fetchone()[0]

print(f"\n{'='*65}")
print(f"  RESULTADO ACTUALIZACIÓN C1 E28")
print(f"{'='*65}")
print(f"  ✅ C1='SI' actualizados: {updated_c1}")
print(f"  ❌ Desertores marcados: {updated_desertor}")
print(f"  ⚠️  No encontrados: {len(not_found)}")
print(f"\n  E28 con C1=SI: {e28_c1_si}")
print(f"  E28 activos: {e28_activos}")
print(f"  E28 desertores: {e28_desertores}")
print(f"{'='*65}")

if not_found:
    print(f"\n--- NO ENCONTRADOS ({len(not_found)}) ---")
    for nf in not_found[:15]:
        print(f"  ⚠️  {nf}")

conn.close()
