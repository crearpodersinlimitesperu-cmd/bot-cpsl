import os, re, json, time, logging
import pandas as pd
import requests as req_lib

# Configuración
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("Lanzamiento_E28")

WA_TOKEN = os.environ.get("WA_TOKEN", "") # Se espera que esté en el ambiente
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")
TEMPLATE_NAME = "reactivacion_c1_e28"
EXCEL_PATH = r"C:\Users\josem\Downloads\Asignacion_C1.xlsx"

def formatear_nombre(texto):
    if not texto or str(texto).lower() == "nan": return "Participante"
    # Si viene como "APELLIDO, NOMBRE"
    if "," in texto:
        return texto.split(",")[1].strip().split()[0].title()
    # Si viene como "NOMBRE APELLIDO" o "APELLIDO APELLIDO NOMBRE"
    tokens = str(texto).split()
    if len(tokens) >= 3: # Asumimos APELLIDO APELLIDO NOMBRE...
        return tokens[2].title()
    return tokens[0].title()

def enviar_template(tel, nombre):
    url = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"}
    
    # Limpiar teléfono
    tel = re.sub(r'[^\d]', '', str(tel))
    if not tel.startswith("51"): tel = "51" + tel
    
    nombre_clean = formatear_nombre(nombre)
    
    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": nombre_clean}
                ]
            }]
        }
    }
    
    try:
        r = req_lib.post(url, json=payload, headers=headers, timeout=15)
        if r.status_code in (200, 201):
            log.info(f"✅ Enviado a {nombre_clean} ({tel})")
            return True
        else:
            log.error(f"❌ Error {r.status_code} en {tel}: {r.text}")
            return False
    except Exception as e:
        log.error(f"💥 Excepción en {tel}: {e}")
        return False

def main():
    if not WA_TOKEN:
        log.error("WA_TOKEN no encontrado en variables de entorno.")
        return

    if not os.path.exists(EXCEL_PATH):
        log.error(f"Excel no encontrado en {EXCEL_PATH}")
        return

    log.info(f"Leyendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    # Filtrar solo Diana y Joyce
    # Columnas: 'Usuario Registro', 'NombreCompleto', 'TelefonoMovil'
    df_filtrado = df[df['Usuario Registro'].isin(['jmarin', 'dmoscoso'])]
    
    total = len(df_filtrado)
    log.info(f"Total de mensajes a enviar: {total} (Asignados a Diana y Joyce)")
    
    input("Presiona ENTER para iniciar el envío masivo...")
    
    enviados = 0
    for idx, row in df_filtrado.iterrows():
        tel = row['TelefonoMovil']
        nombre = row['NombreCompleto']
        
        if pd.isna(tel) or not str(tel).strip():
            log.warning(f"Fila {idx} sin teléfono. Saltando.")
            continue
            
        if enviar_template(tel, nombre):
            enviados += 1
            # Pausa para no saturar la API
            time.sleep(1.5)
            
    log.info(f"--- PROCESO FINALIZADO ---")
    log.info(f"Total enviados con éxito: {enviados} de {total}")

if __name__ == "__main__":
    main()
