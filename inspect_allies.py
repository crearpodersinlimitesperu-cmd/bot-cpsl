import pandas as pd
import sys
sys.stdout.reconfigure(encoding='utf-8')

file_path = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2\ALIADOS C2 EQUIPO 18.xlsx"
try:
    df = pd.read_excel(file_path, sheet_name='PX')
    # Clean column names
    df.columns = [str(c).strip().upper() for c in df.columns]
    print(df[['NOMBRES', 'APELLIDOS', 'ALIADO']].dropna(subset=['NOMBRES']).head(15))
except Exception as e:
    print("Error reading file:", e)
