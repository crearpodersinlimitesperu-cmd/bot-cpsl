import imaplib
import email
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
OUTPUT_CSV = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_SONIC.csv")

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_rebotes_sonica():
    print("--- INICIANDO EXTRACCION SONICA DE REBOTES (2 AÑOS) ---")
    
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
                writer.writerow(['Email', 'Fecha'])
                
                procesados = 0
                for i in reversed(ids):
                    procesados += 1
                    if procesados % 100 == 0: 
                        print(f"Procesando {procesados} de {len(ids)}...")
                        f.flush()
                    
                    # Fetch ligero: solo cuerpo y fecha
                    status, data = mail.fetch(i, "(BODY[TEXT] INTERNALDATE)")
                    if status != "OK": continue
                    
                    body = data[0][1].decode(errors='ignore')
                    date_match = re.search(r'\d{2}-\w{3}-\d{4}', str(data[1]))
                    fecha = date_match.group(0) if date_match else "Unknown"

                    failed_email = extract_email(body)
                    if failed_email and failed_email.lower() != EMAIL_USER.lower():
                        writer.writerow([failed_email, fecha])
                        # print(f"   [+] {failed_email}")
            
            print(f"--- EXTRACCION SONICA FINALIZADA: {OUTPUT_CSV} ---")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    auditoria_rebotes_sonica()
