import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_prueba_premium_pro():
    print("--- INICIANDO DESPACHO DE PRUEBA PREMIUM PRO (DEEP NIGHT & GOLD) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Premium Pro
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_premium_pro.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Crear Global <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com"
    msg['Subject'] = "ACCESO OFICIAL | Bienvenido a tu Capítulo Uno – Equipo 28 Lima"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # 3. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo Premium Pro enviado a Jose Sanchez.")

        # 4. Registrar en Caja Negra
        t = TrazabilidadPX(
            px_id=0,
            canal="EMAIL",
            tipo_evento="TEST_ENVIO_PREMIUM_PRO",
            contenido="Prueba de diseño Premium Pro para Jose Sanchez.",
            metadatos='{"asunto": "PREMIUM PRO C1 E28", "style": "DEEP_NIGHT"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Prueba Premium Pro registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho Premium Pro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_prueba_premium_pro()
