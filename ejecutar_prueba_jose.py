import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_prueba_jose():
    print("--- INICIANDO DESPACHO DE PRUEBA ELITE GLOBAL (VALIDACION INTERNA) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Global Final
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_global_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Crear Global <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com"
    msg['Subject'] = "[PRUEBA] Diseño Elite Global C1 E28 - Validación de Marca"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # 3. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo de prueba enviado a Jose Sanchez.")

        # 4. Registrar en Caja Negra
        t = TrazabilidadPX(
            px_id=0, # ID 0 para pruebas internas
            canal="EMAIL",
            tipo_evento="TEST_ENVIO",
            contenido="Prueba de diseño Global C1 E28 para Jose Sanchez.",
            metadatos='{"asunto": "[PRUEBA] Diseño Elite Global", "target": "ADMIN"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Prueba registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho de prueba: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_prueba_jose()
