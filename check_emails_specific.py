import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
query = "SELECT email, es_pendiente_real, c1, c2 FROM participantes WHERE email LIKE '%sole201782%' OR email LIKE '%deivilozano%' OR email LIKE '%mqm0477%'"
df = pd.read_sql_query(query, conn)
print(df)
conn.close()
