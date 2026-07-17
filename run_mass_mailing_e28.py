import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import time
import sys

excel_path = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'
html_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html'
banner_path = r'c:\Users\josem\Downloads\bot-cpsl-review\templates\banner_c1_e28.jpg'

sender = "crearpodersinlimitesperu@gmail.com"
password = "bgsl xjus xsmn pzqd".replace(" ", "")

print("Leyendo Excel completo...")
df = pd.read_excel(excel_path)

# Filtrar Equipo 28
df_e28 = df[df['NombreEquipo'].str.contains('28', case=False, na=False)]
df_e28 = df_e28.dropna(subset=['Correo']) # Evitar procesar sin correo

with open(html_path, 'r', encoding='utf-8') as f:
    html_template = f.read()

with open(banner_path, 'rb') as f:
    banner_data = f.read()

total = len(df_e28)
print(f"Total a enviar para EQUIPO 28: {total} correos.")

# Mapeo de coordinadores a WhatsApp
coords_wa = {
    'jmarin': '51933599903',
    'dmoscoso': '51912379744',
    'jsanchez': '51919563284'
}

enviados = 0
errores = 0

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender, password)
        print("Conectado al servidor SMTP. Iniciando envíos...\n")
        
        for index, row in df_e28.iterrows():
            nombre = str(row['NombreCompleto']).strip().title()
            # Si tiene varios nombres, tomar el primero
            primer_nombre = nombre.split()[0] if ' ' in nombre else nombre
            
            correo = str(row['Correo']).strip().lower()
            coord_id = str(row['Usuario Actual']).strip().lower()
            wa_coord = coords_wa.get(coord_id, '51919563284') # Default a Jose por si acaso
            
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

print(f"\n\n=== RESUMEN DE CAMPAÑA EQUIPO 28 ===")
print(f"Total enviados exitosamente: {enviados}")
print(f"Errores de envío: {errores}")
