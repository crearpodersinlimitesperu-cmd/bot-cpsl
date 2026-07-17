import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT id, nombre, apellido, cc_nombre, c1, c2, resultado_gestion, notas_gestion FROM participantes WHERE cc_nombre LIKE '%otty%' OR cc_nombre LIKE '%oty%'", conn)
print(f"Casos de Otty: {len(df)}")
if len(df) > 0:
    print(df.head(10))
