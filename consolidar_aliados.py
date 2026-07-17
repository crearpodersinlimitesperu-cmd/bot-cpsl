import os
import glob
import pandas as pd
import sqlite3

def consolidate_aliados():
    print("Consolidando Aliados C1 y C2...")
    
    path_c1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1\*.xlsx"
    path_c2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2\*.xlsx"
    
    # Consolidar C1
    dfs_c1 = []
    for file in glob.glob(path_c1):
        try:
            df = pd.read_excel(file)
            # C1 format varies, but columns might be Unnamed
            # Let's try to extract DNI, phone, names if possible
            # To be safe, we just concat them with a 'source' column
            df['Fuente'] = os.path.basename(file)
            df['Capitulo'] = 'C1'
            dfs_c1.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            
    # Consolidar C2
    dfs_c2 = []
    for file in glob.glob(path_c2):
        try:
            df = pd.read_excel(file)
            df['Fuente'] = os.path.basename(file)
            df['Capitulo'] = 'C2'
            dfs_c2.append(df)
        except Exception as e:
            print(f"Error reading {file}: {e}")

    # Instead of complex merging of unstructured C1, we'll save raw combined files for the user to review,
    # and a structured DB update if possible.
    master_c1 = pd.concat(dfs_c1, ignore_index=True) if dfs_c1 else pd.DataFrame()
    master_c2 = pd.concat(dfs_c2, ignore_index=True) if dfs_c2 else pd.DataFrame()
    
    output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Master_Aliados_Consolidado.xlsx"
    with pd.ExcelWriter(output_path) as writer:
        if not master_c1.empty:
            master_c1.to_excel(writer, sheet_name='C1_Raw', index=False)
        if not master_c2.empty:
            master_c2.to_excel(writer, sheet_name='C2_Raw', index=False)
            
    print(f"Consolidado guardado en {output_path}")

if __name__ == "__main__":
    consolidate_aliados()
