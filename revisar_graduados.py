import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"

# Leer todas las hojas
xls = pd.ExcelFile(GRAD_PATH)
print(f"Hojas disponibles: {xls.sheet_names}")

for sheet in xls.sheet_names:
    df = pd.read_excel(GRAD_PATH, sheet_name=sheet)
    print(f"\n{'='*60}")
    print(f"HOJA: '{sheet}' — {len(df)} filas")
    print(f"Columnas: {list(df.columns)[:10]}")
    
    # Contar filas no vacías (que tengan nombre)
    nombre_cols = [c for c in df.columns if 'nombre' in str(c).lower() or 'name' in str(c).lower() or c == df.columns[0]]
    if nombre_cols:
        col = nombre_cols[0]
        no_vacias = df[df[col].notna() & (df[col].astype(str).str.strip() != '')]
        print(f"Filas con datos en '{col}': {len(no_vacias)}")
    
    # Show first few rows
    print(f"Primeras 3 filas:")
    print(df.head(3).to_string())

# Specifically check for "graduados" or "MJ" sheets
print(f"\n{'='*60}")
print("ANÁLISIS DETALLADO DE GRADUADOS")
print(f"{'='*60}")

for sheet in xls.sheet_names:
    df = pd.read_excel(GRAD_PATH, sheet_name=sheet)
    # Count non-empty rows properly
    # Drop rows where ALL values are NaN
    df_clean = df.dropna(how='all')
    # Also drop header-like rows if any
    print(f"\n  '{sheet}': {len(df_clean)} filas con datos (de {len(df)} total)")
    
    # Check if there's a status column
    for col in df.columns:
        col_str = str(col).lower()
        if any(kw in col_str for kw in ['status', 'estado', 'graduado', 'mj', 'maestr']):
            print(f"    Columna '{col}': {df[col].value_counts().head(5).to_string()}")
