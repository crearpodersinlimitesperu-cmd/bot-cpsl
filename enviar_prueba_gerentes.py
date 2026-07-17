import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time

# Credenciales
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

GERENTES = [
    "emily.campuzano@crearpsl.com",
    "freddy.sosa@crearpsl.com",
    "josue.vera@crearpsl.com",
    "emely.leon@crearpsl.com",
    "yurany.gonzalez@crearpsl.com",
    "jose.sanchez@crearpsl.com" # También te lo envío a ti para que confirmes que llegó
]

def enviar_pruebas_gerentes():
    print("--- INICIANDO ENVÍO DE PRUEBA A GERENTES ---")
    
    try:
        # Recuperar Contenido del Artefacto de Rocío
        with open(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\bienvenida_rocio.html", "r", encoding="utf-8") as f:
            html_content = f.read()

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        
        for email in GERENTES:
            msg = MIMEMultipart()
            msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
            msg['To'] = email
            msg['Subject'] = "[TEST] ¡BIENVENIDA AL EQUIPO 28, ROCIO! Tu camino comienza aquí"
            msg.attach(MIMEText(html_content, 'html'))
            
            server.send_message(msg)
            print(f"   [OK] Prueba enviada exitosamente a: {email}")
            time.sleep(1) # Pausa por seguridad anti-spam
            
        server.quit()
        print("--- TODOS LOS ENVÍOS FUERON EXITOSOS ---")

    except Exception as e:
        print(f"   [ERR] Error en el despacho: {e}")

if __name__ == "__main__":
    enviar_pruebas_gerentes()
