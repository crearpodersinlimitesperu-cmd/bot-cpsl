import smtplib
import os
from dotenv import load_dotenv

import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(r'C:\Users\josem\Downloads\bot-cpsl-review\.env')
user = 'crearpodersinlimitesperu@gmail.com'
password = os.environ.get('GMAIL_APP_PASS', '').replace(' ', '').replace('"', '')

print(f"Probando conexión SMTP para: {user}")

try:
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(user, password)
    print("OK: SMTP Login EXITOSO. El servidor aun permite la conexion.")
    
    # Intentar enviar un correo de prueba a si mismo para verificar bloqueo de envio
    from email.mime.text import MIMEText
    msg = MIMEText("Prueba de desbloqueo")
    msg['Subject'] = "Test Connection"
    msg['From'] = user
    msg['To'] = user
    
    server.send_message(msg)
    print("OK: Envio de prueba EXITOSO. No parece haber un bloqueo total de envio.")
    server.quit()
except Exception as e:
    print(f"ERROR: SMTP: {e}")
