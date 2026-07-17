import imaplib, os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join('C:\\Users\\josem\\Downloads\\bot-cpsl-review', '.env'))
GMAIL_USER = 'crearpodersinlimitesperu@gmail.com'
GMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace("'", "").replace(' ', '')
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select('"[Gmail]/Enviados"')
    status, messages = mail.search(None, '(SINCE "10-May-2026")')
    if status == 'OK':
        email_ids = messages[0].split()
        print(f'Correos enviados desde el 10-May: {len(email_ids)}')
    mail.logout()
except Exception as e:
    print(e)
