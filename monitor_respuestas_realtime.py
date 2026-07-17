import imaplib
import email
import time
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
DB_PATH = Path("torre_control.db")

def clasificar_respuesta(body):
    b = body.lower()
    if any(word in b for word in ["confirmo", "asistire", "listo", "voya ir", "ahi estare"]):
        return "CONFIRMADO"
    if any(word in b for word in ["duda", "pregunta", "donde", "hora", "costo"]):
        return "DUDA_TECNICA"
    if any(word in b for word in ["no puedo", "retiro", "devolucion", "otro dia"]):
        return "SOLICITA_REPROGRAMACION"
    return "OTRO"

def monitorear_respuestas():
    print("--- INICIANDO MONITOR DE RESPUESTAS (ESCUCHA ACTIVA) ---")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar correos no leídos de los últimos 15 minutos
        # Para este bot, buscaremos los mas recientes
        status, messages = mail.search(None, 'UNSEEN')
        if status == "OK":
            ids = messages[0].split()
            print(f"Detectadas {len(ids)} nuevas interacciones potenciales.")
            
            for i in ids:
                status, data = mail.fetch(i, "(RFC822)")
                msg = email.message_from_bytes(data[0][1])
                remitente = email.utils.parseaddr(msg.get("From"))[1].lower()
                subject = msg.get("Subject")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')

                tipo = clasificar_respuesta(body)
                print(f"   [!] Respuesta de {remitente}: {tipo}")
                
                # Actualizar DB o generar log de confirmados
                # Aqui vendria la logica de inyeccion a torre_control.db
                
            if not ids:
                print("   [.] Sin respuestas nuevas en este ciclo.")

        mail.logout()
    except Exception as e:
        print(f"Error en monitor: {e}")

if __name__ == "__main__":
    while True:
        monitorear_respuestas()
        print("Esperando 5 minutos para el siguiente barrido...")
        time.sleep(300) # 5 minutos
