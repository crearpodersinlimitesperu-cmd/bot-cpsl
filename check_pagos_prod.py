import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
df = pd.read_excel(file_path, sheet_name=0)

df['Fecha Gestión'] = pd.to_datetime(df['Fecha Gestión'], errors='coerce')
df = df.sort_values(by='Fecha Gestión', ascending=False)
df_unicos = df.drop_duplicates(subset=['ClienteId'], keep='first').copy()
df_vacio = df_unicos[df_unicos['Asistencia'].isna()].copy()

print("Columnas disponibles:")
print(df_vacio.columns.tolist())

for col in ['Pago Capítulo2', 'Pago Maestría']:
    if col in df_vacio.columns:
        print(f"\nValores en {col}:")
        print(df_vacio[col].value_counts(dropna=False).to_string())
