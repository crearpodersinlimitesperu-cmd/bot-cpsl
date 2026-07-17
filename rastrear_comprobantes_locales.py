import pandas as pd
import PyPDF2
import os
from pathlib import Path

# Ruta
BASE_PATH = Path(r"C:\Users\josem\Downloads\Facturas y Pagos")

def buscar_evidencia():
    print(f"--- RASTREANDO COMPROBANTES EN: {BASE_PATH} ---")
    if not BASE_PATH.exists():
        print("La ruta no existe.")
        return

    encontrados = []
    for f in os.listdir(BASE_PATH):
        full_path = BASE_PATH / f
        # Escaneo Excel
        if f.lower().endswith(('.xlsx', '.xls')):
            try:
                df = pd.read_excel(full_path)
                if df.astype(str).apply(lambda x: x.str.contains('MIRKO', case=False).any()).any():
                    print(f"!!! Hallazgo en Excel: {f}")
                    encontrados.append(f)
            except:
                continue
        
        # Escaneo PDF
        elif f.lower().endswith('.pdf'):
            try:
                with open(full_path, 'rb') as pdf_file:
                    reader = PyPDF2.PdfReader(pdf_file)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text()
                    if 'MIRKO' in text.upper():
                        print(f"!!! Hallazgo en PDF: {f}")
                        encontrados.append(f)
            except:
                continue

    if not encontrados:
        print("No se encontró rastro de 'Cesar Mirko' en la carpeta de Facturas y Pagos.")
    else:
        print(f"\nTotal de archivos con evidencia: {len(encontrados)}")

if __name__ == "__main__":
    buscar_evidencia()
