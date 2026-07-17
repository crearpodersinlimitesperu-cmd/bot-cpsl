import imaplib
import email
from email.header import decode_header
import os
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join('C:\\Users\\josem\\Downloads\\bot-cpsl-review', '.env'))
GMAIL_USER = 'crearpodersinlimitesperu@gmail.com'
GMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace("'", "").replace(' ', '')

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
    return ''

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login(GMAIL_USER, GMAIL_PASS)
mail.select('"[Gmail]/Todos"')

status, messages = mail.search(None, '(FROM "greacedm30")')
if status == 'OK' and messages[0]:
    for e_id in messages[0].split():
        res, msg_data = mail.fetch(e_id, '(RFC822)')
        if res == 'OK':
            msg = email.message_from_bytes(msg_data[0][1])
            print('MENSAJE DE GREACE DIAZ:')
            print(get_body(msg)[:500].encode('ascii', 'ignore').decode('ascii'))
mail.logout()
