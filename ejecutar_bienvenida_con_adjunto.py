import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio
from datetime import datetime

# Configuración de Credenciales Blindadas
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def enviar_bienvenida_con_adjunto():
    print("--- INICIANDO DESPACHO INSTITUCIONAL v3.1 (CON ADJUNTO CONTRACTUAL) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Institucional
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_institucional_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com" # Enviando prueba a Jose
    msg['Subject'] = "BIENVENIDA OFICIAL | Capítulo 1 — Equipo 28 Lima (Documento Adjunto)"
    msg.attach(MIMEText(html_content, 'html'))

    # 3. Inyectar Adjunto Contractual
    file_path = r"C:\Users\josem\Downloads\Documentos\Manuales y Materiales CREAR\Terminos_y_Condiciones_Web_C1.txt.pdf"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=Terminos y Condiciones del Servicio - Programa Capitulo Uno.pdf",
                )
                msg.attach(part)
                print("   [OK] Documento contractual adjuntado.")
        except Exception as e:
            print(f"   [ERR] Error al adjuntar archivo: {e}")
    else:
        print(f"   [ERR] No se encontró el archivo en: {file_path}")

    try:
        # 4. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo Institucional con adjunto enviado a Jose Sanchez.")

        # 5. Registrar en Caja Negra
        t = TrazabilidadPX(
            px_id=0,
            canal="EMAIL",
            tipo_evento="TEST_ENVIO_CON_ADJUNTO",
            contenido="Prueba Institucional v3.1 con adjunto PDF para Jose Sanchez.",
            metadatos='{"asunto": "CON ADJUNTO", "file": "Terminos_y_Condiciones_Web_C1.txt.pdf"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Prueba con adjunto registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_bienvenida_con_adjunto()
