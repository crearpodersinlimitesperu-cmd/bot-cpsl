import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import time
import sys

csv_path = r'c:\Users\josem\Downloads\bot-cpsl-review\Aptos_E26_E27_ZeroBounces.csv'
html_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html'
banner_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\banner_c1_e28.jpg'

sender = "crearpodersinlimitesperu@gmail.com"
password = "bgsl xjus xsmn pzqd".replace(" ", "")

print("Leyendo lista final...")
df = pd.read_csv(csv_path)

with open(html_path, 'r', encoding='utf-8') as f:
    html_template = f.read()

with open(banner_path, 'rb') as f:
    banner_data = f.read()

total = len(df)
print(f"Total a enviar: {total} correos.")

# Mapeo de coordinadores a WhatsApp
coords_wa = {
    'jmarin': '51933599903',
    'dmoscoso': '51912379744'
}

enviados = 0
errores = 0

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        print("Conectado al servidor SMTP. Iniciando envíos...\n")
        
        for index, row in df.iterrows():
            nombre = str(row['NombreCompleto']).strip().title()
            # Si tiene varios nombres, tomar el primero
            primer_nombre = nombre.split()[0] if ' ' in nombre else nombre
            
            correo = str(row['Correo']).strip().lower()
            coord_id = str(row['Usuario Registro']).strip().lower()
            wa_coord = coords_wa.get(coord_id, '51933599903') # Default a Joyce si no coincide
            
            # Personalizar HTML
            html = html_template.replace('{{NOMBRE}}', primer_nombre)
            html = html.replace('{{WHATSAPP_COORD}}', wa_coord)
            
            msg = MIMEMultipart('related')
            msg['Subject'] = 'CREAR — Capítulo 1 · Equipo 28'
            msg['From'] = f"CREAR Poder Sin Límites <{sender}>"
            msg['To'] = correo
            
            msg_alt = MIMEMultipart('alternative')
            msg.attach(msg_alt)
            msg_alt.attach(MIMEText(html, 'html'))
            
            img = MIMEImage(banner_data)
            img.add_header('Content-ID', '<banner_c1_e28>')
            img.add_header('Content-Disposition', 'inline')
            msg.attach(img)
            
            try:
                server.send_message(msg)
                enviados += 1
                sys.stdout.write(f"\r[{enviados}/{total}] Enviado a {correo} ({primer_nombre})")
                sys.stdout.flush()
                time.sleep(2) # Pausa para evitar rate limit de Gmail
            except Exception as e:
                errores += 1
                print(f"\n[!] Error enviando a {correo}: {e}")
                
except Exception as e:
    print(f"\nError de conexión SMTP: {e}")

print(f"\n\n=== RESUMEN DE CAMPAÑA ===")
print(f"Total enviados exitosamente: {enviados}")
print(f"Errores de envío: {errores}")
