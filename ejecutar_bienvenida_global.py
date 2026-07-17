import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_bienvenida_global():
    print("--- INICIANDO DESPACHO DE BIENVENIDA ELITE GLOBAL (SINCRONIZADO) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Global Final
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_global_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Crear Global <{EMAIL_USER}>" # Remitente como Crear Global
    msg['To'] = "rjampuero@gmail.com"
    msg['Subject'] = "¡BIENVENIDA AL EQUIPO 28, ROCIO! Tu camino de poder comienza hoy"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # 3. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo de bienvenida Global enviado a ROCIO.")

        # 4. Registrar en Caja Negra (Trazabilidad 360)
        px = db.query(Usuario).filter(Usuario.email == "rjampuero@gmail.com").first()
        px_id = px.id if px else 0
        
        t = TrazabilidadPX(
            px_id=px_id,
            canal="EMAIL",
            tipo_evento="ENVIO_BIENVENIDA_GLOBAL",
            contenido="Bienvenida Elite Global (Sincronizada con crearglobal.com) enviada exitosamente.",
            metadatos='{"asunto": "¡BIENVENIDA AL EQUIPO 28, ROCIO!", "brand": "GLOBAL"}'
        )
        db.add(t)
        
        log = LogEnvio(
            destino="rjampuero@gmail.com",
            tipo="OUT",
            canal="EMAIL",
            mensaje="Bienvenida Elite C1 E28 GLOBAL",
            status_code=200
        )
        db.add(log)
        db.commit()
        print("   [OK] Acción registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho Global: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_bienvenida_global()
