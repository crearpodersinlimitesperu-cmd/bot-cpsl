import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time
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

def enviar_correos_imos():
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    # Obtener rebotes y agrupar por IMO
    cursor.execute('''
        SELECT id, nombre, apellido, imo 
        FROM participantes 
        WHERE email = 'REBOTE' AND imo IS NOT NULL AND imo != ''
    ''')
    rebotes = cursor.fetchall()
    
    imos_dict = {}
    for px in rebotes:
        px_id, nom, ape, imo_name = px
        imo_clean = str(imo_name).strip()
        if imo_clean not in imos_dict:
            imos_dict[imo_clean] = []
        imos_dict[imo_clean].append(f"{nom} {ape}")
        
    print(f"--- INICIANDO ENVÍO A IMOS ({len(imos_dict)} únicos) ---")
    
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    
    enviados = 0
    errores = 0
    
    for imo_name, pxs in imos_dict.items():
        # Buscar el correo del IMO en la DB
        cursor.execute("SELECT email FROM participantes WHERE nombre || ' ' || apellido LIKE ? AND email IS NOT NULL AND email != 'REBOTE' LIMIT 1", (f"%{imo_name[:12]}%",))
        imo_email_row = cursor.fetchone()
        
        if not imo_email_row:
            print(f"⚠️ IMO sin correo en BD: {imo_name}")
            continue
            
        imo_email = imo_email_row[0]
        
        lista_px = "\n".join([f"• {px}" for px in pxs])
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333;">
                <p>Hola <strong>{imo_name.title()}</strong>,</p>
                <p>Te escribimos de parte del equipo de <strong>Crear Poder Sin Límites</strong>.</p>
                <p>Durante nuestra campaña reciente, intentamos enviar información importante a los siguientes participantes bajo tu enrolamiento, pero <strong>los correos electrónicos registrados han rebotado</strong> (son inválidos o están mal escritos):</p>
                <p><strong>Participantes afectados:</strong></p>
                <ul>{lista_px}</ul>
                <p>Para asegurar que no se pierdan ningún detalle del Capítulo, te pedimos por favor que te comuniques con ellos y nos respondas a este correo con sus <strong>direcciones de email correctas y actualizadas</strong>.</p>
                <p>¡Gracias por tu apoyo en su proceso!</p>
                <p>Saludos cordiales,<br><strong>Equipo Crear Poder Sin Límites</strong></p>
            </body>
        </html>
        """
        
        msg = MIMEMultipart()
        msg['From'] = f"Crear Poder Sin Limites <{EMAIL_USER}>"
        msg['To'] = imo_email
        msg['Subject'] = "IMPORTANTE: Correos inválidos de tus enrolados"
        msg.attach(MIMEText(html_body, 'html'))
        
        try:
            server.send_message(msg)
            print(f"✅ Enviado a IMO {imo_name} ({imo_email})")
            enviados += 1
            log_blackbox(conn_cn, 'EMAIL_A_IMO', f"Solicitud actualización enviada a {imo_email} para PXs: {len(pxs)}", 'COMPLETADO')
            time.sleep(2) # Pausa para evitar rate limits
        except Exception as e:
            print(f"❌ Error al enviar a {imo_email}: {e}")
            errores += 1
            log_blackbox(conn_cn, 'ERROR_EMAIL_IMO', str(e), 'ERROR')
            
    server.quit()
    conn.close()
    conn_cn.close()
    
    print(f"--- RESUMEN ---")
    print(f"Enviados: {enviados} | Errores: {errores}")

if __name__ == "__main__":
    enviar_correos_imos()
