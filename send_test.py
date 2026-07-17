import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os

sender = "crearpodersinlimitesperu@gmail.com"
receiver = "crearpodersinlimitesperu@gmail.com"  # Sending to the same inbox for testing
password = "bgsl xjus xsmn pzqd".replace(" ", "")

if not password:
    print("Error: GMAIL_APP_PASS no está configurado.")
    exit(1)

html_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html'
banner_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\banner_c1_e28.jpg'

# Read HTML and replace variables
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

html = html.replace('{{NOMBRE}}', 'Usuario de Prueba')
html = html.replace('{{WHATSAPP_COORD}}', '51933599903')

msg = MIMEMultipart('related')
msg['Subject'] = 'PRUEBA - CREAR — Capítulo 1 · Equipo 28'
msg['From'] = f"CREAR Poder Sin Límites <{sender}>"
msg['To'] = receiver

# Attach HTML
msg_alternative = MIMEMultipart('alternative')
msg.attach(msg_alternative)
msg_alternative.attach(MIMEText(html, 'html'))

# Attach the inline image
with open(banner_path, 'rb') as f:
    img = MIMEImage(f.read())
    img.add_header('Content-ID', '<banner_c1_e28>')
    img.add_header('Content-Disposition', 'inline')
    msg.attach(img)

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        server.send_message(msg)
    print(f"EXITO: Correo de prueba enviado a {receiver}")
except Exception as e:
    print(f"ERROR al enviar el correo: {e}")
