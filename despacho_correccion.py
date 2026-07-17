"""
Módulo para el despacho masivo de mensajes de corrección de correo electrónico.
Utiliza el gateway de MacroDroid para notificar a los participantes cuyos correos rebotaron.
"""
import json
import sqlite3
import time
from pathlib import Path

import pandas as pd
import requests

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
CONFIG_PATH = BASE_DIR / "config_scanner.json"

def despachar_correccion_masiva():
    """
    Identifica participantes con correos rebotados y les envía un SMS
    solicitando la corrección de su dirección de email.
    """
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT nombre, telefono 
        FROM participantes 
        WHERE (email = 'REBOTE' OR estado_respuesta_sms = 'EMAIL_BOUNCED') 
          AND telefono IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()

    print(f"--- DESPACHO MASIVO DE CORRECCION ({len(df)} PAX) ---")

    url = f"https://trigger.macrodroid.com/{config['macrodroid']['device_id']}/{config['macrodroid']['event_name']}"
    exitosos = 0

    for _, row in df.iterrows():
        tel = str(row['telefono'])[-9:]
        # Limpiar cualquier caracter no numérico
        tel = "".join(filter(str.isdigit, tel))

        if len(tel) < 9:
            continue

        nombre = str(row['nombre']).split()[0].title()
        msg = (f"Hola {nombre}, de CREAR Global. 📩 Tu correo rebotó. "
               "Para mantener tu información de alto impacto, responde con tu email correcto. "
               "¡Tu transformación sigue aquí! ✨")

        print(f"Enviando a {tel} ({nombre})...")
        try:
            r = requests.get(url, params={'numero': tel, 'mensaje': msg}, timeout=15)
            if r.status_code == 200:
                exitosos += 1
                time.sleep(4)  # Delay anti-bloqueo
            else:
                print(f"Error Gateway: {r.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error de red: {e}")
            break

    print("\n--- FIN DEL DESPACHO ---")
    print(f"Total exitosos: {exitosos}")

if __name__ == "__main__":
    despachar_correccion_masiva()
