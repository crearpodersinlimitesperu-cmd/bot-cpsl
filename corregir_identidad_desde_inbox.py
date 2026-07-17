import imaplib
import email
import os
import sqlite3
import re
from email.header import decode_header

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
EMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace(' ', '')
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('IDENTIDAD', evento, detalle, estado))
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

def scan_inbox():
    print("--- INICIANDO SCAN DE INBOX ---")
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('inbox')
        
        # Buscar correos desde el día 10 de Mayo
        status, messages = mail.search(None, '(SINCE "10-May-2026")')
        msg_ids = messages[0].split()
        print(f'Se encontraron {len(msg_ids)} correos recientes en Inbox.')
        
        rebotes_encontrados = 0
        respuestas_encontradas = 0
        correcciones_db = 0
        
        for i in msg_ids:
            try:
                status, data = mail.fetch(i, '(RFC822)')
                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        subject = decode_str(msg.get('Subject'))
                        sender = decode_str(msg.get('From'))
                        
                        # Extraer cuerpo para análisis de respuestas
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    try:
                                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                    except:
                                        pass
                        else:
                            try:
                                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                            except:
                                pass
                        
                        # Detectar Rebote
                        if 'mailer-daemon' in sender.lower() or 'delivery status notification' in subject.lower() or 'undelivered' in subject.lower():
                            rebotes_encontrados += 1
                            # Buscar a quién falló
                            failed_email = ""
                            match = re.search(r'(?:to|para):\s*([\w\.-]+@[\w\.-]+)', body, re.IGNORECASE)
                            if match:
                                failed_email = match.group(1).lower()
                            else:
                                failed_email = extract_email(body) # fallback
                                
                            if failed_email:
                                cursor.execute("UPDATE participantes SET email = 'REBOTE' WHERE email = ?", (failed_email,))
                                if cursor.rowcount > 0:
                                    correcciones_db += 1
                                    log_blackbox(conn_cn, 'REBOTE_CORREGIDO', f'Email rebotado marcado como REBOTE: {failed_email}', 'COMPLETADO')
                        
                        # Detectar Respuesta de participante
                        elif 'crearpodersinlimitesperu@gmail.com' not in sender.lower():
                            respuestas_encontradas += 1
                            sender_email = extract_email(sender)
                            
                            # Si en el cuerpo nos da su correo correcto, o si simplemente responde, podemos intentar cruzar por nombre
                            # O buscar si dice "mi correo es..."
                            nuevo_correo_match = re.search(r'mi (?:nuevo )?correo es:?\s*([\w\.-]+@[\w\.-]+)', body, re.IGNORECASE)
                            if nuevo_correo_match:
                                nuevo_correo = nuevo_correo_match.group(1).lower()
                                # Intentar buscar por remitente o nombre en el sender
                                cursor.execute("UPDATE participantes SET email = ? WHERE nombre || ' ' || apellido LIKE ?", (nuevo_correo, f"%{sender.split('<')[0].strip()}%"))
                                if cursor.rowcount > 0:
                                    correcciones_db += 1
                                    log_blackbox(conn_cn, 'CORREO_ACTUALIZADO_POR_RESPUESTA', f'Actualizado a {nuevo_correo}', 'COMPLETADO')
            except Exception as e:
                pass
                
        conn.commit()
        print(f"Rebotes procesados: {rebotes_encontrados}")
        print(f"Respuestas procesadas: {respuestas_encontradas}")
        print(f"Correcciones en DB: {correcciones_db}")
        
        log_blackbox(conn_cn, 'AUDITORIA_INBOX', f'Rebotes: {rebotes_encontrados}, Respuestas: {respuestas_encontradas}, Correcciones DB: {correcciones_db}', 'COMPLETADO')
        mail.logout()
        
    except Exception as e:
        print(f'Error general IMAP: {e}')
    finally:
        conn.close()
        conn_cn.close()

if __name__ == "__main__":
    scan_inbox()
