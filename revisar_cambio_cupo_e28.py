import pandas as pd
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

files = glob.glob(r'C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\*Cambio*28*')
FILE_PATH = files[0]

df = pd.read_excel(FILE_PATH, sheet_name='Sheet1')
print(f"Total solicitudes: {len(df)}")
print(f"Columnas: {list(df.columns)[:15]}")

# Find the status column
status_col = None
for col in df.columns:
    vals = df[col].dropna().astype(str)
    if vals.str.contains('APTO|USADO|NO APTO', case=False, na=False).any():
        status_col = col
        break

print(f"\nColumna de estado: '{status_col}'")

# Map each solicitud with its status and new participant details
print(f"\n{'='*65}")
print(f"  DETALLE POR SOLICITUD")
print(f"{'='*65}")

# Column mapping based on what we saw:
# Col 5 = IMO name, Col 6 = IMO DNI, Col 7 = Equipo IMO
# We need to find the NEW participant columns
for idx, row in df.iterrows():
    imo_nombre = str(row.iloc[5]) if pd.notna(row.iloc[5]) else ""
    estado = str(row.get(status_col, "")) if status_col else ""
    
    # Look for new participant data in remaining columns
    # The form has fields for the NEW participant
    all_vals = {}
    for i, col in enumerate(df.columns):
        v = row[col]
        if pd.notna(v):
            s = str(v).strip()
            if s and len(s) > 1:
                all_vals[f"Col{i}_{str(col)[:30]}"] = s[:60]
    
    if imo_nombre and imo_nombre != 'nan':
        status_emoji = "✅" if "USADO" in estado.upper() else ("❌" if "NO APTO" in estado.upper() else "⏳")
        print(f"\n  {status_emoji} Solicitud #{idx}")
        print(f"     Estado: {estado}")
        for k, v in all_vals.items():
            col_name = k.split('_', 1)[1] if '_' in k else k
            if 'Acepto' not in v and 'anónim' not in v.lower() and 'anonymous' not in v.lower():
                print(f"     {col_name}: {v}")

# Summary
if status_col:
    print(f"\n{'='*65}")
    print(f"  RESUMEN")
    print(f"{'='*65}")
    print(df[status_col].value_counts().to_string())
    
    usados = df[df[status_col].astype(str).str.upper() == 'USADO']
    no_aptos = df[df[status_col].astype(str).str.upper() == 'NO APTO']
    sin_estado = df[df[status_col].isna() | (df[status_col].astype(str).str.strip() == '')]
    
    print(f"\n  USADOS (aprobados): {len(usados)}")
    print(f"  NO APTOS: {len(no_aptos)}")
    print(f"  Sin estado: {len(sin_estado)}")
