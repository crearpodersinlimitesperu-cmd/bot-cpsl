import json
import requests
import time
import os
import sqlite3
import sys

# Forzar encoding UTF-8 para evitar errores con emojis en Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

def log_to_blackbox(categoria, evento, detalle, estado="INFO"):
    try:
        conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\caja_negra.db')
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO logs (categoria, evento, detalle, estado) 
                          VALUES (?, ?, ?, ?)''', (categoria, evento, detalle, estado))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error logging to blackbox: {e}")

def enviar_sms_rebotes():
    json_path = r'C:\Users\josem\Downloads\bot-cpsl-review\sms_rebotes_pendientes.json'
    
    if not os.path.exists(json_path):
        print("No se encontró sms_rebotes_pendientes.json")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        mensajes = json.load(f)

    print(f"--- INICIANDO ENVIO DE {len(mensajes)} SMS DE REBOTES ---", flush=True)
    log_to_blackbox('CAMPANA', 'ENVIO_SMS_REBOTES', f'Iniciando envío de {len(mensajes)} mensajes.', 'EN_CURSO')

    enviados = 0
    errores = 0

    for msg in mensajes:
        tel = str(msg['telefono']).strip()
        texto = msg['mensaje']
        nombre = msg.get('nombre', msg.get('referencia', 'Participante'))

        # Limpiar teléfono
        tel_clean = "".join(filter(str.isdigit, tel))
        if len(tel_clean) > 9 and tel_clean.startswith("51"):
            tel_clean = tel_clean[2:]
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_clean, "mensaje": texto}

        print(f"Enviando a {nombre} ({tel_clean})... ", end="", flush=True)
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]", flush=True)
                enviados += 1
            else:
                print(f"[ERROR {r.status_code}]", flush=True)
                errores += 1
        except Exception as e:
            print(f"[EXCEPCION: {str(e)}]", flush=True)
            errores += 1

        time.sleep(5)

    print(f"\n--- FIN DE PROCESO ---", flush=True)
    print(f"Enviados exitosos: {enviados} | Fallidos: {errores}", flush=True)
    log_to_blackbox('CAMPANA', 'ENVIO_SMS_REBOTES', f'Finalizado. Enviados: {enviados}, Fallidos: {errores}', 'COMPLETADO')

if __name__ == "__main__":
    enviar_sms_rebotes()
