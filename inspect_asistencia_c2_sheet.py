import pandas as pd
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

pattern = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\**\ASISTENCIA CAP*LIMA*.xlsx"
files = glob.glob(pattern, recursive=True)
file_path = files[0]

try:
    xl = pd.ExcelFile(file_path)
    sheet_name = 'C2 #18 LIMA'
    print(f"Reading Sheet: {sheet_name}")
    df = xl.parse(sheet_name)
    print("Columns:", list(df.columns))
    print("First 15 rows:")
    print(df.head(15))
except Exception as e:
    print("Error reading file:", e)
