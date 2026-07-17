import imaplib
import email
from email.header import decode_header
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configurar salida
sys.stdout.reconfigure(encoding='utf-8')

# CONFIGURACION
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
OUTPUT_CSV = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_2AÑOS.csv")

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_rebotes_csv():
    print("--- INICIANDO EXTRACCION DE REBOTES A CSV (2 AÑOS) ---")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        status, messages = mail.search(None, 'FROM "mailer-daemon@googlemail.com"')
        if status == "OK":
            ids = messages[0].split()
            print(f"Encontrados {len(ids)} rebotes potenciales.")
            
            with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Email', 'Fecha', 'Contenido_Clave'])
                
                procesados = 0
                for i in reversed(ids):
                    procesados += 1
                    if procesados % 100 == 0: print(f"Procesando {procesados} de {len(ids)}...")
                    
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
                    
                    failed_email = extract_email(body)
                    if not failed_email: failed_email = extract_email(str(msg.get("Subject")))

                    if failed_email and failed_email.lower() != EMAIL_USER.lower():
                        writer.writerow([failed_email, str(msg.get("Date")), body[:100].strip()])
            
            print(f"--- EXTRACCION FINALIZADA: {OUTPUT_CSV} ---")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    auditoria_rebotes_csv()
