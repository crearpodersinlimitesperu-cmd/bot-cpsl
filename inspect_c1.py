import pandas as pd
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

pattern = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\**\Asignacion_C1.xlsx"
files = glob.glob(pattern, recursive=True)
if not files:
    print("No files found!")
    sys.exit()

file_path = files[0]
print("Found file:", file_path)
try:
    xl = pd.ExcelFile(file_path)
    print("Sheet names:", xl.sheet_names)
    df = xl.parse(xl.sheet_names[0])
    print("Columns:", list(df.columns))
    print("First 15 rows:")
    print(df.head(15))
except Exception as e:
    print("Error reading file:", e)
