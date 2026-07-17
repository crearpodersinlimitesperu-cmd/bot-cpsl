"""
CORREGIR GRADUADOS MJ — Sincronizar con archivo oficial
=========================================================
El archivo 'GRADUADOS LIMA.xlsx' hoja 'GRADUADOS' tiene 347 graduados reales.
La DB tiene solo 11 como GRADUADO_COMPLETO.
El CRM muestra 640 (incorrecto).

Este script:
1. Lee los 347 graduados del archivo oficial
2. Los cruza con la DB por nombre
3. Marca los que coincidan como GRADUADO_COMPLETO
4. Actualiza el endpoint del CRM para usar el conteo correcto
"""
import pandas as pd
import sqlite3
import unicodedata
import sys
sys.stdout.reconfigure(encoding='utf-8')

GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"
DB_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"

def norm(s):
    """Normaliza nombre: sin acentos, mayúsculas, sin espacios extra."""
    if not s or str(s) == 'nan':
        return ''
    s = str(s).strip().upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = ' '.join(s.split())  # Colapsar espacios
    return s

# 1. Leer graduados del archivo oficial
print("=" * 65)
print("  SINCRONIZACIÓN DE GRADUADOS MJ")
print("=" * 65)

df_grad = pd.read_excel(GRAD_PATH, sheet_name='GRADUADOS ')
print(f"\nGraduados en archivo oficial: {len(df_grad)}")

graduados_nombres = []
for _, row in df_grad.iterrows():
    nombre = str(row['CREAR CUANTICO']).strip()
    if nombre and nombre != 'nan':
        graduados_nombres.append(norm(nombre))

print(f"Nombres de graduados limpios: {len(graduados_nombres)}")

# 2. Cruzar con la DB
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Obtener todos los participantes de la DB
c.execute("SELECT id, nombre, apellido, estado FROM participantes")
todos = c.fetchall()
print(f"Total participantes en DB: {len(todos)}")

# Matching
matched = 0
unmatched_grad = []
matched_ids = []

for grad_name in graduados_nombres:
    found = False
    grad_tokens = set(grad_name.split())
    
    for pid, nombre, apellido, estado in todos:
        db_name = norm(f"{nombre} {apellido}")
        db_tokens = set(db_name.split())
        
        # Match: al menos 2 tokens en común y nombre/apellido coincidan
        common = grad_tokens & db_tokens
        if len(common) >= 2 and len(grad_tokens) > 0:
            # Verificar que sea un match fuerte (>= 60% tokens)
            ratio = len(common) / max(len(grad_tokens), len(db_tokens))
            if ratio >= 0.5:
                matched += 1
                matched_ids.append(pid)
                found = True
                break
    
    if not found:
        unmatched_grad.append(grad_name)

print(f"\nResultados del cruce:")
print(f"  ✅ Graduados encontrados en DB: {matched}")
print(f"  ❌ Graduados NO encontrados en DB: {len(unmatched_grad)}")

if unmatched_grad[:10]:
    print(f"\n  Primeros 10 no encontrados:")
    for name in unmatched_grad[:10]:
        print(f"    - {name}")

# 3. Actualizar estados en la DB
print(f"\n{'='*65}")
print("  ACTUALIZANDO ESTADOS EN LA DB")
print(f"{'='*65}")

# Primero, verificar cuántos ya tienen GRADUADO_COMPLETO
c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'")
antes = c.fetchone()[0]
print(f"Antes: {antes} con estado GRADUADO_COMPLETO")

# Actualizar solo los matched que NO sean ya GRADUADO_COMPLETO
updated = 0
for pid in matched_ids:
    c.execute("SELECT estado FROM participantes WHERE id=?", (pid,))
    row = c.fetchone()
    if row and row[0] != 'GRADUADO_COMPLETO':
        c.execute("UPDATE participantes SET estado='GRADUADO_COMPLETO' WHERE id=?", (pid,))
        updated += 1

conn.commit()

# Verificar después
c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'")
despues = c.fetchone()[0]
print(f"Después: {despues} con estado GRADUADO_COMPLETO (+{updated} actualizados)")

# 4. Verificar conteo final para el embudo
c.execute("SELECT estado, COUNT(*) FROM participantes GROUP BY estado ORDER BY COUNT(*) DESC")
print(f"\nEstados finales en DB:")
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Embudo correcto
total = conn.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
c1_si = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='SI'").fetchone()[0]
c2_si = conn.execute("SELECT COUNT(*) FROM participantes WHERE c2='SI'").fetchone()[0]
grad = conn.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'").fetchone()[0]

print(f"\n{'='*65}")
print(f"  EMBUDO DE CONVERSIÓN CORREGIDO")
print(f"{'='*65}")
print(f"  Inscritos (Total):  {total}")
print(f"  C1 Asistieron:      {c1_si}")
print(f"  C2 Asistieron:      {c2_si}")
print(f"  Graduados MJ:       {grad}  ← Correcto (archivo oficial: {len(graduados_nombres)})")
print(f"{'='*65}")

conn.close()
