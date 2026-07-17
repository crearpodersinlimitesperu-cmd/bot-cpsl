import imaplib
import email
import os
import sqlite3
import re
import requests
import time
import sys
from email.header import decode_header
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

sys.path.append(os.path.dirname(__file__))
from gatekeeper import Gatekeeper

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace(' ', '')
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('IDENTIDAD_Y_SMS', evento, detalle, estado))
        conn_cn.commit()
    except Exception as e:
        print(f"Error blackbox: {e}")

def decode_str(s):
    if not s: return ""
    decoded_parts = decode_header(s)
    res = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                res.append(part.decode(encoding or 'utf-8', errors='ignore'))
            except:
                res.append(part.decode('utf-8', errors='ignore'))
        else:
            res.append(part)
    return "".join(res)

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else ""

def scan_y_enviar_sms():
    print("--- INICIANDO SCAN DE INBOX PARA NUEVOS REBOTES ---")
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    gk = Gatekeeper()
    
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')
        
        status, messages = mail.search(None, '(UNSEEN)')
        msg_ids = messages[0].split()
        print(f'Se encontraron {len(msg_ids)} correos no leídos.')
        
        enviados = 0
        bloqueados = 0
        
        for i in msg_ids:
            try:
                status, data = mail.fetch(i, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])
                subject = decode_str(msg.get('Subject', ''))
                sender = decode_str(msg.get('From', ''))
                
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try: body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except: pass
                else:
                    try: body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                    except: pass
                
                # Es un rebote?
                if 'mailer-daemon' in sender.lower() or 'delivery status notification' in subject.lower() or 'undelivered' in subject.lower():
                    failed_email = ""
                    match = re.search(r'(?:to|para):\s*([\w\.-]+@[\w\.-]+)', body, re.IGNORECASE)
                    if match: failed_email = match.group(1).lower()
                    else: failed_email = extract_email(body)
                        
                    if failed_email:
                        # Buscar los PX con este correo
                        cursor.execute("SELECT id, nombre, telefono FROM participantes WHERE LOWER(email) = ?", (failed_email,))
                        afectados = cursor.fetchall()
                        
                        # Actualizar en BD a REBOTE
                        cursor.execute("UPDATE participantes SET email = 'REBOTE' WHERE LOWER(email) = ?", (failed_email,))
                        conn.commit()
                        mail.store(i, '+FLAGS', '\Seen')
                        
                        for px in afectados:
                            px_id, nombre_full, tel = px
                            nombre_corto = nombre_full.split()[0].title() if nombre_full else "Participante"
                            
                            # VALIDACIÓN GATEKEEPER PARA SMS C1/C2
                            # Como esto es para rezagados, probamos campana C1
                            valido, razon = gk.validate_send(participante_id=px_id, canal='SMS', campana_tipo='C1')
                            
                            if not valido:
                                bloqueados += 1
                                print(f"⛔ SMS Bloqueado por Gatekeeper para ID {px_id} ({nombre_corto}): {razon}")
                                continue
                                
                            # Enviar SMS via MacroDroid
                            tel_clean = "".join(filter(str.isdigit, str(tel)))
                            if len(tel_clean) > 9 and tel_clean.startswith("51"):
                                tel_clean = tel_clean[2:]
                                
                            texto = f"Hola {nombre_corto}, te escribimos de CREAR. Intentamos enviarte tu info de C1 a {failed_email} pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
                            
                            url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
                            params = {"numero": tel_clean, "mensaje": texto}
                            
                            print(f"Enviando SMS a {nombre_corto} ({tel_clean})... ", end="", flush=True)
                            
                            try:
                                r = requests.get(url, params=params, timeout=10)
                                if r.status_code == 200:
                                    print("[OK]", flush=True)
                                    enviados += 1
                                    log_blackbox(conn_cn, 'ENVIO_SMS_NUEVO_REBOTE', f'Enviado a {tel_clean}', 'COMPLETADO')
                                else:
                                    print(f"[ERROR {r.status_code}]", flush=True)
                            except Exception as e:
                                print(f"[EXCEPCION: {str(e)}]", flush=True)
                            
                            time.sleep(5)
            except Exception as e:
                pass
                
        print(f"\n--- FIN DE PROCESO ---")
        print(f"SMS Enviados: {enviados} | Bloqueados por Gatekeeper: {bloqueados}")
        
    except Exception as e:
        print(f'Error general: {e}')
    finally:
        mail.logout()
        conn.close()
        conn_cn.close()

if __name__ == "__main__":
    scan_y_enviar_sms()
