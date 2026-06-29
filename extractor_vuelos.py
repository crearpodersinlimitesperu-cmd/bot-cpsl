import os
import re
import json
from pypdf import PdfReader
from google import genai
from google.genai import types
from dotenv import load_dotenv
from dotenv import load_dotenv
load_dotenv()

# We expect the GOOGLE_AI_KEY to be in the environment.
API_KEY = os.environ.get("GOOGLE_AI_KEY")
if not API_KEY:
    print("WARNING: GOOGLE_AI_KEY is not set in the environment.")

def extraer_datos_vuelo_ia(pdf_path):
    """
    Extrae nombre, reserva y detalles de los vuelos de llegada y salida a/desde Lima (LIM),
    desde un PDF utilizando IA (Gemini 2.5 Flash), sin importar el formato o la aerolínea.
    """
    try:
        reader = PdfReader(pdf_path)
        text_content = ""
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
    except Exception as e:
        print(f"Error leyendo el PDF {pdf_path}: {e}")
        return None

    if not text_content.strip():
        print("El PDF parece estar vacío o es una imagen sin texto OCR.")
        return None

    # Inicializar el cliente de Gemini
    client = genai.Client(api_key=API_KEY)
    
    prompt = f"""
    Eres un asistente experto en logística y reservas de vuelos.
    A continuación, te entregaré el texto extraído de un boleto de avión, pasaje o factura.
    Tu tarea es extraer los datos clave y devolverlos ESTRICTAMENTE en formato JSON.
    
    Reglas críticas para la extracción:
    1. "nombre": El nombre del pasajero principal (Adulto).
    2. "reserva": El código de reserva o PNR (Booking Code) de la aerolínea (normalmente 6 caracteres alfanuméricos).
    3. Para el "vuelo_llegada": Debes encontrar el último tramo del viaje de ida que tiene como DESTINO FINAL Lima (LIM), Perú. No importa cuántas escalas haya hecho antes. Extrae la fecha, la hora de LLEGADA a Lima, la aerolínea operadora y el código de reserva de ese tramo.
    4. Para el "vuelo_salida": Debes encontrar el primer tramo del viaje de regreso que tiene como ORIGEN Lima (LIM), Perú. Extrae la fecha, la hora de SALIDA de Lima, la aerolínea operadora y el código de reserva de ese tramo.
    5. Fechas deben estar en formato DD/MM/YY. Horas en formato HH:MM (24 horas).
    
    Estructura JSON EXACTA esperada:
    {{
        "nombre": "NOMBRES APELLIDOS",
        "reserva": "CODIGO",
        "vuelo_llegada": {{
            "fecha": "DD/MM/YY",
            "hora": "HH:MM",
            "aerolinea": "Nombre Aerolinea",
            "referencia": "CODIGO"
        }},
        "vuelo_salida": {{
            "fecha": "DD/MM/YY",
            "hora": "HH:MM",
            "aerolinea": "Nombre Aerolinea",
            "referencia": "CODIGO"
        }}
    }}
    
    Si el pasajero solo tiene vuelo de ida, simplemente omite la clave "vuelo_salida". Lo mismo si solo tiene vuelo de regreso (omite "vuelo_llegada").
    Si algún dato no se puede encontrar, asígnale el valor null.
    No devuelvas ningún texto extra, bloques de markdown (```json ... ```) ni comentarios, SOLO el JSON puro.
    
    TEXTO DEL BOLETO:
    {text_content}
    """
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        # Limpiar la respuesta para asegurar que es un JSON válido
        respuesta_limpia = response.text.strip()
        if respuesta_limpia.startswith("```json"):
            respuesta_limpia = respuesta_limpia[7:]
        if respuesta_limpia.startswith("```"):
            respuesta_limpia = respuesta_limpia[3:]
        if respuesta_limpia.endswith("```"):
            respuesta_limpia = respuesta_limpia[:-3]
            
        respuesta_limpia = respuesta_limpia.strip()
        datos_json = json.loads(respuesta_limpia)
        return datos_json
    except Exception as e:
        print(f"Error procesando el PDF con Gemini: {e}")
        return None

# Mantenemos un alias hacia la función original para compatibilidad con código existente
extraer_datos_factura_latam = extraer_datos_vuelo_ia

if __name__ == "__main__":
    test_file = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS\LA5448499XKKO-30b3c0de-6663-4870-acc3-141995d50c8a-cuv-bill.pdf"
    print("Probando el extractor universal (IA de Gemini)...")
    resultado = extraer_datos_vuelo_ia(test_file)
    print(json.dumps(resultado, indent=4, ensure_ascii=False))
