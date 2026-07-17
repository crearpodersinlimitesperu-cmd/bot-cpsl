import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio, init_db
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_bienvenida_rocio():
    print("--- INICIANDO DESPACHO DE BIENVENIDA ELITE (ROCIO) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del Artefacto
    with open(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\bienvenida_rocio.html", "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
    msg['To'] = "rjampuero@gmail.com"
    msg['Subject'] = "¡BIENVENIDA AL EQUIPO 28, ROCIO! Tu camino comienza aquí"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # 3. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo de bienvenida enviado a ROCIO.")

        # 4. Registrar en Caja Negra (Trazabilidad 360)
        # Buscamos al usuario o lo creamos si no existe
        px = db.query(Usuario).filter(Usuario.email == "rjampuero@gmail.com").first()
        px_id = px.id if px else 0
        
        t = TrazabilidadPX(
            px_id=px_id,
            canal="EMAIL",
            tipo_evento="ENVIO_BIENVENIDA",
            contenido="Bienvenida Elite C1 E28 enviada exitosamente.",
            metadatos='{"asunto": "¡BIENVENIDA AL EQUIPO 28, ROCIO!", "template": "bienvenida_rocio.html"}'
        )
        db.add(t)
        
        log = LogEnvio(
            destino="rjampuero@gmail.com",
            tipo="OUT",
            canal="EMAIL",
            mensaje="Bienvenida Elite C1 E28",
            status_code=200
        )
        db.add(log)
        db.commit()
        print("   [OK] Acción registrada en la Caja Negra.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_bienvenida_rocio()
