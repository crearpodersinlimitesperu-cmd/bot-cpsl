import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_prueba_institucional_final():
    print("--- INICIANDO DESPACHO INSTITUCIONAL v3.0 (CREACION CUANTICA) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Institucional Final
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_institucional_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com"
    msg['Subject'] = "BIENVENIDA OFICIAL | Capítulo 1 — Equipo 28 Lima (Creación Cuántica)"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # 3. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo Institucional v3.0 enviado a Jose Sanchez.")

        # 4. Registrar en Caja Negra
        t = TrazabilidadPX(
            px_id=0,
            canal="EMAIL",
            tipo_evento="TEST_ENVIO_INSTITUCIONAL",
            contenido="Prueba de diseño Institucional v3.0 (Creación Cuántica) para Jose Sanchez.",
            metadatos='{"asunto": "INSTITUCIONAL C1 E28", "standard": "PREMIUM_PRO"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Prueba Institucional registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho Institucional: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_prueba_institucional_final()
