import imaplib

user = "crearpodersinlimitesperu@gmail.com"
password = "bgsl xjus xsmn pzqd".replace(" ", "")

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    
    status, folders = mail.list()
    print("Carpetas disponibles:")
    for f in folders:
        print(f.decode())

    # Revisar spam
    mail.select('"[Gmail]/Spam"')
    status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    print(f"\nTotal correos en SPAM: {len(email_ids)}")

    mail.logout()

except Exception as e:
    print(f"Error: {e}")
