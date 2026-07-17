"""
ANÁLISIS CORRECTO DE GRADUADOS MJ
===================================
La hoja 'GRADUADOS' tiene 347 filas pero NO todos son graduados MJ.
Los códigos en las columnas E5-E28 significan:
  M = Maestría (GRADUADO MJ real)
  A = Aliado/Apoyo
  C = Capitán
  Q = QT
  - = No participó

Solo los que tienen "M" en al menos una columna son GRADUADOS MJ reales.
Los demás se dejan con su estado original.
"""
import pandas as pd
import sqlite3
import unicodedata
import sys
sys.stdout.reconfigure(encoding='utf-8')

GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"
DB_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"

def norm(s):
    if not s or str(s) == 'nan':
        return ''
    s = str(s).strip().upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = ' '.join(s.split())
    return s

# 1. Leer la hoja GRADUADOS
df = pd.read_excel(GRAD_PATH, sheet_name='GRADUADOS ')
print(f"Total filas en hoja 'GRADUADOS': {len(df)}")
print(f"Columnas: {list(df.columns)}")

# Columnas de equipos (E5 a E28)
equipo_cols = [c for c in df.columns if str(c).startswith('E') and str(c)[1:].isdigit()]
print(f"Columnas de equipos: {equipo_cols}")

# 2. Clasificar cada persona
graduados_mj = []       # Tienen al menos una "M"
no_graduados_mj = []    # Solo tienen A, C, Q, - (NO son graduados MJ)

for idx, row in df.iterrows():
    nombre = str(row['CREAR CUANTICO']).strip()
    equipo_orig = str(row.get('EQUIPO ORIGINAL ', '')).strip()
    
    if not nombre or nombre == 'nan':
        continue
    
    # Revisar todos los valores en columnas de equipo
    codigos = []
    tiene_M = False
    for col in equipo_cols:
        val = str(row[col]).strip().upper()
        if val and val != 'NAN' and val != '-' and val != 'NAN':
            codigos.append(f"{col}={val}")
            if val == 'M':
                tiene_M = True
    
    if tiene_M:
        graduados_mj.append({
            'nombre': nombre,
            'equipo_original': equipo_orig,
            'codigos': ', '.join(codigos)
        })
    else:
        no_graduados_mj.append({
            'nombre': nombre,
            'equipo_original': equipo_orig,
            'codigos': ', '.join(codigos) if codigos else '(solo - o vacío)'
        })

print(f"\n{'='*65}")
print(f"  RESULTADO DEL ANÁLISIS")
print(f"{'='*65}")
print(f"  ✅ GRADUADOS MJ REALES (tienen M): {len(graduados_mj)}")
print(f"  ❌ NO GRADUADOS MJ (A, C, Q, -):   {len(no_graduados_mj)}")
print(f"  Total en hoja:                     {len(graduados_mj) + len(no_graduados_mj)}")

# 3. Mostrar los NO graduados para verificar
print(f"\n--- NO GRADUADOS MJ (descartar de conteo) ---")
for ng in no_graduados_mj:
    print(f"  {ng['nombre'][:40]:<42} | Eq: {ng['equipo_original']:<4} | Roles: {ng['codigos']}")

# 4. Mostrar primeros graduados MJ reales
print(f"\n--- PRIMEROS 15 GRADUADOS MJ REALES ---")
for g in graduados_mj[:15]:
    print(f"  {g['nombre'][:40]:<42} | Eq: {g['equipo_original']:<4} | {g['codigos']}")

# 5. Ahora corregir la DB: revertir los que NO son graduados MJ
print(f"\n{'='*65}")
print(f"  CORRIGIENDO BASE DE DATOS")
print(f"{'='*65}")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Primero: revertir TODOS los GRADUADO_COMPLETO a ACTIVO
c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'")
antes_grad = c.fetchone()[0]
print(f"Antes: {antes_grad} con GRADUADO_COMPLETO")

# Revertir todos a su estado anterior (ACTIVO por defecto)
c.execute("UPDATE participantes SET estado='ACTIVO' WHERE estado='GRADUADO_COMPLETO'")
revertidos = c.rowcount
print(f"Revertidos a ACTIVO: {revertidos}")

# Ahora solo marcar los GRADUADOS MJ REALES
matched = 0
not_found = []
nombres_graduados_mj = [norm(g['nombre']) for g in graduados_mj]

c.execute("SELECT id, nombre, apellido FROM participantes")
todos = c.fetchall()

for grad_name in nombres_graduados_mj:
    grad_tokens = set(grad_name.split())
    found = False
    
    for pid, nombre, apellido in todos:
        db_name = norm(f"{nombre} {apellido}")
        db_tokens = set(db_name.split())
        
        common = grad_tokens & db_tokens
        if len(common) >= 2:
            ratio = len(common) / max(len(grad_tokens), len(db_tokens))
            if ratio >= 0.5:
                c.execute("UPDATE participantes SET estado='GRADUADO_COMPLETO' WHERE id=?", (pid,))
                matched += 1
                found = True
                break
    
    if not found:
        not_found.append(grad_name)

conn.commit()

# Verificar resultado final
c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'")
despues_grad = c.fetchone()[0]

# Estado final completo
c.execute("SELECT estado, COUNT(*) FROM participantes GROUP BY estado ORDER BY COUNT(*) DESC")
print(f"\nEstados finales en DB:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Embudo final
total = conn.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
c1_si = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='SI'").fetchone()[0]
c2_si = conn.execute("SELECT COUNT(*) FROM participantes WHERE c2='SI'").fetchone()[0]

print(f"\n{'='*65}")
print(f"  EMBUDO DE CONVERSIÓN FINAL CORREGIDO")
print(f"{'='*65}")
print(f"  Inscritos (Total):     {total}")
print(f"  C1 Asistieron:         {c1_si}")
print(f"  C2 Asistieron:         {c2_si}")
print(f"  Graduados MJ REALES:   {despues_grad}")
print(f"{'='*65}")
print(f"\n  No encontrados en DB ({len(not_found)}):")
for nf in not_found:
    print(f"    - {nf}")

conn.close()
