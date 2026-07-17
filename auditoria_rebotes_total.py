import imaplib
import email
from email.header import decode_header
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configurar salida para evitar errores de encoding
sys.stdout.reconfigure(encoding='utf-8')

# CONFIGURACION
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\patrones_forenses_v3.db")

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_rebotes_total():
    print("--- INICIANDO AUDITORIA DE REBOTES (2 AÑOS) ---")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS historial_interacciones (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, fecha TEXT, tipo_interaccion TEXT, contenido_clave TEXT, fuente TEXT)")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        # Búsqueda específica de rebotes de Google
        print("Buscando notificaciones de Mail Delivery Subsystem...")
        status, messages = mail.search(None, 'FROM "mailer-daemon@googlemail.com"')
        if status == "OK":
            ids = messages[0].split()
            print(f"Encontrados {len(ids)} rebotes potenciales.")
            
            procesados = 0
            for i in reversed(ids):
                procesados += 1
                if procesados % 100 == 0: print(f"Procesando rebote {procesados} de {len(ids)}...")
                
                status, data = mail.fetch(i, "(RFC822)")
                if status != "OK": continue
                
                msg = email.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                
                # Extraer el correo que falló (usualmente en el cuerpo)
                failed_email = extract_email(body)
                if not failed_email:
                    # Intentar buscar en el asunto si no esta en el cuerpo
                    failed_email = extract_email(str(msg.get("Subject")))

                if failed_email and failed_email.lower() != EMAIL_USER.lower():
                    print(f"   [!] Rebote detectado: {failed_email}")
                    c.execute("INSERT INTO historial_interacciones (email, fecha, tipo_interaccion, contenido_clave, fuente) VALUES (?, ?, ?, ?, ?)",
                              (failed_email, str(msg.get("Date")), "REBOTE", body[:150].strip(), "GMAIL_BOUNCE_SCAN"))
                else:
                    print(f"   [?] No se pudo extraer email del rebote {procesados}")
            
            conn.commit()
            print("--- ESCANEO DE REBOTES FINALIZADO ---")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    auditoria_rebotes_total()
