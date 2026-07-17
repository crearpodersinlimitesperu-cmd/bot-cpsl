import os
import pandas as pd
import logging
import time
import requests
from datetime import datetime

# Configuración
EXCEL_PATH = r"C:\Users\josem\Downloads\Asignacion_C1.xlsx"
COORDINADORES_FILTRO = ["jmarin", "dmoscoso"] # Joyce y Diana
TEMPLATE_NAME = "reactivacion_c1_e28" # Aprobada por Meta
TEMPLATE_LANG = "es"

# WhatsApp API config
WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_API = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("MasivoAsignacion")

def enviar_plantilla(tel, nombre):
    if not WA_TOKEN:
        logger.error("Sin WA_TOKEN")
        return False
        
    tel = str(tel).strip().replace(".0", "")
    if not tel.startswith("51"):
        tel = "51" + tel
        
    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(nombre).split()[0].title()}]
                }
            ]
        }
    }
    
    try:
        r = requests.post(WA_API, json=payload, headers={"Authorization": f"Bearer {WA_TOKEN}"}, timeout=15)
        if r.status_code in (200, 201):
            return True
        logger.error(f"Error {tel}: {r.text}")
        return False
    except Exception as e:
        logger.error(f"Excepción {tel}: {e}")
        return False

def procesar():
    logger.info(f"Leyendo Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    
    # Filtrar por coordinadores
    df_filtrado = df[df["Usuario Registro"].isin(COORDINADORES_FILTRO)]
    logger.info(f"Total registros: {len(df)} | Filtrados (Joyce/Diana): {len(df_filtrado)}")
    
    # PRUEBA DE SEGURIDAD: Solo los primeros 2
    df_prueba = df_filtrado.head(2)
    logger.info(f"--- MODO PRUEBA ACTIVO: Enviando solo a {len(df_prueba)} personas ---")
    
    exitos = 0
    fallidos = 0
    
    for i, row in df_prueba.iterrows():
        tel = row.get("TelefonoMovil")
        nom = row.get("NombreCompleto", "Participante")
        
        if not tel or pd.isna(tel):
            logger.warning(f"Fila {i} sin teléfono")
            continue
            
        logger.info(f"[{i+1}/{len(df_filtrado)}] Enviando a {nom} ({tel})...")
        if enviar_plantilla(tel, nom):
            exitos += 1
        else:
            fallidos += 1
            
        time.sleep(15) # Pausa para evitar bloqueos
        
    logger.info(f"Proceso terminado. Éxitos: {exitos}, Fallidos: {fallidos}")

if __name__ == "__main__":
    procesar()
