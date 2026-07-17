import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT imo, count(id) FROM participantes WHERE imo IS NOT NULL AND imo != '' GROUP BY imo ORDER BY count(id) DESC LIMIT 10", conn)
print(df)
conn.close()
