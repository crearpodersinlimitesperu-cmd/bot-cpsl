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
    mail.select('"[Gmail]/Todos"')
    
    # Solo ASCII keywords
    keywords = ["otty", "c2", "capitulo 2", "ya hice", "confirmado"]
    encontrados = []
    
    for kw in keywords:
        # Search by BODY
        status, messages = mail.search(None, f'(SINCE "01-May-2026" BODY "{kw}")')
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()
            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                if res == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    from_ = msg.get("From", "")
                    
                    if "mailer-daemon" in from_.lower() or "no-reply" in from_.lower() or "latam" in from_.lower() or "reddit" in from_.lower() or "movistar" in from_.lower() or "zoom" in from_.lower():
                        continue
                        
                    if "crearpodersinlimites" in from_.lower():
                        continue # Skip our own sent emails
                        
                    subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                    
                    body = get_body(msg).lower()
                    encontrados.append({
                        "from": from_,
                        "subject": subject,
                        "body": body[:500]
                    })
    
    vistos = set()
    unicos = []
    for r in encontrados:
        key = r["subject"] + r["from"]
        if key not in vistos:
            unicos.append(r)
            vistos.add(key)
            
    print(f"\n--- Se encontraron {len(unicos)} respuestas en ARCHIVADOS ---")
    for i, r in enumerate(unicos):
        print(f"\n[{i+1}] De: {r['from']}")
        print(f"Asunto: {r['subject']}")
        print(f"Mensaje: {r['body'].strip().replace(chr(10), ' ')}")
        print("-" * 50)

    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error: {e}")
