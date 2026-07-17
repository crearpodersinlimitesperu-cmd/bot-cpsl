import pandas as pd
import os

def check_file(path):
    print(f"\n--- Checking: {os.path.basename(path)} ---")
    try:
        df = pd.read_excel(path, nrows=5)
        print("Columns:", df.columns.tolist())
        print("Sample data:")
        print(df.head())
    except Exception as e:
        print("Error:", e)

def main():
    p1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1\ALIADOS CAPÍTULO UNO EQUIPO 26.xlsx"
    p2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2\ALIADOS C2 EQUIPO 26.xlsx"
    
    check_file(p1)
    check_file(p2)

if __name__ == "__main__":
    main()
