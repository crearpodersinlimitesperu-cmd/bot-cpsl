import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"

# Leer la hoja GRADUADOS
df = pd.read_excel(GRAD_PATH, sheet_name='GRADUADOS ')
print(f"Total filas en hoja 'GRADUADOS': {len(df)}")
print(f"Columnas: {list(df.columns)}")
print(f"\nPrimeras 5 filas:")
print(df.head(5).to_string())
print(f"\nÚltimas 5 filas:")
print(df.tail(5).to_string())

# Buscar columna de nombre para contar reales
primera_col = df.columns[0]
print(f"\nPrimera columna: '{primera_col}'")

# Contar filas NO vacías en cada columna para entender la estructura
print(f"\nConteo no-vacíos por columna:")
for col in df.columns[:8]:
    count = df[col].notna().sum()
    non_empty = df[col].astype(str).str.strip().ne('').sum() - df[col].isna().sum()
    print(f"  '{str(col)[:40]}': {count} no-NaN")

# Intentar identificar nombres reales (no headers, no vacíos)
# Buscar la columna que parece tener los nombres
for col in df.columns:
    col_str = str(col).lower()
    if any(kw in col_str for kw in ['nombre', 'creador', 'graduado', 'participante']):
        print(f"\nColumna clave encontrada: '{col}'")
        vals = df[col].dropna()
        print(f"  Valores no-NaN: {len(vals)}")
        # Filtrar headers repetidos
        vals_clean = vals[~vals.astype(str).str.contains('NOMBRE|CREADOR|GRADUADO|EQUIPO|^$', case=False, na=True)]
        print(f"  Valores limpios (sin headers): {len(vals_clean)}")
        print(f"  Primeros 5: {vals_clean.head().tolist()}")
        print(f"  Últimos 5: {vals_clean.tail().tolist()}")

# Contar graduados por equipo si hay columna de equipo
for col in df.columns:
    if 'equipo' in str(col).lower() or 'eq' in str(col).lower():
        print(f"\nDistribución por '{col}':")
        print(df[col].value_counts().to_string())

# Also check - where does 640 come from? Maybe it's summing MJ from multiple sheets
print(f"\n{'='*60}")
print("BUSCANDO ORIGEN DEL 640 — Contando MJ en todas las hojas")
print(f"{'='*60}")
xls = pd.ExcelFile(GRAD_PATH)
mj_total = 0
for sheet in xls.sheet_names:
    sheet_lower = sheet.lower()
    if 'mj' in sheet_lower or 'maestr' in sheet_lower:
        dfs = pd.read_excel(GRAD_PATH, sheet_name=sheet)
        clean = dfs.dropna(how='all')
        # Remove header rows (first 2 usually)
        data_rows = len(clean) - 2 if len(clean) > 2 else len(clean)
        mj_total += data_rows
        print(f"  '{sheet}': ~{data_rows} participantes")

print(f"\nTotal MJ sumando todas las hojas de apoyo MJ: ~{mj_total}")
print(f"\nGraduados reales (hoja GRADUADOS): {len(df.dropna(how='all'))}")
