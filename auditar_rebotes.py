import imaplib
import email
import os
import re
import sqlite3
import pandas as pd
from dotenv import load_dotenv
import time

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def extract_failed_recipient(body):
    patterns = [
        r"no se entregó a ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"delivered to ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"Final-Recipient: rfc822; ([^\s\n\r]+)",
        r"To: ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"Tu mensaje no se entregó a ([^\s\n\r<]+@[^\s\n\r>]+)"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, body, re.I)
        if match:
            return match.group(1).strip(".<>").lower()
    return None

def connect_imap():
    user = "crearpodersinlimitesperu@gmail.com"
    password = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace(" ", "")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(user, password)
    return mail

def process_bounces(folder_name, max_msgs=100):
    print(f"\n--- PROCESANDO CARPETA: {folder_name} ---", flush=True)
    mail = connect_imap()
    try:
        mail.select(f'"{folder_name}"')
        status, messages = mail.search(None, '(FROM "mailer-daemon@googlemail.com")')
        if status != 'OK':
            return set()
        
        msg_ids = messages[0].split()
        failed_emails = set()
        
        # Procesar los últimos N
        for msg_id in reversed(msg_ids[-max_msgs:]):
            try:
                res, msg_data = mail.fetch(msg_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() in ["text/plain", "text/html"]:
                                    try:
                                        body += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    except: pass
                        else:
                            body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        
                        email_failed = extract_failed_recipient(body)
                        if email_failed:
                            if email_failed.endswith('@gmail'): email_failed += '.com'
                            failed_emails.add(email_failed)
            except Exception as e:
                print(f"Error procesando msg {msg_id}: {e}")
                continue
        
        mail.logout()
        return failed_emails
    except Exception as e:
        print(f"Error en carpeta {folder_name}: {e}")
        return set()

def load_contacts_mapping():
    path = r"C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv"
    mapping = {}
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, dtype=str)
            for _, row in df.iterrows():
                email = str(row.get('E-mail 1 - Value', '')).strip().lower()
                name = str(row.get('Name', '')).strip()
                if email and '@' in email: mapping[email] = name
        except: pass
    return mapping

def audit_bounces():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    
    # Reducimos el batch para evitar timeouts
    bounces_inbox = process_bounces("INBOX", max_msgs=50)
    time.sleep(2)
    bounces_archived = process_bounces("[Gmail]/Todos", max_msgs=200)
    
    all_bounces = bounces_inbox.union(bounces_archived)
    print(f"\nTotal correos rebotados únicos detectados: {len(all_bounces)}", flush=True)
    
    if not all_bounces:
        print("No se detectaron rebotes.")
        return

    contacts_map = load_contacts_mapping()
    conn = sqlite3.connect(db_path)
    results = []
    
    for email_failed in all_bounces:
        px = conn.execute("SELECT id, nombre, apellido, cc_nombre FROM participantes WHERE email=?", (email_failed,)).fetchone()
        if px:
            results.append({"email": email_failed, "id": px[0], "nombre": f"{px[1]} {px[2]}", "cc": px[3], "fuente": "DATABASE"})
        elif email_failed in contacts_map:
            results.append({"email": email_failed, "id": "-", "nombre": contacts_map[email_failed], "cc": "-", "fuente": "CONTACTS_CSV"})
        else:
            results.append({"email": email_failed, "id": "-", "nombre": "Desconocido", "cc": "-", "fuente": "BOUNCE_ONLY"})
    
    df = pd.DataFrame(results)
    output_path = r'C:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv'
    df.to_csv(output_path, index=False)
    print(f"Auditoría guardada en {output_path}")
    print(df['fuente'].value_counts())
    conn.close()

if __name__ == "__main__":
    audit_bounces()
