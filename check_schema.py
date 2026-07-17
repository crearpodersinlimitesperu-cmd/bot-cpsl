import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("PRAGMA table_info(participantes);", conn)
print(df['name'].tolist())
conn.close()
