import imaplib
import email
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def sample_bounces():
    user = "crearpodersinlimitesperu@gmail.com"
    password = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace(" ", "")
    
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    
    mail.select('"[Gmail]/Todos"')
    status, messages = mail.search(None, '(FROM "mailer-daemon@googlemail.com")')
    
    if status != 'OK':
        print("Error al buscar.")
        return

    msg_ids = messages[0].split()
    print(f"Total rebotes: {len(msg_ids)}")
    
    # Ver los últimos 3
    for msg_id in reversed(msg_ids[-3:]):
        res, msg_data = mail.fetch(msg_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                print("\n" + "="*50)
                print(f"Subject: {msg['Subject']}")
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            print(f"--- BODY SAMPLE (First 500 chars) ---\n{body[:500]}")
                        elif content_type == "message/delivery-status":
                            print(f"--- DELIVERY STATUS ATTACHMENT FOUND ---")
                else:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    print(f"--- BODY SAMPLE (First 500 chars) ---\n{body[:500]}")

    mail.logout()

if __name__ == "__main__":
    sample_bounces()
