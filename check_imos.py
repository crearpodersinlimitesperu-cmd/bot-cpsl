import pandas as pd
import sqlite3

csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
df = pd.read_csv(csv_path)

print("Columnas en CSV:", df.columns.tolist())

# Buscar correos de IMOs en la base de datos de participantes
conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db')
cursor = conn.cursor()

imo_ids = df['IdentificacionIMO'].dropna().unique().tolist()
placeholders = ','.join('?' * len(imo_ids))
query = f"SELECT identificacion, nombre, email, telefono FROM participantes WHERE identificacion IN ({placeholders})"
cursor.execute(query, imo_ids)
imo_data = cursor.fetchall()

print(f"IMOs encontrados en BD: {len(imo_data)} de {len(imo_ids)}")
print("Ejemplos:", imo_data[:5])
