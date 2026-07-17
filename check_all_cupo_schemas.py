import os
import glob
import pandas as pd

onedrive_base = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
files = glob.glob(os.path.join(onedrive_base, "**", "*Cambio de Cupo*.xlsx"), recursive=True)
files = [f for f in files if not os.path.basename(f).startswith("~$")]

print(f"Found {len(files)} files.")
for fpath in files:
    fname = os.path.basename(fpath)
    try:
        df = pd.read_excel(fpath)
        last_cols = list(df.columns[-3:])
        print(f"\nFile: {fname} (Rows: {len(df)})")
        print(f"  Last 3 columns: {last_cols}")
        for col in df.columns:
            if 'columna' in str(col).lower() or 'resultado' in str(col).lower() or 'apto' in str(col).lower() or 'estado' in str(col).lower():
                val_counts = df[col].value_counts(dropna=False).to_dict()
                print(f"  Column '{col}' value counts: {val_counts}")
    except Exception as e:
        print(f"  Error reading {fname}: {e}")
