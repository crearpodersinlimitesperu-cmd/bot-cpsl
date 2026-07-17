import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT cc_nombre, count(id) FROM participantes WHERE cc_nombre LIKE '%zuley%' GROUP BY cc_nombre", conn)
print('Zuley pending cases:')
print(df)

df_c1c2 = pd.read_sql_query("SELECT count(id) FROM participantes WHERE c1 = 'SI' AND c2 = 'SI'", conn)
print('\nParticipants with C1 and C2 done:', df_c1c2.iloc[0,0])
conn.close()
