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

def enviar_magna_v4_rocio_final():
    print("--- INICIANDO DESPACHO DEFINITIVO MAGNA v4.1 (ROCÍO) ---")
    db = SessionLocal()
    
    # 1. Recuperar Contenido del HTML Magna v4 Final
    html_path = r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_magna_v4_final.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 2. Configurar el Correo
    msg = MIMEMultipart()
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = "rjampuero@gmail.com"
    msg['Subject'] = "✨ Bienvenido(a) a CAPÍTULO 1 | Equipo 28 Lima — Confirmación Oficial de Inscripción"
    msg.attach(MIMEText(html_content, 'html'))

    # 3. Kit de Adjuntos Oficial (Caja Negra)
    adjuntos = [
        {
            "path": r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\CAPITULO UNO\C1ACUERDO DE PARTICIPACIÓN, EXONERACIÓN DE RESPONSABILIDAD Y TÉRMINOS DEL SERVICIO.pdf",
            "name": "Contrato y Términos del Servicio.pdf"
        },
        {
            "path": r"C:\Users\josem\Downloads\Documentos\Manuales y Materiales CREAR\Terminos_y_Condiciones_Web_C1.txt.pdf",
            "name": "Declaración de aceptación digital.pdf"
        },
        {
            "path": r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\CAPITULO UNO\Manual Grounding Zoom Capítulo Uno.pdf",
            "name": "Recomendaciones generales para participantes.pdf"
        },
        {
            "path": r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\CAPITULO UNO\BIENVENIDO A  CAPITULO UNO E17 LIMA.pdf",
            "name": "Indicaciones logísticas y de asistencia.pdf"
        }
    ]

    for adj in adjuntos:
        if os.path.exists(adj["path"]):
            try:
                with open(adj["path"], "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={adj['name']}")
                    msg.attach(part)
                    print(f"   [OK] Adjuntado: {adj['name']}")
            except Exception as e:
                print(f"   [ERR] Error al adjuntar {adj['name']}: {e}")

    try:
        # 4. Envío SMTP Blindado
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        
        print("   [OK] Correo Magna v4.1 enviado a ROCÍO.")

        # 5. Registrar en Caja Negra (Trazabilidad 360)
        px = db.query(Usuario).filter(Usuario.email == "rjampuero@gmail.com").first()
        px_id = px.id if px else 0
        
        t = TrazabilidadPX(
            px_id=px_id,
            canal="EMAIL",
            tipo_evento="ENVIO_BIENVENIDA_MAGNA_FINAL",
            contenido="Bienvenida Suprema Magna v4.1 (Kit 4 Adjuntos) enviada exitosamente.",
            metadatos='{"asunto": "MAGNA SUPREMA C1 E28", "version": "4.1"}'
        )
        db.add(t)
        
        log = LogEnvio(
            destino="rjampuero@gmail.com",
            tipo="OUT",
            canal="EMAIL",
            mensaje="Bienvenida Magna v4.1 C1 E28",
            status_code=200
        )
        db.add(log)
        db.commit()
        print("   [OK] Acción registrada en la Caja Negra Pro.")

    except Exception as e:
        print(f"   [ERR] Error en el despacho Magna Final: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    enviar_magna_v4_rocio_final()
