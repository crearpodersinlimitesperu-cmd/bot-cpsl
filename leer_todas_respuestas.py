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
    mail.select("inbox")
    status, messages = mail.search(None, '(SINCE "10-May-2026")')
    if status == 'OK':
        email_ids = messages[0].split()
        print(f"Total correos recibidos desde el 10-May: {len(email_ids)}")
        encontrados = []
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                from_ = msg.get("From", "")
                if "mailer-daemon" in from_.lower() or "no-reply" in from_.lower() or "latam" in from_.lower() or "reddit" in from_.lower():
                    continue
                
                subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                
                body = get_body(msg)
                if body.strip():
                    encontrados.append({
                        "from": from_,
                        "subject": subject,
                        "body": body[:500]
                    })
        print(f"Respuestas reales encontradas: {len(encontrados)}")
        for i, r in enumerate(encontrados):
            print(f"\n--- RESPUESTA {i+1} ---")
            print(f"De: {r['from']}")
            print(f"Asunto: {r['subject']}")
            print(f"Mensaje: {r['body'].strip().replace(chr(10), ' ')}")
            
    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error conectando a Gmail: {e}")
