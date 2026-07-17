import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

files = [
    r'C:\Users\josem\Downloads\reporte_equipos.xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (1).xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (2).xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (3).xlsx',
]

for f in files:
    print(f"\n{'='*80}")
    print(f"ARCHIVO: {f.split(chr(92))[-1]}")
    print('='*80)
    try:
        df = pd.read_excel(f)
        print(f"Filas: {len(df)} | Columnas: {len(df.columns)}")
        print(f"Columnas: {df.columns.tolist()}")
        print(f"\nPrimeras 3 filas:")
        print(df.head(3).to_string())
    except Exception as e:
        print(f"ERROR: {e}")
