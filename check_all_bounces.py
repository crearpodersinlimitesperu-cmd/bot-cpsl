import imaplib
import email
from email.header import decode_header
import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")

def extract_bounced_emails():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        # Select All Mail (Archivados)
        status, messages = mail.select('"[Gmail]/Todos"')
        if status != 'OK':
            print("No se pudo seleccionar Archivados.")
            return

        print("Buscando correos de Mailer-Daemon...")
        status, messages = mail.search(None, '(FROM "mailer-daemon")')
        
        email_list = []
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()
            print(f"Total correos de Mailer-Daemon encontrados: {len(email_ids)}")
            
            # Fetch a sample to see what we are dealing with
            for e_id in email_ids[-10:]:  # last 10
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                if res == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    import re
                    # Simple regex to extract email
                    matches = re.findall(r'[\w\.-]+@[\w\.-]+', body)
                    for m in matches:
                        if "mailer-daemon" not in m.lower() and "google" not in m.lower():
                            email_list.append(m)
                            break # just need the first matched bounced email
            print("Muestra de emails rebotados extraidos:")
            print(set(email_list))
        else:
            print("No se encontraron correos de Mailer-Daemon.")
            
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_bounced_emails()
