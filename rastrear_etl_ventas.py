import os
import pandas as pd
from pathlib import Path

# Ruta ETL
ETL_BASE = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\ETL - VENTAS CREAR LIMA - Documentos")

def rastrear_venta():
    print(f"--- INICIANDO RASTREO EN ETL: {ETL_BASE} ---")
    if not ETL_BASE.exists():
        print("La ruta de OneDrive no es accesible localmente.")
        return

    hallazgos = []
    for root, dirs, files in os.walk(ETL_BASE):
        for f in files:
            if f.lower().endswith(('.xlsx', '.xls', '.csv')):
                full_path = Path(root) / f
                try:
                    if f.lower().endswith('.csv'):
                        df = pd.read_csv(full_path, low_memory=False)
                    else:
                        df = pd.read_excel(full_path)
                    
                    if df.astype(str).apply(lambda x: x.str.contains('MIRKO', case=False).any()).any():
                        print(f"!!! Hallazgo en ETL: {full_path}")
                        hallazgos.append(full_path)
                except:
                    continue
    
    if not hallazgos:
        print("No se encontró rastro de 'Cesar Mirko' en las carpetas de Ventas ETL.")
    else:
        print(f"\nTotal de archivos de venta detectados: {len(hallazgos)}")

if __name__ == "__main__":
    rastrear_venta()
