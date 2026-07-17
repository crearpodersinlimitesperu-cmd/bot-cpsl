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
    
    # Seleccionar la carpeta de archivados (Todos los correos)
    mail.select('"[Gmail]/Todos"')
    
    # Buscar correos desde el 01-May-2026
    status, messages = mail.search(None, '(SINCE "01-May-2026")')
    if status == 'OK' and messages[0]:
        email_ids = messages[0].split()
        # Limit to first 200 emails to reduce load and avoid timeout
        MAX_EMAILS = 200
        if len(email_ids) > MAX_EMAILS:
            email_ids = email_ids[:MAX_EMAILS]
        print(f"Total correos en Archivados/Todos (limit {MAX_EMAILS}): {len(email_ids)}")
        
        encontrados = []
        # Buscar en TODOS los correos de All Mail
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                from_ = msg.get("From", "")
                
                # Ignorar correos automáticos
                if "mailer-daemon" in from_.lower() or "no-reply" in from_.lower() or "latam" in from_.lower() or "reddit" in from_.lower() or "movistar" in from_.lower() or "zoom" in from_.lower():
                    continue
                    
                subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                
                body = get_body(msg).lower()
                
                # Criterios de búsqueda: Si mencionan Otty, o ya hicieron C1, o van a C2, o si es una respuesta de una persona
                if "otty" in body or "c2" in body or "ya hice" in body or "capitulo" in body or "confirmado" in body:
                    encontrados.append({
                        "from": from_,
                        "subject": subject,
                        "body": body[:500] # Primeros 500 caracteres
                    })
        
        print(f"\n--- Se encontraron {len(encontrados)} respuestas relevantes en ARCHIVADOS ---")
        for i, r in enumerate(encontrados):
            print(f"\n[{i+1}] De: {r['from']}")
            print(f"Asunto: {r['subject']}")
            print(f"Mensaje: {r['body'].strip().replace(chr(10), ' ')}")
            print("-" * 50)
            
    else:
        print("No se encontraron correos en Archivados.")

    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error: {e}")
