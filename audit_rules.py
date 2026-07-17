import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')
conn = sqlite3.connect('torre_control.db')

leyla = conn.execute("SELECT COUNT(*) FROM participantes WHERE LOWER(cc_nombre) LIKE '%leyla%' OR LOWER(cc_nombre) LIKE '%linid%'").fetchone()[0]
print(f'PX con Leyla/Linid como CC: {leyla}')

done = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='SI' AND c2='SI'").fetchone()[0]
print(f'PX ya completaron C1+C2: {done}')

imp = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND c2='SI'").fetchone()[0]
print(f'ESTADOS IMPOSIBLES (C2=SI pero C1=NO): {imp}')

null_pref = conn.execute("SELECT COUNT(*) FROM participantes WHERE nombre_preferido IS NULL OR nombre_preferido=''").fetchone()[0]
print(f'PX sin nombre preferido: {null_pref}')

linid = conn.execute("SELECT COUNT(*) FROM participantes WHERE LOWER(cc_nombre) LIKE '%linid%'").fetchone()[0]
print(f'PX asignados a Linid: {linid}')

zuley = conn.execute("SELECT COUNT(*) FROM participantes WHERE LOWER(cc_nombre) LIKE '%zuley%'").fetchone()[0]
print(f'PX asignados a Zuley: {zuley}')

# Pendientes sin CC
no_cc_pend = conn.execute("SELECT COUNT(*) FROM participantes WHERE (cc_nombre IS NULL OR cc_nombre='') AND c1='NO'").fetchone()[0]
print(f'Pendientes C1 SIN coordinadora: {no_cc_pend}')

# Tel < 9 dígitos
short_tel = conn.execute("SELECT telefono FROM participantes WHERE LENGTH(telefono) < 9 AND telefono != ''").fetchall()
for t in short_tel:
    print(f'  Tel corto: {t[0]}')

# Verificar si hay índices
indices = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
print(f'\nÍndices DB: {[i[0] for i in indices]}')

# Tamaño DB
import os
size = os.path.getsize('torre_control.db')
print(f'Tamaño DB: {size/1024:.0f} KB')

conn.close()
