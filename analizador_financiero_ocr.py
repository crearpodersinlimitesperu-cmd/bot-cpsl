import os
import easyocr
import pandas as pd
import re
import cv2
import numpy as np
import time

print("Inicializando Analizador Financiero OCR...")
reader = easyocr.Reader(['es', 'en'], gpu=False)
print("Motor OCR Listo.")

# Diccionario de precios (redondeados a entero) extraídos de PRECIOS CREAR LIMA 2025.xlsx
# Formato: Monto (INT) -> Tipo de Entrenamiento Asignado
price_map = {
    # CAPITULO UNO (Soles y Dólares)
    1515: "CAPÍTULO UNO", 720: "CAPÍTULO UNO / MAESTRÍA", 480: "CAPÍTULO UNO", 
    615: "CAPÍTULO UNO", 900: "CAPÍTULO UNO", 505: "CAPÍTULO UNO",
    420: "CAPÍTULO UNO", 200: "CAPÍTULO UNO / CAMINATA", 135: "CAPÍTULO UNO", 
    170: "CAPÍTULO UNO", 250: "CAPÍTULO UNO", 140: "CAPÍTULO UNO",
    
    # CAPITULO DOS (Soles y Dólares)
    1875: "CAPÍTULO DOS", 2160: "CAPÍTULO DOS", 2790: "CAPÍTULO DOS",
    520: "CAPÍTULO DOS", 600: "CAPÍTULO DOS", 775: "CAPÍTULO DOS",
    
    # CAPITULO 1 + 2
    2595: "CAPÍTULO 1+2 / MAESTRÍA", 2250: "CAPÍTULO 1+2",
    625: "CAPÍTULO 1+2",
    
    # MAESTRIA DEL JUEGO
    3185: "MAESTRÍA DEL JUEGO", 1655: "MAESTRÍA DEL JUEGO", 2000: "MAESTRÍA DEL JUEGO", 
    2195: "MAESTRÍA DEL JUEGO", 2395: "MAESTRÍA DEL JUEGO",
    885: "MAESTRÍA DEL JUEGO", 465: "MAESTRÍA DEL JUEGO", 555: "MAESTRÍA DEL JUEGO", 
    610: "MAESTRÍA DEL JUEGO", 665: "MAESTRÍA DEL JUEGO",
    
    # CAPITULO 2 + MAESTRIA
    3530: "CAPÍTULO 2 + MAESTRÍA",
    980: "CAPÍTULO 2 + MAESTRÍA",
    
    # PROCESO COMPLETO
    4250: "PROCESO COMPLETO", 4000: "PROCESO COMPLETO",
    1180: "PROCESO COMPLETO", 1110: "PROCESO COMPLETO"
}

def extract_financials(image_path):
    try:
        # Evitar fallos de Unicode en cv2
        with open(image_path, 'rb') as f:
            img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
        results = reader.readtext(img, detail=0)
        full_text = " ".join(results).replace(',', '') # Quitar comas (ej. 1,515.00)
        
        # Buscar números con o sin decimales
        # ej. 1515.00, 1515, 720.50
        number_matches = re.findall(r'\b(\d{3,4}(?:\.\d{1,2})?)\b', full_text)
        
        detected_prices = []
        for match in number_matches:
            try:
                val = int(float(match))
                if val in price_map:
                    detected_prices.append(val)
            except ValueError:
                pass
                
        if detected_prices:
            # Si hay varios, tomamos el mayor (asumiendo que es el Total Pagado y no un subtotal parcial)
            max_val = max(detected_prices)
            return max_val, price_map[max_val]
            
    except Exception as e:
        print(f"Error procesando {image_path}: {e}")
        
    return None, "NO DETECTADO / ABONO PARCIAL"

def scan_receipts():
    comprobantes_dir = "C:/Users/josem/OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA/CREAR LIMA - 02. Comprobantes"
    report_path = os.path.join(comprobantes_dir, "Reporte_Pagos_OCR.xlsx")
    
    print("Catalogando imágenes de comprobantes...")
    image_catalog = []
    for root, dirs, files in os.walk(comprobantes_dir):
        if "FICHAS" in root: continue
        for file in files:
            if file.lower().endswith(('.jpeg', '.jpg', '.png')):
                image_catalog.append((os.path.splitext(file)[0], os.path.join(root, file)))
                
    print(f"Se encontraron {len(image_catalog)} comprobantes de imagen. Iniciando lectura OCR financiera...")
    
    resultados = []
    
    start_time = time.time()
    
    for i, (nombre, path) in enumerate(image_catalog):
        print(f"[{i+1}/{len(image_catalog)}] Analizando: {nombre}")
        monto, entrenamiento = extract_financials(path)
        
        resultados.append({
            "Archivo Comprobante": nombre,
            "Ruta": path,
            "Monto Detectado": monto if monto else "No legible / No en tabla",
            "Entrenamiento Asignado": entrenamiento
        })
        
        # Guardar progreso parcial cada 50 comprobantes por seguridad
        if (i + 1) % 50 == 0:
            df_temp = pd.DataFrame(resultados)
            df_temp.to_excel(report_path, index=False)
            
    df_final = pd.DataFrame(resultados)
    df_final.to_excel(report_path, index=False)
    
    end_time = time.time()
    mins = (end_time - start_time) / 60
    print(f"\n¡Proceso Completado en {mins:.1f} minutos!")
    print(f"Reporte guardado en: {report_path}")

if __name__ == "__main__":
    scan_receipts()
