import os
import glob
import pandas as pd

onedrive_base = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
matches = glob.glob(os.path.join(onedrive_base, "*Cambio de Cupo*28*.xlsx"))
if not matches:
    print("File not found!")
    exit(1)

filepath = matches[0]
df = pd.read_excel(filepath)

print(f"File: {os.path.basename(filepath)}")
print(f"Total Rows: {len(df)}")

# Print columns that are relevant
rel_cols = [
    'Id',
    'Nombre Completo del Aliado/QT (Tú):',
    'Nombre Completo del participante que SALE:',
    'DNI / Documento de Identidad del participante que SALE:',
    'Nombre Completo del NUEVO participante:',
    'DNI / Documento de Identidad del NUEVO participante:',
    'Teléfono Mívil (con código de país si es extranjero):',
    'Correo Electrónico Principal:(Asegúrate de que este correo esté escrito de manera precisa. Toda la comunicación oficial se enviará a esta dirección).',
    'Columna1'
]

# Map columns ignoring encoding issues by index
mapped_df = df.copy()
# Rename columns to make them easier to read
new_cols = {}
for col in df.columns:
    col_clean = col.encode('ascii', 'ignore').decode('utf-8').strip()
    # Let's map key columns
    if 'Completo del Aliado' in col:
        new_cols[col] = 'IMO_Nombre'
    elif 'DNI / CE:' in col:
        new_cols[col] = 'IMO_DNI'
    elif 'Contacto:' in col:
        new_cols[col] = 'IMO_Tel'
    elif 'participante que SALE' in col:
        new_cols[col] = 'Sale_Nombre'
    elif 'SALE:' in col and ('DNI' in col or 'Documento' in col):
        new_cols[col] = 'Sale_DNI'
    elif 'NUEVO participante' in col:
        new_cols[col] = 'Nuevo_Nombre'
    elif 'NUEVO participante:' in col and ('DNI' in col or 'Documento' in col):
        new_cols[col] = 'Nuevo_DNI'
    elif 'Mvil' in col_clean or 'Movil' in col_clean or 'Telefono' in col_clean:
        new_cols[col] = 'Nuevo_Tel'
    elif 'Correo Electronico Principal' in col_clean or 'Correo' in col_clean and 'Principal' in col_clean:
        new_cols[col] = 'Nuevo_Email'
    elif 'Columna1' in col:
        new_cols[col] = 'Resultado'

mapped_df = mapped_df.rename(columns=new_cols)

print("\nAvailable columns after mapping:")
print(mapped_df.columns.tolist())

# Select mapped columns if they exist
show_cols = [c for c in ['Id', 'IMO_Nombre', 'Sale_Nombre', 'Sale_DNI', 'Nuevo_Nombre', 'Nuevo_DNI', 'Nuevo_Tel', 'Nuevo_Email', 'Resultado'] if c in mapped_df.columns]
print("\nTable data:")
pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(mapped_df[show_cols])

print("\nValue counts for 'Resultado':")
if 'Resultado' in mapped_df.columns:
    print(mapped_df['Resultado'].value_counts(dropna=False))
