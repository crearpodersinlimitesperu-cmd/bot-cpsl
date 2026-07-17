import sqlite3
import os
import requests
import time
import sys
from dotenv import load_dotenv

# Asegurar UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('SMS_IMOS', evento, detalle, estado))
        conn_cn.commit()
    except Exception as e:
        print(f"Error blackbox: {e}")

def enviar_sms_imos():
    print("="*60)
    print("  ENVÍO DE SMS A IMOS POR REBOTES (MODO DIOS)")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    # Obtener IMOs con participantes rebotados
    query = """
        SELECT imo, tel_imo, GROUP_CONCAT(nombre || ' ' || apellido, ', ') as px_rebotados
        FROM participantes 
        WHERE email = 'REBOTE' AND imo IS NOT NULL AND imo != '' AND imo != 'nan'
        GROUP BY imo, tel_imo
    """
    cursor.execute(query)
    imos = cursor.fetchall()
    
    print(f"Encontrados {len(imos)} IMOs con participantes rebotados.")
    
    enviados = 0
    sin_telefono = 0
    
    for row in imos:
        imo_name, tel, pxs = row
        
        # Limpiar nombre de IMO
        imo_pref = imo_name.split()[0].title() if imo_name else "Estimado IMO"
        
        # Limpiar teléfono
        tel_clean = "".join(filter(str.isdigit, str(tel)))
        if len(tel_clean) > 9 and tel_clean.startswith("51"):
            tel_clean = tel_clean[2:]
        
        if not tel_clean or len(tel_clean) < 9:
            print(f"⚠️ IMO sin teléfono válido: {imo_name}")
            sin_telefono += 1
            continue

        # Formatear mensaje (limitar lista de nombres para no exceder SMS)
        lista_nombres = pxs
        if len(lista_nombres) > 60:
            lista_nombres = lista_nombres[:57] + "..."
            
        texto = f"Hola {imo_pref}, de CREAR. Los correos de tus enrolados rebotaron: {lista_nombres}. Por favor pídeles que nos envíen su correo correcto por aquí. Gracias!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_clean, "mensaje": texto}
        
        print(f"Enviando SMS a IMO {imo_name} ({tel_clean})... ", end="", flush=True)
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]", flush=True)
                enviados += 1
                log_blackbox(conn_cn, 'ENVIO_SMS_IMO_REBOTE', f'Enviado a {tel_clean} ({imo_name})', 'COMPLETADO')
            else:
                print(f"[ERROR {r.status_code}]", flush=True)
        except Exception as e:
            print(f"[EXCEPCION: {str(e)}]", flush=True)
            
        time.sleep(4) # Pausa entre mensajes
        
    conn.close()
    conn_cn.close()
    
    print("\n" + "="*60)
    print(f"  RESUMEN FINAL IMOS")
    print(f"  Enviados: {enviados}")
    print(f"  Sin teléfono: {sin_telefono}")
    print("="*60)

if __name__ == "__main__":
    enviar_sms_imos()
