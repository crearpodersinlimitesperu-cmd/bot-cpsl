import imaplib
import email
from email.header import decode_header

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def analizar_muestra():
    print("--- ANALIZANDO MUESTRA DE CORREOS ([Gmail]/Todos) ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        status, messages = mail.search(None, "ALL")
        ids = messages[0].split()
        
        # Analizar los últimos 20 correos
        for i in reversed(ids[-20:]):
            status, data = mail.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            
            subject, encoding = decode_header(msg.get("Subject", "Sin Asunto"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            
            print(f"\nDE: {msg.get('From')}")
            print(f"ASUNTO: {subject}")
            
            # Ver si es un rebote tipico
            if "mailer-daemon" in str(msg.get("From")).lower() or "failure" in subject.lower():
                print(">>> [DETECTADO COMO POSIBLE REBOTE]")
            
            # Cuerpo corto
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            
            print(f"CONTENIDO: {body[:150].strip()}...")
            print("-" * 30)
            
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    analizar_muestra()
