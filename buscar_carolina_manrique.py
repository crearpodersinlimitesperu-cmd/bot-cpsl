import imaplib
import email
from email.header import decode_header
import sys

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def buscar_carolina():
    print("--- BUSCANDO CORREOS DE CAROLINA MANRIQUE ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar por nombre
        status, messages = mail.search(None, 'BODY "Carolina Manrique"')
        if status != "OK":
            print("No se pudieron buscar los correos.")
            return

        ids = messages[0].split()
        print(f"Total de hilos encontrados: {len(ids)}")
        
        for i in reversed(ids):
            status, data = mail.fetch(i, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            
            # Decodificar asunto
            subject, encoding = decode_header(msg.get("Subject", "Sin Asunto"))[0]
            if isinstance(subject, bytes):
                subject = subject.decode(encoding if encoding else 'utf-8')
            
            print(f"\n--- CORREO DETECTADO ---")
            print(f"DE: {msg.get('From')}")
            print(f"FECHA: {msg.get('Date')}")
            print(f"ASUNTO: {subject}")
            
            # Extraer cuerpo
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            
            print(f"CONTENIDO (Muestra): {body[:600]}...")
            print("-" * 50)
            
        mail.logout()
    except Exception as e:
        print(f"Error en la búsqueda: {e}")

if __name__ == "__main__":
    buscar_carolina()
