import sqlite3
import pandas as pd
conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
df = pd.read_sql_query("SELECT nombre, apellido, email FROM participantes WHERE email LIKE '%atlanticcity%'", conn)
print(df)
conn.close()
