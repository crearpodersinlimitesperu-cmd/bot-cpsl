import pandas as pd
import os

files = [
    r"c:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_2AÑOS.csv",
    r"c:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_SONIC.csv",
    r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv",
    r"c:\Users\josem\Downloads\bot-cpsl-review\REPORTE_REBOTES_SISTEMA_CREAR.xlsx"
]

for f in files:
    try:
        if os.path.exists(f):
            if f.endswith('.csv'):
                df = pd.read_csv(f, on_bad_lines='skip', nrows=1)
            else:
                df = pd.read_excel(f, nrows=1)
            print(f"{os.path.basename(f)} columns: {df.columns.tolist()}")
        else:
            print(f"File not found: {f}")
    except Exception as e:
        print(f"Error reading {f}: {e}")
