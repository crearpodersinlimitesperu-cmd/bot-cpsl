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

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return ""

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    
    # Check Inbox
    mail.select("inbox")
    status, messages = mail.search(None, '(SINCE "09-May-2026")')
    if status == 'OK':
        email_ids = messages[0].split()
        print(f"Bandeja de entrada - Correos desde el 09-May: {len(email_ids)}")
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                from_ = msg.get("From", "")
                
                body = get_body(msg)
                if "otty" in body.lower() or "c2" in body.lower() or "capítulo 2" in body.lower() or "capitulo 2" in body.lower():
                    print("-" * 50)
                    print(f"De: {from_}")
                    print(f"Asunto: {subject}")
                    print(f"Mensaje: {body[:500].strip()}")
                    
    # Check SPAM just in case
    mail.select('"[Gmail]/Spam"')
    status, messages = mail.search(None, '(SINCE "09-May-2026")')
    if status == 'OK' and messages[0]:
        email_ids = messages[0].split()
        print(f"SPAM - Correos desde el 09-May: {len(email_ids)}")
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                from_ = msg.get("From", "")
                body = get_body(msg)
                if "otty" in body.lower() or "c2" in body.lower() or "capitulo 2" in body.lower():
                    print("-" * 50)
                    print(f"[SPAM] De: {from_}")
                    print(f"Asunto: {subject}")
                    print(f"Mensaje: {body[:500].strip()}")

    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error conectando a Gmail: {e}")
