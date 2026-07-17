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
    mail.select("inbox")
    
    # Buscar correos del Mailer-Daemon (rebotes) de hoy
    status, messages = mail.search(None, '(FROM "mailer-daemon" SINCE "10-May-2026")')
    rebotes = []
    
    if status == 'OK' and messages[0]:
        email_ids = messages[0].split()
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                # Buscar el correo rebotado en el cuerpo
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            if "No se encontró la dirección" in body or "El mensaje no se entregó a" in body or "The recipient server did not accept our requests" in body:
                                rebotes.append(body[:200].replace('\n', ' '))
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    rebotes.append(body[:200].replace('\n', ' '))
                    
    print(f"Total rebotes detectados: {len(rebotes)}")
    for r in rebotes[:5]:
        print(f"- {r}")

    mail.close()
    mail.logout()
except Exception as e:
    print(f"Error: {e}")
