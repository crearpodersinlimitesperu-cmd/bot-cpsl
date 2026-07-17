import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT id, nombre, apellido, cc_nombre, c1, c2, maestria, resultado_gestion, estado FROM participantes WHERE estado LIKE '%ARCHIVAD%' OR resultado_gestion LIKE '%ARCHIVAD%'", conn)
print(f'Casos Archivados: {len(df)}')
if len(df) > 0:
    for i, r in df.head(10).iterrows():
        print(f"[{r['id']}] {r['nombre']} {r['apellido']} | CC: {r['cc_nombre']} | C1: {r['c1']} | C2: {r['c2']} | Estado: {r['estado']} | Gestion: {r.get('resultado_gestion', '')}")
conn.close()
