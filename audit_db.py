import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('torre_control.db')
c = conn.cursor()

tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print('=== TABLAS ===')
for t in tables:
    cols = c.execute(f'PRAGMA table_info({t[0]})').fetchall()
    count = c.execute(f'SELECT COUNT(*) FROM {t[0]}').fetchone()[0]
    print(f'\n{t[0]} ({count} registros):')
    for col in cols:
        print(f'  {col[1]} ({col[2]})')

print('\n=== CALIDAD DE DATOS ===')
checks = [
    ("Nombres vacíos", "SELECT COUNT(*) FROM participantes WHERE nombre IS NULL OR nombre=''"),
    ("Apellidos vacíos", "SELECT COUNT(*) FROM participantes WHERE apellido IS NULL OR apellido=''"),
    ("Tel vacíos", "SELECT COUNT(*) FROM participantes WHERE telefono IS NULL OR telefono=''"),
    ("CC vacía", "SELECT COUNT(*) FROM participantes WHERE cc_nombre IS NULL OR cc_nombre=''"),
    ("Tel con .0", "SELECT COUNT(*) FROM participantes WHERE telefono LIKE '%.0'"),
    ("CC tel con .0", "SELECT COUNT(*) FROM participantes WHERE cc_tel LIKE '%.0'"),
    ("Nombre pref nan", "SELECT COUNT(*) FROM participantes WHERE nombre_preferido='nan'"),
    ("Apellido nan", "SELECT COUNT(*) FROM participantes WHERE apellido='nan'"),
    ("Estado vacío", "SELECT COUNT(*) FROM participantes WHERE estado IS NULL OR estado=''"),
]
for label, q in checks:
    print(f'  {label}: {c.execute(q).fetchone()[0]}')

print('\n=== DUPLICADOS TELÉFONO ===')
dups = c.execute("SELECT telefono, COUNT(*) as cnt FROM participantes WHERE telefono != '' GROUP BY telefono HAVING cnt > 1 ORDER BY cnt DESC LIMIT 10").fetchall()
for d in dups:
    print(f'  {d[0]}: {d[1]} veces')
total_dups = c.execute("SELECT SUM(cnt) FROM (SELECT COUNT(*) as cnt FROM participantes WHERE telefono != '' GROUP BY telefono HAVING cnt > 1)").fetchone()[0]
print(f'  TOTAL registros en duplicados: {total_dups or 0}')

print('\n=== DISTRIBUCIÓN CC ===')
ccs = c.execute("SELECT cc_nombre, COUNT(*) FROM participantes GROUP BY cc_nombre ORDER BY COUNT(*) DESC").fetchall()
for cc in ccs:
    print(f'  {cc[0] or "(vacío)"}: {cc[1]}')

print('\n=== ESTADOS ===')
for e in c.execute("SELECT estado, COUNT(*) FROM participantes GROUP BY estado").fetchall():
    print(f'  {e[0]}: {e[1]}')

print('\n=== COMBINACIONES C1/C2 ===')
for co in c.execute("SELECT c1, c2, COUNT(*) FROM participantes GROUP BY c1, c2").fetchall():
    print(f'  C1={co[0]} C2={co[1]}: {co[2]}')

print('\n=== CAJA NEGRA ===')
cn_count = c.execute("SELECT COUNT(*) FROM caja_negra").fetchone()[0]
print(f'  Total registros: {cn_count}')
for r in c.execute("SELECT tipo, COUNT(*) FROM caja_negra GROUP BY tipo").fetchall():
    print(f'  {r[0]}: {r[1]}')

print('\n=== COMUNICACIONES ===')
com_count = c.execute("SELECT COUNT(*) FROM comunicaciones").fetchone()[0]
print(f'  Total: {com_count}')

print('\n=== DESERTORES ===')
des_count = c.execute("SELECT COUNT(*) FROM desertores").fetchone()[0]
print(f'  Total: {des_count}')

print('\n=== TELÉFONOS INVÁLIDOS ===')
inv = c.execute("SELECT COUNT(*) FROM participantes WHERE LENGTH(telefono) < 9 AND telefono != ''").fetchone()[0]
print(f'  Tel < 9 dígitos: {inv}')
long_tel = c.execute("SELECT COUNT(*) FROM participantes WHERE LENGTH(telefono) > 15").fetchone()[0]
print(f'  Tel > 15 dígitos: {long_tel}')

print('\n=== MUESTRA DATOS E27 (EQUIPO 27) ===')
for r in c.execute("SELECT nombre, apellido, nombre_preferido, telefono, cc_nombre, c1, c2 FROM participantes WHERE equipo='EQUIPO 27' LIMIT 5").fetchall():
    print(f'  {r[0]} | {r[1]} | pref:{r[2]} | tel:{r[3]} | cc:{r[4]} | C1:{r[5]} C2:{r[6]}')

conn.close()
