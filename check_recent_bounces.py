import imaplib
import email
from email.header import decode_header
import os
import re
from datetime import datetime, timedelta

user = "crearpodersinlimitesperu@gmail.com"
password = "bgsl xjus xsmn pzqd".replace(" ", "")

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    mail.select("inbox")

    # Búsqueda de correos rebotados en el día de hoy
    # El asunto típico de un rebote es "Delivery Status Notification (Failure)" o "Undeliverable" o "Mensaje no entregado"
    date_since = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE {date_since} FROM "mailer-daemon")')
    
    email_ids = messages[0].split()
    print(f"Se encontraron {len(email_ids)} mensajes de 'mailer-daemon' (rebotes) desde {date_since}.\n")
    
    bounced_emails = set()
    
    # Check the last 50 bounces just in case there are many
    for e_id in email_ids[-50:]:
        status, msg_data = mail.fetch(e_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                # Extraer texto del body para buscar el correo que rebotó
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body += part.get_payload(decode=True).decode()
                            except:
                                pass
                else:
                    try:
                        body = msg.get_payload(decode=True).decode()
                    except:
                        pass
                
                # Buscar patrones de correo en el body
                # Generalmente dice "Your message to xxx@xxx.com couldn't be delivered"
                # o "La entrega a los siguientes destinatarios o grupos no se pudo realizar: xxx@xxx.com"
                
                # Usar regex para sacar todos los correos del cuerpo del rebote
                found_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', body)
                for em in found_emails:
                    em_lower = em.lower()
                    if em_lower != user.lower() and "mailer-daemon" not in em_lower and "googlemail.com" not in em_lower:
                        bounced_emails.add(em_lower)

    if not bounced_emails:
        print("No se pudieron extraer direcciones específicas de los rebotes, revisando asuntos...")
    else:
        print("Correos que rebotaron encontrados en los mensajes de error:")
        for b_mail in bounced_emails:
            print(f"- {b_mail}")

    mail.logout()

except Exception as e:
    print(f"Error: {e}")
