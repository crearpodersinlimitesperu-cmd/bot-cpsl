import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
df = pd.read_excel(file_path, sheet_name=0)

print(f"Total de filas: {len(df)}")
print(f"Columnas ({len(df.columns)}): {df.columns.tolist()}")

# Mostrar unas filas de ejemplo para entender las gestiones múltiples
# Busquemos un DNI que se repita
dup_dnis = df[df.duplicated('Identificación', keep=False)]
if not dup_dnis.empty:
    dni_ejemplo = dup_dnis['Identificación'].iloc[0]
    print(f"\nEjemplo de participante duplicado (DNI: {dni_ejemplo}):")
    print(df[df['Identificación'] == dni_ejemplo].to_string())
else:
    print("\nNo se encontraron DNI duplicados.")
