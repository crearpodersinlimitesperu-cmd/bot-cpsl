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

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select('"[Gmail]/Todos"')
    
    # Get last 50 emails not sent by us
    status, messages = mail.search(None, f'(SINCE "09-May-2026" NOT FROM "{GMAIL_USER}")')
    if status == 'OK' and messages[0]:
        email_ids = messages[0].split()
        print(f"Total correos: {len(email_ids)}")
        for e_id in email_ids[-30:]: # ultimos 30
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                from_ = msg.get("From", "")
                subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                print(f"De: {from_[:40]} | Asunto: {subject[:60]}")
    else:
        print("No se encontraron correos.")

    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error: {e}")
