import imaplib
import email
import os
import sys
import datetime
from email.header import decode_header
from dotenv import load_dotenv
import re

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace(' ', '')

def get_bounced_emails():
    print("Conectando a IMAP...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
    except Exception as e:
        print(f"Error conectando a IMAP: {e}")
        return []

    try:
        mail.select('"[Gmail]/Todos"')
    except:
        try:
            mail.select('"[Gmail]/All Mail"')
        except:
            mail.select("inbox")
    
    # Buscar correos desde hoy
    date = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE {date} FROM "mailer-daemon@googlemail.com")')
    
    if status != 'OK' or not messages[0]:
        print("No se encontraron mensajes de Mailer-Daemon, intentando busqueda por asunto...")
        status, messages = mail.search(None, f'(SINCE {date} SUBJECT "Delivery Status")')
        
    if status != 'OK' or not messages[0]:
        print("No se encontraron rebotes.")
        return []

    email_ids = messages[0].split()
    print(f"Se encontraron {len(email_ids)} mensajes de Mailer-Daemon desde {date}.")
    
    bounced_addresses = []
    
    for eid in email_ids:
        status, msg_data = mail.fetch(eid, '(RFC822)')
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Buscar en el cuerpo
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                # Buscar correos fallidos (suele decir: "Your message to X couldn't be delivered" o similar)
                                # Tambien en cabeceras X-Failed-Recipients
                            except:
                                body = ""
                else:
                    try:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except:
                        body = ""
                
                # Buscar en cabeceras especificas del reporte de error
                failed_recipients = []
                for part in msg.walk():
                    if part.get_content_type() == 'message/delivery-status':
                        for line in part.get_payload():
                            if isinstance(line, str):
                                continue
                            if 'Final-Recipient' in line:
                                val = line['Final-Recipient']
                                if ';' in val:
                                    failed_recipients.append(val.split(';')[-1].strip())
                                else:
                                    failed_recipients.append(val)
                
                if failed_recipients:
                    for fr in failed_recipients:
                        bounced_addresses.append(fr.lower())
                else:
                    # Intento de parseo por regex si no esta el bloque standar
                    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', body)
                    for e in emails:
                        if e.lower() != 'crearpodersinlimitesperu@gmail.com' and 'mailer-daemon' not in e.lower():
                            bounced_addresses.append(e.lower())

    mail.logout()
    return list(set(bounced_addresses))

if __name__ == "__main__":
    bounces = get_bounced_emails()
    print("\n--- REBOTES ENCONTRADOS ---")
    for b in bounces:
        print(b)
    
    with open('rebotes_recientes.txt', 'w') as f:
        for b in bounces:
            f.write(f"{b}\n")
    print(f"\nTotal rebotes: {len(bounces)}")
