import imaplib
import email
import os
import sys
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")

def check_dates():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select('"[Gmail]/Todos"')
        status, messages = mail.search(None, '(FROM "mailer-daemon")')
        
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()
            print(f"Total: {len(email_ids)}")
            for e_id in email_ids[-10:]:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                if res == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    print(f"ID: {e_id.decode()} | Date: {msg['Date']}")
        mail.close()
        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_dates()
