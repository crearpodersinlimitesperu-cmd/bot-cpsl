import easyocr
import os

try:
    print("Inicializando EasyOCR (esto descargará los modelos si es la primera vez)...")
    reader = easyocr.Reader(['es', 'en'], gpu=False)
    print("¡EasyOCR inicializado correctamente!")
except Exception as e:
    print(f"Error inicializando EasyOCR: {e}")
