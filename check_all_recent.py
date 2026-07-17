import imaplib
import email
import re
from datetime import datetime, timedelta

user = "crearpodersinlimitesperu@gmail.com"
password = "bgsl xjus xsmn pzqd".replace(" ", "")

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    mail.select("inbox")

    # Búsqueda más amplia para ver si hay ALGO nuevo hoy
    date_since = datetime.now().strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE {date_since})')
    
    email_ids = messages[0].split()
    print(f"Total de correos recibidos HOY ({date_since}): {len(email_ids)}")
    
    # Revisar los últimos 15 correos para ver qué asuntos tienen
    print("Últimos correos recibidos:")
    for e_id in email_ids[-15:]:
        status, msg_data = mail.fetch(e_id, "(BODY[HEADER.FIELDS (SUBJECT FROM)])")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                print(response_part[1].decode('utf-8', errors='ignore').strip())
                print("---")

    mail.logout()

except Exception as e:
    print(f"Error: {e}")
