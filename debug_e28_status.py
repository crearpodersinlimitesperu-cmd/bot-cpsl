import os
import glob
import pandas as pd

onedrive_base = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
matches = glob.glob(os.path.join(onedrive_base, "*Cambio de Cupo*28*.xlsx"))
filepath = matches[0]
df = pd.read_excel(filepath)

print("Columns in Excel:")
print(list(df.columns))

# Let's find Columna1
col_status = None
for col in df.columns:
    if 'columna1' in str(col).lower() or 'resultado' in str(col).lower():
        col_status = col
        break

print(f"\nFound status column: '{col_status}'")
if col_status:
    print("\nValue representations:")
    for idx, val in enumerate(df[col_status]):
        print(f"Row {idx}: {repr(val)} | type: {type(val)} | equal to 'NO APTO'? {str(val).strip().upper() == 'NO APTO'}")
        
    print("\nFiltered df row count:")
    df_filtered = df[df[col_status].astype(str).str.upper().str.strip() != 'NO APTO']
    print(f"Filtered rows count: {len(df_filtered)}")
    print(df_filtered)
