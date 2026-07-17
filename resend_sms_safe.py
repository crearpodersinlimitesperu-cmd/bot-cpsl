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

# Importar Gatekeeper
sys.path.append(os.path.dirname(__file__))
from gatekeeper import Gatekeeper

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('SMS_RESEND', evento, detalle, estado))
        conn_cn.commit()
    except Exception as e:
        print(f"Error blackbox: {e}")

def resend_safe(batch_size=10, delay=20):
    print("="*60)
    print("  REENVÍO SEGURO DE SMS (MODO DIOS)")
    print(f"  Configuración: Lotes de {batch_size} | Delay: {delay}s")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    gk = Gatekeeper()
    
    # Obtener todos los objetivos potenciales (PX e IMOs de rebotes)
    # 1. PX Rebotados
    cursor.execute("SELECT id, nombre, apellido, telefono FROM participantes WHERE email = 'REBOTE' AND telefono != ''")
    px_list = cursor.fetchall()
    
    # 2. IMOs de Rebotados
    cursor.execute("""
        SELECT imo, tel_imo, GROUP_CONCAT(nombre || ' ' || apellido, ', ') as px_rebotados
        FROM participantes 
        WHERE email = 'REBOTE' AND imo IS NOT NULL AND imo != '' AND imo != 'nan'
        GROUP BY imo, tel_imo
    """)
    imo_list = cursor.fetchall()
    
    print(f"Total objetivos encontrados: {len(px_list)} participantes y {len(imo_list)} IMOs.")
    print("¿Deseas re-enviar TODO el bloque o solo lo que falte?")
    print("--- INICIANDO PROCESO POR LOTES ---")
    
    enviados_total = 0
    
    # Procesar PX
    for i, px in enumerate(px_list):
        px_id, nom, ape, tel = px
        tel_clean = "".join(filter(str.isdigit, str(tel)))
        if len(tel_clean) > 9 and tel_clean.startswith("51"): tel_clean = tel_clean[2:]
        
        if len(tel_clean) < 9: continue
        
        # Validación Gatekeeper
        valido, razon = gk.validate_send(participante_id=px_id, canal='SMS', campana_tipo='C1')
        if not valido: continue
        
        nombre_corto = nom.split()[0].title()
        texto = f"Hola {nombre_corto}, te escribimos de CREAR. Intentamos enviarte tu info de C1 pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_clean, "mensaje": texto}
        
        print(f"[{enviados_total+1}] Re-enviando a PX: {nom} ({tel_clean})... ", end="", flush=True)
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]")
                enviados_total += 1
                log_blackbox(conn_cn, 'REINTENTO_SMS_PX', f'Lote {enviados_total//batch_size} a {tel_clean}', 'OK')
            else: print(f"[ERR {r.status_code}]")
        except: print("[EXC]")
        
        if enviados_total % batch_size == 0:
            print(f"--- Lote de {batch_size} completado. Pausa larga de 60s para evitar bloqueo de operadora... ---")
            time.sleep(60)
        else:
            time.sleep(delay)

    # Procesar IMOs
    for i, row in enumerate(imo_list):
        imo_name, tel, pxs = row
        tel_clean = "".join(filter(str.isdigit, str(tel)))
        if len(tel_clean) > 9 and tel_clean.startswith("51"): tel_clean = tel_clean[2:]
        
        if not tel_clean or len(tel_clean) < 9: continue
        
        imo_pref = imo_name.split()[0].title()
        lista_nombres = pxs[:60] + "..." if len(pxs) > 60 else pxs
        texto = f"Hola {imo_pref}, de CREAR. Los correos de tus enrolados rebotaron: {lista_nombres}. Por favor pídeles que nos envíen su correo correcto por aquí. Gracias!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_clean, "mensaje": texto}
        
        print(f"[{enviados_total+1}] Re-enviando a IMO: {imo_name} ({tel_clean})... ", end="", flush=True)
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]")
                enviados_total += 1
                log_blackbox(conn_cn, 'REINTENTO_SMS_IMO', f'Lote {enviados_total//batch_size} a {tel_clean}', 'OK')
            else: print(f"[ERR {r.status_code}]")
        except: print("[EXC]")

        if enviados_total % batch_size == 0:
            print(f"--- Lote de {batch_size} completado. Pausa larga de 60s... ---")
            time.sleep(60)
        else:
            time.sleep(delay)
            
    conn.close()
    conn_cn.close()

if __name__ == "__main__":
    resend_safe()
