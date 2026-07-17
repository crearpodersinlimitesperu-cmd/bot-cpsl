import imaplib
import email
from email.header import decode_header
import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')

# Load credentials
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "")
GMAIL_PASS = GMAIL_PASS.replace('"', '').replace("'", "").replace(" ", "")

if not GMAIL_PASS:
    print("Error: GMAIL_APP_PASS no encontrado.")
    sys.exit(1)

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    return part.get_payload(decode=True).decode()
                except:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode()
        except:
            pass
    return ""

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select("inbox")

    # Buscar correos de hoy (10-May-2026) o recientes
    # Usaremos SINCE 09-May-2026 para asegurar
    status, messages = mail.search(None, '(SINCE "09-May-2026")')
    
    if status == 'OK':
        email_ids = messages[0].split()
        print(f"Total correos recientes encontrados: {len(email_ids)}")
        
        # Procesar los últimos 30 correos
        for e_id in email_ids[-30:]:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                # Decodificar Subject
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    try:
                        subject = subject.decode(encoding if encoding else 'utf-8')
                    except:
                        subject = str(subject)
                
                # Obtener remitente
                from_ = msg.get("From", "")
                
                # Filtrar correos enviados por el propio sistema (rebotes o el mismo usuario)
                if "crearpodersinlimites" in from_.lower() and "mailer-daemon" not in from_.lower():
                    continue
                    
                body = get_body(msg)
                
                print("-" * 50)
                print(f"De: {from_}")
                print(f"Asunto: {subject}")
                print("Mensaje:")
                print(body[:300].strip() + ("..." if len(body) > 300 else ""))
                
    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error conectando a Gmail: {e}")
