import easyocr
import pandas as pd
from pathlib import Path
import os

# Configuración
READER = None # Se inicializa en la primera corrida

def inicializar_ocr():
    global READER
    print("Cargando modelos de lenguaje para OCR (Español)...")
    READER = easyocr.Reader(['es'], verbose=False)

def procesar_imagen_ocr(ruta_imagen):
    if READER is None:
        inicializar_ocr()
    
    print(f"Leyendo: {Path(ruta_imagen).name}")
    try:
        results = READER.readtext(ruta_imagen, detail=0)
        return " ".join(results)
    except Exception as e:
        return f"Error: {e}"

def auditoria_masiva_ocr(limite=10):
    print(f"--- INICIANDO ESCANEO OCR (Muestra de {limite}) ---")
    
    # Cargar vinculaciones previas o inventario
    df_vinc = pd.read_csv("EVIDENCIAS_VINCULADAS_POR_NOMBRE.csv").head(limite)
    
    resultados_ocr = []
    for _, row in df_vinc.iterrows():
        texto_extraido = procesar_imagen_ocr(row['ruta_completa'])
        resultados_ocr.append({
            "px_id": row['px_id'],
            "nombre_px": row['nombre_px'],
            "archivo": row['archivo'],
            "texto_ocr": texto_extraido
        })
    
    df_res = pd.DataFrame(resultados_ocr)
    df_res.to_csv("RESULTADOS_OCR_MUESTRA.csv", index=False)
    print("Escaneo de muestra completado. Reporte: RESULTADOS_OCR_MUESTRA.csv")
    print(df_res[['nombre_px', 'texto_ocr']].head(5).to_string())

if __name__ == "__main__":
    auditoria_masiva_ocr(10)
