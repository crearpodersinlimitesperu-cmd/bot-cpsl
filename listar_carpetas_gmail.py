import imaplib

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def listar():
    print("--- LISTANDO CARPETAS DE GMAIL ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        status, folders = mail.list()
        for f in folders:
            print(f.decode())
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    listar()
