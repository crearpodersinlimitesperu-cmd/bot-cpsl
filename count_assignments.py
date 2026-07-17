import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT cc_nombre, COUNT(*) as total FROM participantes GROUP BY cc_nombre", conn)
print(df)
conn.close()
