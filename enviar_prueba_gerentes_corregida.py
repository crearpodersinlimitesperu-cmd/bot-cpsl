import smtplib
import os
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication

# Credenciales
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

GERENTES = [
    "emily.campuzano@crearpsl.com",
    "freddy.sosa@crearpsl.com",
    "josue.vera@crearpsl.com",
    "emely.leon@crearpsl.com",
    "yurany.gonzalez@crearpsl.com",
    "jose.sanchez@crearpsl.com" 
]

LOGO_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\logo_crear_blanco.png"
PDF_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_ROCIO_JARA_AMPUERO.pdf"
HTML_PATH = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\bienvenida_rocio.html"

def enviar_pruebas_gerentes_corregida():
    print("--- INICIANDO ENVÍO DE CORRECCIÓN A GERENTES ---")
    
    try:
        with open(HTML_PATH, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Si por alguna razón no existe el logo localmente, usamos una ruta alternativa de ser necesario
        # Pero logo_crear_blanco.png está en el directorio actual.

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        
        for email in GERENTES:
            msg = MIMEMultipart("related")
            msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
            msg['To'] = email
            msg['Subject'] = "[CORRECCIÓN TEST] ¡BIENVENIDA AL EQUIPO 28, ROCIO! (Versión Completa)"
            
            # Parte alternativa para el HTML
            msg_alt = MIMEMultipart("alternative")
            msg.attach(msg_alt)
            msg_alt.attach(MIMEText(html_content, 'html'))
            
            # 1. Adjuntar Logo CID para visualización inline
            if os.path.exists(LOGO_PATH):
                with open(LOGO_PATH, "rb") as f:
                    logo = MIMEImage(f.read())
                    logo.add_header("Content-ID", "<logo_crear>")
                    logo.add_header("Content-Disposition", "inline", filename="logo.png")
                    msg.attach(logo)
            else:
                print(f"ALERTA: No se encontró el logo en {LOGO_PATH}")
                
            # 2. Adjuntar el Contrato (PDF)
            if os.path.exists(PDF_PATH):
                with open(PDF_PATH, "rb") as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(PDF_PATH))
                    part['Content-Disposition'] = f'attachment; filename="{os.path.basename(PDF_PATH)}"'
                    msg.attach(part)
            else:
                print(f"ALERTA: No se encontró el PDF en {PDF_PATH}")
            
            server.send_message(msg)
            print(f"   [OK] Prueba CORREGIDA enviada a: {email}")
            time.sleep(1) # Pausa anti-spam
            
        server.quit()
        print("--- TODOS LOS ENVÍOS CORREGIDOS FUERON EXITOSOS ---")

    except Exception as e:
        print(f"   [ERR] Error en el despacho: {e}")

if __name__ == "__main__":
    enviar_pruebas_gerentes_corregida()
