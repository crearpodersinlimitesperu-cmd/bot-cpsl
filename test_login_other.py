import imaplib, os
from dotenv import load_dotenv
load_dotenv(os.path.join('C:\\Users\\josem\\Downloads\\bot-cpsl-review', '.env'))
try:
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login('crearpodersinalimites@gmail.com', os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace("'", "").replace(' ', ''))
    print('Login a crearpodersinalimites@gmail.com EXITOSO')
    
    mail.select("inbox")
    status, messages = mail.search(None, '(SINCE "10-May-2026")')
    if status == 'OK':
        print(f"Bandeja de entrada: {len(messages[0].split())} correos desde 10-May")
    mail.logout()
except Exception as e:
    print(f'Error: {e}')
