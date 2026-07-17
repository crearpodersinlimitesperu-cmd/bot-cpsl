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

def enviar_integra_v8_final_suprema():
    print("--- INICIANDO DESPACHO INTEGRA v8.1 (FIDELIDAD ABSOLUTA FINAL) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Integra v8 (Transcripción Literal)
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_integra_v8_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = "jose.sanchez@crearpsl.com"
    msg['Subject'] = "✨ Bienvenido(a) a CAPÍTULO 1 | Equipo 28 Lima — Confirmación Oficial de Inscripción"
    msg.attach(MIMEText(html_content, 'html'))

    # 3. Adjunto ÚNICO: Contrato Integra v8.1 (Protocolo Literal)
    file_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_Integro_ROCIO_JARA.pdf"
    if os.path.exists(file_path):
        try:
            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename=Contrato de Terminos y Condiciones - Programa Capitulo Uno - ROCIO JARA.pdf",
                )
                msg.attach(part)
                print("   [OK] Contrato Integra v8.1 adjuntado exitosamente.")
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
        
        print("   [OK] Correo Integra v8.1 Final enviado a Jose Sanchez.")

        # 5. Registrar en Caja Negra (Inmortalización del Protocolo)
        t = TrazabilidadPX(
            px_id=0,
            canal="EMAIL",
            tipo_evento="ENVIO_INTEGRA_V8_FINAL_SUPREMA",
            contenido="Despacho Final v8.1 (FIDELIDAD ABSOLUTA) enviado exitosamente. Texto íntegro sin simplificaciones.",
            metadatos='{"asunto": "INTEGRA SUPREMA FINAL", "version": "8.1"}'
        )
        db.add(t)
        db.commit()
        print("   [OK] Registro maestro guardado en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho maestro: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_integra_v8_final_suprema()
