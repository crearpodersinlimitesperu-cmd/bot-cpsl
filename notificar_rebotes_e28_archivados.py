import imaplib
import email
import os
import re
import sqlite3
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import urllib.parse
from datetime import date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "bgsl xjus xsmn pzqd").replace('"', '').replace(" ", "")

EXCEL_PATH = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

def extract_failed_recipient(body):
    patterns = [
        r"no se entreg[o\xf3] a ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"delivered to ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"Final-Recipient: rfc822; ([^\s\n\r]+)",
        r"To: ([^\s\n\r<]+@[^\s\n\r>]+)",
        r"Tu mensaje no se entreg[o\xf3] a ([^\s\n\r<]+@[^\s\n\r>]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.I)
        if match:
            return match.group(1).strip(".<>").lower()
    return None

def fetch_bounces():
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)
    
    # Buscar en Todos los Mensajes (incluye archivados)
    status, msg = mail.select('"[Gmail]/Todos"')
    if status != 'OK':
        print("No se pudo abrir la carpeta Todos, usando inbox")
        mail.select("inbox")
            
    # Buscar correos de Mail Delivery Subsystem de los ltimos 2 das para evitar problemas de zona horaria
    date_str = date.today().strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(FROM "mailer-daemon@googlemail.com")')
    
    rebotes = set()
    if status == 'OK':
        # Tomar los ltimos 50 correos del daemon para estar seguros
        msg_ids = messages[0].split()[-50:]
        for num in msg_ids:
            status, data = mail.fetch(num, '(RFC822)')
            if status == 'OK':
                msg = email.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body += part.get_payload(decode=True).decode(errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                
                correo_rebotado = extract_failed_recipient(body)
                if correo_rebotado:
                    rebotes.add(correo_rebotado)
    
    mail.close()
    mail.logout()
    return rebotes

print("1. Conectando a IMAP para buscar rebotes recientes (incluyendo archivados)...")
bounces = fetch_bounces()
print(f"Encontrados {len(bounces)} correos rebotados histricos recientes en total.")

print("\n2. Leyendo Excel y cruzando con Equipo 28...")
df = pd.read_excel(EXCEL_PATH)
df_e28 = df[df['NombreEquipo'].str.contains('28', case=False, na=False)].copy()
df_e28['Correo'] = df_e28['Correo'].astype(str).str.strip().str.lower()

# Filtrar los rebotados que pertenecen al E28
df_rebotes_e28 = df_e28[df_e28['Correo'].isin(bounces)]
print(f"De esos, {len(df_rebotes_e28)} pertenecen al Equipo 28.")

if len(df_rebotes_e28) == 0:
    print("No hay rebotes del Equipo 28. Finalizando.")
    exit()

print("\n3. Buscando IMOs en la base de datos...")
# Agrupar por IdentificacionIMO
imos_afectados = df_rebotes_e28.groupby('IdentificacionIMO').apply(lambda x: x[['NombreCompleto', 'ApellidoCompleto', 'Correo']].to_dict('records')).to_dict()

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
server.login(EMAIL_USER, EMAIL_PASS)

notificados = 0
for imo_dni, pxs in imos_afectados.items():
    imo_dni = str(imo_dni).strip()
    
    # Buscar datos del IMO en la BD
    cursor.execute("SELECT nombre, apellido, email, telefono FROM participantes WHERE identificacion = ? AND (email IS NOT NULL OR telefono IS NOT NULL) LIMIT 1", (imo_dni,))
    imo_data = cursor.fetchone()
    
    if not imo_data:
        print(f"IMO con DNI {imo_dni} no encontrado en la BD. Saltando.")
        continue
        
    imo_nom, imo_ape, imo_email, imo_tel = imo_data
    imo_full = f"{imo_nom} {imo_ape}".strip().title()
    imo_nom_pila = str(imo_nom).split()[0].title() if imo_nom else "Estimado/a IMO"
    
    print(f"\nProcesando IMO: {imo_full} ({imo_dni})")
    
    lista_px_html = ""
    lista_px_sms = ""
    for p in pxs:
        px_nom = str(p['NombreCompleto']).title()
        px_ape = str(p['ApellidoCompleto']).title()
        px_cor = str(p['Correo'])
        lista_px_html += f"<li>{px_nom} {px_ape} (Correo errado: {px_cor})</li>\n"
        lista_px_sms += f"- {px_nom} {px_ape}\n"
    
    # ENVIAR CORREO
    if imo_email and "@" in str(imo_email):
        try:
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; color: #333;">
                    <p>Hola <strong>{imo_nom_pila}</strong>,</p>
                    <p>Te escribimos de parte del equipo de <strong>Crear Poder Sin Lmites</strong>.</p>
                    <p>Acabamos de enviar la campaa de bienvenida del <strong>Captulo 1</strong> (Equipo 28) a los participantes bajo tu enrolamiento. Sin embargo, hemos detectado que <strong>los correos de los siguientes participantes han rebotado</strong> (son invalidos o estan mal escritos):</p>
                    <ul>{lista_px_html}</ul>
                    <p>Para asegurar que no se pierdan ningun detalle del evento, te pedimos por favor que te comuniques con ellos y nos respondas a este correo con sus <strong>direcciones de email correctas y actualizadas</strong>.</p>
                    <p>Gracias por tu apoyo en su proceso!</p>
                    <p>Saludos cordiales,<br><strong>Equipo Crear Poder Sin Lmites</strong></p>
                </body>
            </html>
            """
            msg = MIMEMultipart()
            msg['Subject'] = 'URGENTE: Correos rebotados de tus participantes (Equipo 28)'
            msg['From'] = EMAIL_USER
            msg['To'] = imo_email
            msg.attach(MIMEText(html_body, 'html'))
            server.send_message(msg)
            print(f" -> Correo enviado a {imo_email}")
        except Exception as e:
            print(f" -> Error enviando correo a {imo_email}: {e}")
    else:
        print(f" -> No tiene email valido registrado.")
        
    # ENVIAR SMS
    if imo_tel:
        try:
            imo_tel_clean = re.sub(r'\D', '', str(imo_tel))
            if not imo_tel_clean.startswith("51"):
                if len(imo_tel_clean) == 9:
                    imo_tel_clean = "51" + imo_tel_clean
            if len(imo_tel_clean) >= 11:
                sms_text = f"Hola {imo_nom_pila}, de CREAR. Los correos de tus participantes (E28) han rebotado:\n{lista_px_sms.strip()}\nPor favor envianos sus correos correctos. Gracias!"
                sms_encoded = urllib.parse.quote(sms_text)
                url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}?numero={imo_tel_clean}&mensaje={sms_encoded}"
                resp = requests.get(url, timeout=10)
                print(f" -> SMS enviado a {imo_tel_clean} (Status: {resp.status_code})")
        except Exception as e:
            print(f" -> Error enviando SMS a {imo_tel}: {e}")
            
    notificados += 1

server.quit()
conn.close()

print(f"\nResumen: {notificados} IMOs notificados sobre sus rebotes en E28.")
