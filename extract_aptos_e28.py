import os
import glob
import pandas as pd

onedrive_base = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
matches = glob.glob(os.path.join(onedrive_base, "*Cambio de Cupo*28*.xlsx"))
if not matches:
    print("Error: No se encontró el archivo del Equipo 28 en OneDrive.")
    exit(1)

filepath = matches[0]
df = pd.read_excel(filepath)

# Encontrar columna de estado (literalmente Columna1)
col_status = None
for col in df.columns:
    if str(col).lower().strip() == 'columna1':
        col_status = col
        break

# Si no la encuentra como 'columna1', buscar si hay una columna llamada 'resultado' o 'estado' (búsqueda estricta)
if not col_status:
    for col in df.columns:
        if str(col).lower().strip() in ['resultado', 'estado', 'status']:
            col_status = col
            break

# Filtrar para tomar solo los APTOS (los que NO están marcados como 'NO APTO')
if col_status:
    df_aptos = df[df[col_status].astype(str).str.upper().str.strip() != 'NO APTO'].copy()
    df_no_aptos = df[df[col_status].astype(str).str.upper().str.strip() == 'NO APTO'].copy()
else:
    df_aptos = df.copy()
    df_no_aptos = pd.DataFrame()

# Mapear columnas para exportación limpia
new_cols = {}
for col in df.columns:
    col_clean = col.encode('ascii', 'ignore').decode('utf-8').strip()
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
    elif str(col).lower().strip() == 'columna1':
        new_cols[col] = 'Resultado'

df_aptos_mapped = df_aptos.rename(columns=new_cols)

# Guardar a CSV
output_csv = r"C:\Users\josem\Downloads\bot-cpsl-review\Aptos_E28_Cambio_Cupo.csv"
df_aptos_mapped.to_csv(output_csv, index=False, encoding='utf-8-sig')

print("="*60)
print(f"EXTRACCIÓN DE APTOS - EQUIPO 28 - CAMBIO DE CUPO (CORREGIDO)")
print(f"Archivo Origen: {os.path.basename(filepath)}")
print(f"Total de registros en el archivo: {len(df)}")
print(f"Registros APTOS (Aceptados/Pendientes): {len(df_aptos_mapped)}")
print(f"Registros NO APTOS (Excluidos): {len(df_no_aptos)}")
print(f"Reporte exportado a: {output_csv}")
print("="*60)

if len(df_aptos_mapped) > 0:
    show_cols = [c for c in ['Id', 'IMO_Nombre', 'Sale_Nombre', 'Sale_DNI', 'Nuevo_Nombre', 'Nuevo_DNI', 'Nuevo_Tel', 'Nuevo_Email', 'Resultado'] if c in df_aptos_mapped.columns]
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print("\nDetalle de Participantes APTOS:")
    print(df_aptos_mapped[show_cols].to_string(index=False))
else:
    print("\nNo se encontraron participantes APTOS.")
