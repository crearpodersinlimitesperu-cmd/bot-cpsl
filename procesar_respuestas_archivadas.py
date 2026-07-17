import imaplib
import email
from email.header import decode_header
import os
import sqlite3
from dotenv import load_dotenv
import sys

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join('C:\\Users\\josem\\Downloads\\bot-cpsl-review', '.env'))
GMAIL_USER = 'crearpodersinlimitesperu@gmail.com'
GMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace("'", "").replace(' ', '')

def get_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                try:
                    return part.get_payload(decode=True).decode('utf-8', errors='ignore')
                except:
                    pass
    else:
        try:
            return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        except:
            pass
    return ''

try:
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(GMAIL_USER, GMAIL_PASS)
    mail.select('"[Gmail]/Todos"')
    
    # Buscar correos recibidos hoy, excluyendo los enviados por nosotros
    status, messages = mail.search(None, f'(SINCE "10-May-2026" NOT FROM "{GMAIL_USER}")')
    
    respuestas = []
    if status == 'OK' and messages[0]:
        email_ids = messages[0].split()
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res == 'OK':
                msg = email.message_from_bytes(msg_data[0][1])
                from_ = msg.get("From", "")
                
                # Filtrar basura
                if any(x in from_.lower() for x in ["mailer-daemon", "no-reply", "latam", "reddit", "movistar", "zoom", "google"]):
                    continue
                    
                subject, encoding = decode_header(msg.get("Subject", ""))[0] if msg.get("Subject") else ("Sin asunto", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding if encoding else 'utf-8', errors='ignore')
                
                body = get_body(msg).strip()
                respuestas.append({
                    "from": from_,
                    "subject": subject,
                    "body": body[:500]
                })

    mail.close()
    mail.logout()
    
    # Actualizar BD
    conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')
    cursor = conn.cursor()
    
    print(f"=== SE ENCONTRARON {len(respuestas)} RESPUESTAS EN ARCHIVADOS ===")
    for i, r in enumerate(respuestas):
        print(f"\n[{i+1}] De: {r['from']}")
        print(f"Asunto: {r['subject']}")
        print(f"Mensaje: {r['body'].encode('ascii', 'ignore').decode('ascii').replace(chr(10), ' ')}")
        
        # Buscar en DB
        correo_limpio = r['from'].split('<')[-1].replace('>', '').strip().lower()
        cursor.execute("SELECT id, nombre, apellido, cc_nombre FROM participantes WHERE email LIKE ?", (f"%{correo_limpio}%",))
        px = cursor.fetchone()
        
        if px:
            print(f"  -> MATCH EN DB: ID {px[0]} | {px[1]} {px[2]} | Coordinadora: {px[3]}")
            # Actualizar DB
            cursor.execute("""
                UPDATE participantes 
                SET c1 = 'SI', 
                    c2 = 'PENDIENTE', 
                    es_pendiente_real = 'NO',
                    resultado_gestion = 'ARCHIVADO: Respondio campaña indicando que va a C2'
                WHERE id = ?
            """, (px[0],))
            print("  -> BD ACTUALIZADA: Movido a C2 PENDIENTE y retirado de campaña C1.")
        else:
            print("  -> NO SE ENCONTRO EN LA BD CON ESE CORREO.")
            
    conn.commit()
    conn.close()

except Exception as e:
    print(f"Error: {e}")
