import imaplib

mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('crearpodersinlimitesperu@gmail.com', 'bgslxjusxsmnpzqd')
typ, data = mail.list()
for f in data:
    print(f)
mail.logout()
