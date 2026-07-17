import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import sqlite3
import re
from email.header import decode_header
import sys
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace(' ', '')
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('COMUNICACIONES', evento, detalle, estado))
        conn_cn.commit()
    except:
        pass

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

def responder_correos():
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(EMAIL_USER, EMAIL_PASS)
    mail.select('inbox')
    
    # Buscar correos no leídos desde hoy o ayer
    status, messages = mail.search(None, '(UNSEEN)')
    msg_ids = messages[0].split()
    
    print(f"--- INICIANDO RESPUESTA AUTOMÁTICA ({len(msg_ids)} no leídos) ---")
    
    if not msg_ids:
        return
        
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    
    procesados = 0
    
    for i in msg_ids:
        try:
            status, data = mail.fetch(i, '(RFC822)')
            msg = email.message_from_bytes(data[0][1])
            subject = decode_str(msg.get('Subject', ''))
            sender = decode_str(msg.get('From', ''))
            msg_id_header = msg.get('Message-ID', '')
            
            # Saltar si es del sistema o mailer-daemon
            if 'mailer-daemon' in sender.lower() or 'crearpodersinlimitesperu' in sender.lower():
                continue
                
            sender_email = extract_email(sender)
            
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except: pass
            else:
                try:
                    body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                except: pass
                
            # Extraer nuevo correo (o asumir el del remitente si lo pide explícitamente)
            nuevo_correo = ""
            match = re.search(r'([\w\.-]+@[\w\.-]+)', body, re.IGNORECASE)
            if match:
                nuevo_correo = match.group(1).lower()
            else:
                nuevo_correo = sender_email
                
            nombre_sender = sender.split('<')[0].strip()
            
            # Intentar actualizar BD (por nombre o porque ya sabíamos que rebotó)
            cursor.execute("UPDATE participantes SET email = ? WHERE nombre || ' ' || apellido LIKE ? OR email = 'REBOTE'", (nuevo_correo, f"%{nombre_sender[:10]}%"))
            conn.commit()
            
            # Responder
            html_reply = f"""
            <html>
                <body>
                    <p>Hola {nombre_sender.title()},</p>
                    <p>Gracias por comunicarte con nosotros. Hemos recibido y actualizado tu correo electrónico (<strong>{nuevo_correo}</strong>) exitosamente en nuestra base de datos central.</p>
                    <p>En breve te estaremos reenviando toda la información oficial correspondiente a tu Capítulo.</p>
                    <p>¡Seguimos en el proceso!</p>
                    <p>Saludos,<br><strong>Equipo Crear Poder Sin Límites</strong></p>
                </body>
            </html>
            """
            
            reply_msg = MIMEMultipart()
            reply_msg['From'] = f"Crear Poder Sin Limites <{EMAIL_USER}>"
            reply_msg['To'] = sender_email
            reply_msg['Subject'] = f"Re: {subject}"
            if msg_id_header:
                reply_msg['In-Reply-To'] = msg_id_header
                reply_msg['References'] = msg_id_header
                
            reply_msg.attach(MIMEText(html_reply, 'html'))
            server.send_message(reply_msg)
            
            # Marcar como leído
            mail.store(i, '+FLAGS', '\Seen')
            
            print(f"✅ Respuesta enviada a {sender_email}. BD actualizada a {nuevo_correo}.")
            log_blackbox(conn_cn, 'RESPUESTA_AUTOMATICA', f'Respondido a {sender_email}. Nuevo correo {nuevo_correo}.', 'COMPLETADO')
            procesados += 1
            
        except Exception as e:
            print(f"❌ Error procesando correo: {e}")
            
    server.quit()
    mail.logout()
    conn.close()
    conn_cn.close()
    print(f"--- PROCESADOS: {procesados} ---")

if __name__ == "__main__":
    responder_correos()
