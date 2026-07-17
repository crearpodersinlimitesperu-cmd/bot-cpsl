import imaplib
import json

def check_todos():
    with open('config_scanner.json', 'r') as f:
        config = json.load(f)
    
    mail = imaplib.IMAP4_SSL(config['email_config']['imap_server'])
    mail.login(config['email_config']['email_user'], config['email_config']['email_pass'])
    
    # Intentar con "[Gmail]/Todos" o "INBOX"
    folders = ['"[Gmail]/Todos"', 'INBOX']
    for folder in folders:
        print(f"\n--- REVISANDO CARPETA: {folder} ---")
        status, _ = mail.select(folder, readonly=True)
        if status != "OK":
            print(f"No se pudo acceder a {folder}")
            continue
            
        status, msgs = mail.search(None, 'SUBJECT', '"SMS from"')
        if status == "OK" and msgs[0]:
            ids = msgs[0].split()
            print(f"Encontrados {len(ids)} mensajes.")
            for eid in ids[-10:]: # Ultimos 10
                res, data = mail.fetch(eid, '(BODY[HEADER.FIELDS (SUBJECT)])')
                print(f"ID {eid.decode()}: {data[0][1].decode().strip()}")
        else:
            print("No se encontraron mensajes con 'SMS from'.")
            
    mail.logout()

if __name__ == "__main__":
    check_todos()
