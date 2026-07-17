import pandas as pd
from pathlib import Path

# Ruta al archivo detectado
FILE_PATH = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\ETL - VENTAS CREAR LIMA - Documentos\2025\09. SEPTIEMBRE\01. CIERRES DE CAJA\02. E21-CAPÍTULO 01\BASE DE E21-CAPÍTULO 01.xlsx")

def extraer_detalle():
    print(f"--- EXTRAYENDO DETALLE DE: {FILE_PATH.name} ---")
    try:
        df = pd.read_excel(FILE_PATH)
        # Buscar a Mirko
        mask = df.apply(lambda row: row.astype(str).str.contains('MIRKO', case=False).any(), axis=1)
        result = df[mask]
        
        if not result.empty:
            print("\nResultado Encontrado:")
            print(result.to_string())
            # Guardar en un CSV temporal para que el usuario pueda verlo si lo desea
            result.to_csv("DETALLE_CESAR_MIRKO_ORIGEN.csv", index=False)
        else:
            print("No se encontró a Mirko dentro del archivo de Cierre de Caja.")
    except Exception as e:
        print(f"Error al leer el archivo: {e}")

if __name__ == "__main__":
    extraer_detalle()
