import pandas as pd
import glob
import sys
sys.stdout.reconfigure(encoding='utf-8')

pattern = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\**\ASISTENCIA CAP*LIMA*.xlsx"
files = glob.glob(pattern, recursive=True)
if not files:
    print("No files found!")
    sys.exit()

# Print all found files to choose
for i, f in enumerate(files):
    print(f"File {i}: {f}")

file_path = files[0]
print("Inspecting File:", file_path)
try:
    xl = pd.ExcelFile(file_path)
    print("Sheet names:", xl.sheet_names)
    df = xl.parse(xl.sheet_names[0])
    print("Columns of first sheet:", list(df.columns))
    print("First 10 rows:")
    print(df.head(10))
except Exception as e:
    print("Error reading file:", e)
