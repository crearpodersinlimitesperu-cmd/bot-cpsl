import imaplib
from datetime import date

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('crearpodersinlimitesperu@gmail.com', 'bgslxjusxsmnpzqd')
mail.select('inbox')
date_str = date.today().strftime('%d-%b-%Y')

# Buscar solo por fecha
status, msgs = mail.search(None, f'(SINCE "{date_str}")')
if status == 'OK':
    print(f'Total correos recibidos hoy: {len(msgs[0].split())}')

# Buscar por FROM que contenga mailer o daemon
status, msgs = mail.search(None, f'(FROM "mailer" SINCE "{date_str}")')
if status == 'OK':
    print(f'Total rebotes (FROM "mailer"): {len(msgs[0].split())}')

mail.close()
mail.logout()
