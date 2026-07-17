import imaplib
import email
import os
import sys
import json
import sqlite3
import pandas as pd
import re
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding='utf-8')
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")

def extract_bounced_emails():
    print("--- EXTRAYENDO REBOTES DE GMAIL ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select('"[Gmail]/Todos"')
        status, messages = mail.search(None, '(FROM "mailer-daemon")')
        
        email_list = set()
        if status == 'OK' and messages[0]:
            email_ids = messages[0].split()
            print(f"Total correos de Mailer-Daemon encontrados: {len(email_ids)}")
            
            for e_id in email_ids:
                res, msg_data = mail.fetch(e_id, '(RFC822)')
                if res == 'OK':
                    msg = email.message_from_bytes(msg_data[0][1])
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == 'text/plain':
                                body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                break
                    else:
                        body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    
                    # Regex para encontrar el email de destino que falló
                    # Usualmente viene después de "Final-Recipient: rfc822; "
                    match_fr = re.search(r'Final-Recipient: rfc822;\s*([\w\.-]+@[\w\.-]+)', body, re.IGNORECASE)
                    if match_fr:
                        email_list.add(match_fr.group(1).lower().strip())
                    else:
                        # Fallback a regex general pero limpiando puntos al final
                        matches = re.findall(r'[\w\.-]+@[\w\.-]+', body)
                        for m in matches:
                            m_lower = m.lower().strip().rstrip('.')
                            if "mailer-daemon" not in m_lower and "google" not in m_lower:
                                email_list.add(m_lower)
                                break 
        mail.close()
        mail.logout()
        return list(email_list)
    except Exception as e:
        print(f"Error: {e}")
        return []

def cargar_emails_contacts():
    contacts_path = r"C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv"
    gc_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Google_Contacts_EQUIPO27.csv"
    
    email_to_phone = {} # email -> telefono
    email_to_name = {}  # email -> nombre
    
    if os.path.exists(contacts_path):
        df = pd.read_csv(contacts_path, dtype=str)
        for _, row in df.iterrows():
            email = str(row.get('E-mail 1 - Value', '')).strip().lower()
            if not email or '@' not in email: continue
            phone = re.sub(r'[^\d]', '', str(row.get('Phone 1 - Value', '')))
            if phone.startswith('51') and len(phone) > 9: phone = phone[2:]
            name = str(row.get('Name', '')).strip()
            email_to_phone[email] = phone
            email_to_name[email] = name
            
    if os.path.exists(gc_path):
        df2 = pd.read_csv(gc_path, dtype=str)
        for _, row in df2.iterrows():
            email = str(row.get('E-mail Address', '')).strip().lower()
            if not email or '@' not in email: continue
            phone = re.sub(r'[^\d]', '', str(row.get('Phone 1 - Value', '')))
            if phone.startswith('51') and len(phone) > 9: phone = phone[2:]
            name = str(row.get('Name', '')).strip()
            email_to_phone[email] = phone
            email_to_name[email] = name
            
    return email_to_phone, email_to_name

def generar_sms(emails_rebotados):
    print("--- CRUZANDO CON CONTACTOS Y BD ---")
    email_to_phone, email_to_name = cargar_emails_contacts()
    
    conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db')
    cursor = conn.cursor()
    
    sms_messages = []
    encontrados = 0
    
    for rebote in emails_rebotados:
        phone = email_to_phone.get(rebote)
        name = email_to_name.get(rebote)
        
        if phone:
            # Buscar en la BD para ver si es pendiente real
            row = cursor.execute("SELECT nombre, apellido, imo FROM participantes WHERE telefono LIKE ? AND es_pendiente_real = 'SI'", (f'%{phone}',)).fetchone()
            if row:
                encontrados += 1
                p_nombre, p_apellido, p_imo = row
                msg_px = f"Hola {p_nombre}, te saludamos de CREAR. Intentamos enviarte la informacion de tu C1 a {rebote} pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
                sms_messages.append({"telefono": phone, "mensaje": msg_px})
                
                if p_imo and p_imo != 'None':
                    imo_row = cursor.execute("SELECT nombre, telefono FROM participantes WHERE identificacion = ?", (p_imo,)).fetchone()
                    if imo_row:
                        i_nombre, i_tel = imo_row
                        msg_imo = f"Hola {i_nombre}, como IMO de {p_nombre} {p_apellido}, te informamos que su correo {rebote} rebotó. Apoyanos solicitandole su correo actual. Gracias!"
                        sms_messages.append({"telefono": i_tel, "mensaje": msg_imo})

    with open(r'C:\Users\josem\Downloads\bot-cpsl-review\sms_rebotes_masivos.json', 'w', encoding='utf-8') as f:
        json.dump(sms_messages, f, ensure_ascii=False, indent=4)
        
    print(f"Participantes encontrados y SMS generados: {encontrados}")
    print(f"Total mensajes (PX + IMO): {len(sms_messages)}")
    conn.close()

if __name__ == "__main__":
    bounces = extract_bounced_emails()
    if bounces:
        generar_sms(bounces)
