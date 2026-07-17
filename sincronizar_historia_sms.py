import imaplib
import email
import json
import re
import sqlite3
from datetime import datetime, timedelta

def backfill_sms():
    with open('config_scanner.json', 'r') as f:
        config = json.load(f)
    
    mail = imaplib.IMAP4_SSL(config['email_config']['imap_server'])
    mail.login(config['email_config']['email_user'], config['email_config']['email_pass'])
    
    # IMPORTANTE: MacroDroid suele quedar en "Todos" si se archiva
    folder = '"[Gmail]/Todos"'
    mail.select(folder)
    
    since = (datetime.now() - timedelta(days=30)).strftime('%d-%b-%Y')
    # Buscar correos de los ultimos 30 dias con el asunto especifico de MacroDroid
    status, msgs = mail.search(None, f'SINCE {since} SUBJECT "SMS from"')
    
    if status != "OK" or not msgs[0]:
        print("No se encontraron mensajes antiguos.")
        return

    ids = msgs[0].split()
    print(f"Encontrados {len(ids)} correos de MacroDroid. Sincronizando...")
    
    conn = sqlite3.connect('torre_control.db')
    cursor = conn.cursor()
    updated = 0
    
    for eid in ids:
        res, data = mail.fetch(eid, '(RFC822)')
        if res != 'OK': continue
        
        msg = email.message_from_bytes(data[0][1])
        # Decodificar asunto
        raw_asunto = email.header.decode_header(msg.get('Subject'))[0]
        asunto = raw_asunto[0].decode(raw_asunto[1] if raw_asunto[1] else 'utf-8') if isinstance(raw_asunto[0], bytes) else str(raw_asunto[0])
        
        # Extraer telefono
        tel_match = re.search(r'(\d{9,13})', asunto)
        if not tel_match: continue
        tel = tel_match.group(1)[-9:]
        
        # Cuerpo
        cuerpo = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    cuerpo = part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            cuerpo = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        cuerpo = cuerpo.strip().split('\n')[0][:250]
        
        # Detectar email
        new_email = re.search(config['regex_patterns']['email'], cuerpo)
        intent = 'RECEIVED_EMAIL' if new_email else 'NO_REPLY'
        email_val = new_email.group(0).lower() if new_email else None
        
        if email_val:
            cursor.execute('''
                UPDATE participantes 
                SET email=?, estado_respuesta_sms=?, observaciones=?, fecha_ultima_interaccion=?
                WHERE telefono LIKE ? OR tel_imo LIKE ?
            ''', (email_val, intent, cuerpo, datetime.now().isoformat(), f'%{tel}', f'%{tel}'))
            if cursor.rowcount > 0:
                updated += cursor.rowcount
                print(f"Actualizado: {tel} -> {email_val}")

    conn.commit()
    conn.close()
    mail.logout()
    print(f"Sincronizacion historica completada. Registros actualizados: {updated}")

if __name__ == "__main__":
    backfill_sms()
