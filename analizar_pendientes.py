import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('torre_control.db')

print("=== ANÁLISIS DE PENDIENTES C1 ===\n")

# 1. Total pendientes C1
total = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO'").fetchone()[0]
print(f"Total C1=NO: {total}\n")

# 2. Distribución por TIPO
print("--- POR TIPO ---")
for row in conn.execute("SELECT tipo, COUNT(*) FROM participantes WHERE c1='NO' GROUP BY tipo ORDER BY COUNT(*) DESC"):
    print(f"  {row[0] or '(vacío)'}: {row[1]}")

# 3. Distribución por ESTADO
print("\n--- POR ESTADO ---")
for row in conn.execute("SELECT estado, COUNT(*) FROM participantes WHERE c1='NO' GROUP BY estado ORDER BY COUNT(*) DESC"):
    print(f"  {row[0] or '(vacío)'}: {row[1]}")

# 4. Buscar patrones en nombres que indiquen "cambio de cupo" o "devolución"
print("\n--- POSIBLES NO-REALES (en nombre/apellido) ---")
keywords = ['CAMBIO', 'CUPO', 'DEVOL', 'CANCEL', 'ANULA', 'TRASPAS', 'NO INTER', 'BAJA', 'RETIRO']
for kw in keywords:
    cnt = conn.execute(f"SELECT COUNT(*) FROM participantes WHERE c1='NO' AND (UPPER(nombre) LIKE '%{kw}%' OR UPPER(apellido) LIKE '%{kw}%' OR UPPER(tipo) LIKE '%{kw}%' OR UPPER(estado) LIKE '%{kw}%')").fetchone()[0]
    if cnt > 0:
        print(f"  '{kw}': {cnt}")
        # Mostrar ejemplos
        for r in conn.execute(f"SELECT nombre, apellido, tipo, estado, equipo FROM participantes WHERE c1='NO' AND (UPPER(nombre) LIKE '%{kw}%' OR UPPER(apellido) LIKE '%{kw}%' OR UPPER(tipo) LIKE '%{kw}%' OR UPPER(estado) LIKE '%{kw}%') LIMIT 3"):
            print(f"    → {r[0]} {r[1]} | Tipo: {r[2]} | Estado: {r[3]} | Eq: {r[4]}")

# 5. Revisar la columna "Acciones"
print("\n--- CAMPO 'acciones' (si existe) ---")
try:
    for row in conn.execute("SELECT acciones, COUNT(*) FROM participantes WHERE c1='NO' AND acciones IS NOT NULL AND acciones != '' GROUP BY acciones ORDER BY COUNT(*) DESC LIMIT 10"):
        print(f"  {row[0]}: {row[1]}")
except:
    print("  (columna no existe)")

# 6. Cruzar con desertores
print("\n--- CRUCE CON DESERTORES ---")
desertores_en_pendientes = conn.execute("""
    SELECT COUNT(*) FROM participantes p
    INNER JOIN desertores d ON UPPER(TRIM(p.nombre)) = UPPER(TRIM(d.nombre))
    WHERE p.c1='NO'
""").fetchone()[0]
print(f"  PX pendientes que también están en tabla desertores: {desertores_en_pendientes}")

# 7. Distribución por equipo de los pendientes
print("\n--- POR EQUIPO (Top 10) ---")
for row in conn.execute("SELECT equipo, COUNT(*) FROM participantes WHERE c1='NO' GROUP BY equipo ORDER BY COUNT(*) DESC LIMIT 10"):
    print(f"  {row[0]}: {row[1]}")

# 8. Verificar columna "ident_cambio_cupo"
print("\n--- CAMPO ident_cambio_cupo ---")
try:
    cambios = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND ident_cambio_cupo IS NOT NULL AND ident_cambio_cupo != '' AND ident_cambio_cupo != '-'").fetchone()[0]
    print(f"  Con cambio de cupo: {cambios}")
    if cambios > 0:
        for r in conn.execute("SELECT nombre, apellido, ident_cambio_cupo, tipo FROM participantes WHERE c1='NO' AND ident_cambio_cupo IS NOT NULL AND ident_cambio_cupo != '' AND ident_cambio_cupo != '-' LIMIT 5"):
            print(f"    → {r[0]} {r[1]} | Cambio: {r[2]} | Tipo: {r[3]}")
except:
    print("  (columna no existe)")

# 9. Muestra de tipos raros
print("\n--- TODOS LOS TIPOS ÚNICOS EN SISTEMA ---")
for row in conn.execute("SELECT tipo, COUNT(*) FROM participantes GROUP BY tipo ORDER BY COUNT(*) DESC"):
    print(f"  {row[0] or '(vacío)'}: {row[1]}")

conn.close()
