import pandas as pd

csv_path = r'C:\Users\josem\Downloads\participantes_2026-05-25.csv'
excel_path = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'

df_csv = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
df_excel = pd.read_excel(excel_path)

# Find the actual ID columns
id_col_csv = [c for c in df_csv.columns if 'identificac' in c.lower()][0]
id_col_excel = [c for c in df_excel.columns if 'identificac' in c.lower() and 'imo' not in c.lower()][0]

df_csv['Identificación_clean'] = df_csv[id_col_csv].astype(str).str.strip().str.replace('.0', '', regex=False)
df_excel['Identificación_clean'] = df_excel[id_col_excel].astype(str).str.strip().str.replace('.0', '', regex=False)

e28_csv = df_csv[df_csv['Equipo'].str.contains('28', na=False, case=False)]
print(f"Participantes E28 en CSV: {len(e28_csv)}")

merged = pd.merge(e28_csv, df_excel, on='Identificación_clean', how='inner')

print("Usuarios Actuales (Coordinadores) asignados:")
print(merged['Usuario Actual'].value_counts(dropna=False))

# Look up coordinators info
print("\nCoordinadores:")
for coord in ['jmarin', 'dmoscoso', 'jose']:
    print(coord)
