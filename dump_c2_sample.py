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
    df = xl.parse(sheet_name)
    # Print the row at index 0 which contains the actual headers
    print("Row 0:", list(df.iloc[0].values))
    print("Columns:", list(df.columns))
    # Print first 10 rows
    print(df.iloc[1:10, 0:6])
except Exception as e:
    print("Error reading file:", e)
