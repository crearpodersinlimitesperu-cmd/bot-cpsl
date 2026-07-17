import imaplib
import os
import re
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def list_folders():
    user = "crearpodersinlimitesperu@gmail.com"
    password = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace(" ", "")
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    
    print("--- CARPETAS DISPONIBLES ---")
    for f in mail.list()[1]:
        print(f.decode())
    
    mail.logout()

if __name__ == "__main__":
    list_folders()
