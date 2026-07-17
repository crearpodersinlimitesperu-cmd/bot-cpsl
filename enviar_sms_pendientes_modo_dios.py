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
                       ('SMS_PENDIENTES', evento, detalle, estado))
        conn_cn.commit()
    except Exception as e:
        print(f"Error blackbox: {e}")

def enviar_sms_pendientes():
    print("="*60)
    print("  EJECUCIÓN DE SMS PENDIENTES (MODO DIOS)")
    print("="*60)
    
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    gk = Gatekeeper()
    
    # 1. Obtener todos los rebotes que no hayan recibido SMS hoy (o nunca)
    # Buscamos en la caja negra si ya hubo un envío exitoso hoy para ese número
    fecha_hoy = time.strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id, nombre, apellido, telefono, email 
        FROM participantes 
        WHERE email = 'REBOTE' AND telefono != ''
    """)
    rebotes = cursor.fetchall()
    
    print(f"Encontrados {len(rebotes)} participantes marcados como REBOTE.")
    
    enviados = 0
    bloqueados = 0
    ya_enviados_count = 0
    
    for px in rebotes:
        px_id, nom, ape, tel, mail_status = px
        
        # Limpiar teléfono
        tel_clean = "".join(filter(str.isdigit, str(tel)))
        if len(tel_clean) > 9 and tel_clean.startswith("51"):
            tel_clean = tel_clean[2:]
        
        if len(tel_clean) < 9:
            print(f"⚠️ Teléfono inválido para {nom} {ape}: {tel}")
            continue

        # Verificar si ya se envió hoy (evitar spam)
        cursor_cn = conn_cn.cursor()
        cursor_cn.execute("SELECT COUNT(*) FROM logs WHERE evento = 'ENVIO_SMS_NUEVO_REBOTE' AND detalle LIKE ? AND timestamp LIKE ?", (f"%{tel_clean}%", f"{fecha_hoy}%"))
        if cursor_cn.fetchone()[0] > 0:
            ya_enviados_count += 1
            continue

        # 2. VALIDACIÓN GATEKEEPER (¿Es apto?)
        valido, razon = gk.validate_send(participante_id=px_id, canal='SMS', campana_tipo='C1')
        
        if not valido:
            print(f"⛔ Bloqueado por Gatekeeper: {nom} {ape} -> {razon}")
            bloqueados += 1
            continue
            
        # 3. Enviar SMS
        nombre_corto = nom.split()[0].title()
        texto = f"Hola {nombre_corto}, te escribimos de CREAR. Intentamos enviarte tu info de C1 pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_clean, "mensaje": texto}
        
        print(f"Enviando SMS a {nom} {ape} ({tel_clean})... ", end="", flush=True)
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]", flush=True)
                enviados += 1
                log_blackbox(conn_cn, 'ENVIO_SMS_NUEVO_REBOTE', f'Enviado a {tel_clean} ({nom} {ape})', 'COMPLETADO')
            else:
                print(f"[ERROR {r.status_code}]", flush=True)
        except Exception as e:
            print(f"[EXCEPCION: {str(e)}]", flush=True)
            
        time.sleep(3) # Pausa breve entre mensajes
        
    conn.close()
    conn_cn.close()
    
    print("\n" + "="*60)
    print(f"  RESUMEN FINAL")
    print(f"  Enviados: {enviados}")
    print(f"  Bloqueados (Gatekeeper): {bloqueados}")
    print(f"  Ya enviados hoy: {ya_enviados_count}")
    print("="*60)

if __name__ == "__main__":
    enviar_sms_pendientes()
