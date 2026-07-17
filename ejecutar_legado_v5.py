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

def enviar_legado_v5_seguro():
    print("--- INICIANDO DESPACHO SUPREMO LEGADO v5.0 (UNICO ADJUNTO) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Legado v5 Final
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_legado_v5_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com"
    msg['Subject'] = "✨ Bienvenido(a) a CAPÍTULO 1 | Equipo 28 Lima — Confirmación Oficial de Inscripción"
    msg.attach(MIMEText(html_content, 'html'))

    # 3. Adjunto ÚNICO: Contrato Legado (Seguridad Máxima)
    file_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_Legado_ROCIO_JARA.pdf"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=Contrato de Prestacion de Servicios - Programa Capitulo Uno - ROCIO JARA.pdf",
                )
                msg.attach(part)
                print("   [OK] Contrato Legado v5.0 adjuntado exitosamente.")
        except Exception as e:
            print(f"   [ERR] Error al adjuntar contrato: {e}")
    else:
        print(f"   [ERR] No se encontró el archivo en: {file_path}")

    try:
        # 4. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo Legado v5.0 enviado a Jose Sanchez.")

        # 5. Registrar en Caja Negra
        t = TrazabilidadPX(
            px_id=0,
            canal="EMAIL",
            tipo_evento="ENVIO_LEGADO_V5",
            contenido="Prueba Legado v5.0 con UNICO adjunto PDF diligenciado para Jose Sanchez.",
            metadatos='{"asunto": "LEGADO SUPREMO", "version": "5.0"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Prueba Legado v5.0 registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho supremo: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_legado_v5_seguro()
