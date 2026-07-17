import os
import glob
import pandas as pd

onedrive_base = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
e28_path = os.path.join(onedrive_base, "Solicitud de Cambio de Cupo _ C1 - Equipo 28-  MAYO 29,30 y 31 2026.xlsx")

# Check if the specific E28 file exists
print("=== CHECKING E28 FILE ===")
print(f"Path: {e28_path}")
exists = os.path.exists(e28_path)
print(f"Exists? {exists}")

if not exists:
    # Let's search using glob
    print("Searching for similar files in OneDrive...")
    matches = glob.glob(os.path.join(onedrive_base, "*Cambio de Cupo*28*.xlsx"))
    print(f"Found matches: {matches}")
    if not matches:
        matches_all = glob.glob(os.path.join(onedrive_base, "**", "*Cambio de Cupo*.xlsx"), recursive=True)
        print(f"All Cambio de Cupo files: {matches_all}")
    if matches:
        e28_path = matches[0]
        exists = True

if exists:
    try:
        xls = pd.ExcelFile(e28_path)
        print(f"Sheets: {xls.sheet_names}")
        df = pd.read_excel(e28_path, sheet_name=xls.sheet_names[0])
        print(f"Shape: {df.shape}")
        print("Columns:")
        for i, col in enumerate(df.columns):
            print(f"  {i}: {col}")
        
        # Look for "apto" column or value
        print("\nChecking first few rows:")
        print(df.head(2))
    except Exception as e:
        print(f"Error reading E28 file: {e}")

# Check Aliados C1/C2 folders
print("\n=== CHECKING ALIADOS FOLDERS ===")
dir_c1 = os.path.join(onedrive_base, "CREAR LIMA", "PORCENTAJE ALIADOS C1")
dir_c2 = os.path.join(onedrive_base, "CREAR LIMA", "PORCENTAJE ALIADOS C2")

print(f"C1 Directory: {dir_c1} (Exists: {os.path.exists(dir_c1)})")
print(f"C2 Directory: {dir_c2} (Exists: {os.path.exists(dir_c2)})")

if os.path.exists(dir_c1):
    c1_files = glob.glob(os.path.join(dir_c1, "*.xlsx"))
    print(f"C1 Files ({len(c1_files)}):")
    for f in c1_files[:10]:
        print(f"  {os.path.basename(f)}")
        
if os.path.exists(dir_c2):
    c2_files = glob.glob(os.path.join(dir_c2, "*.xlsx"))
    print(f"C2 Files ({len(c2_files)}):")
    for f in c2_files[:10]:
        print(f"  {os.path.basename(f)}")
