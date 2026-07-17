import imaplib
import email
import os
from email.header import decode_header
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def review_sent_emails():
    user = "crearpodersinlimitesperu@gmail.com"
    password = os.environ.get("GMAIL_APP_PASS", "")
    
    if not password:
        print("Error: GMAIL_APP_PASS no encontrado.")
        return

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(user, password)
        
        # Seleccionar carpeta de enviados específica para Gmail en español
        mail.select('"[Gmail]/Enviados"')
        
        status, messages = mail.search(None, 'ALL')
        msg_ids = messages[0].split()
        last_ids = msg_ids[-10:] 
        
        print(f"--- ÚLTIMOS {len(last_ids)} CORREOS ENVIADOS ---")
        
        for msg_id in reversed(last_ids):
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        subject = subject.decode(encoding if encoding else "utf-8")
                    
                    to = msg.get("To")
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/html":
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    # Buscar el saludo "Hola [Nombre]"
                    import re
                    match = re.search(r"Hola\s+([^,!<]+)", body)
                    nombre_cuerpo = match.group(1).strip() if match else "No encontrado"
                    
                    print(f"A: {to} | Cuerpo dice: Hola {nombre_cuerpo} | Asunto: {subject[:40]}...")
                    
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    review_sent_emails()
