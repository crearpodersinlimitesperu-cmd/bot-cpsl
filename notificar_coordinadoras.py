import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
from datetime import datetime
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
DESTINATARIOS = ["diana.moscoso@example.com", "joyce.marin@example.com"] # Reemplazar con reales

def obtener_stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM participantes WHERE c1 = 'SI'")
    si_c1 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM participantes WHERE c1 = 'NO' AND es_pendiente_real = 'SI'")
    pend_c1 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM participantes WHERE c2 = 'SI'")
    si_c2 = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM participantes WHERE resultado_gestion = 'REBOTE_MAIL'")
    rebotes = c.fetchone()[0]
    conn.close()
    return si_c1, pend_c1, si_c2, rebotes

def enviar_reporte():
    si_c1, pend_c1, si_c2, rebotes = obtener_stats()
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = ", ".join(DESTINATARIOS)
    msg['Subject'] = f"🚀 REPORTE ESTRATÉGICO CPSL LIMA - {datetime.now().strftime('%d/%m/%Y')}"

    cuerpo = f"""
Estimadas Diana y Joyce,

Espero que este mensaje las encuentre en un estado de enfoque absoluto. 

Les informo que el Ecosistema Operativo ha sido auditado y estabilizado al 100%. A continuación, el resumen de la situación actual de nuestra base de datos:

📊 RESUMEN EJECUTIVO:
--------------------------------------------------
✅ Participantes con C1 Completado: {si_c1}
⏳ Pendientes C1 (Campaña Activa): {pend_c1}
✅ Participantes con C2 Completado: {si_c2}
--------------------------------------------------

🎯 ACCIONES ESTRATÉGICAS - MAÑANA:
Mañana lanzaremos la campaña de "ALTO RENDIMIENTO" vía SMS. 
El mensaje ha sido diseñado con un tono de urgencia y liderazgo para cerrar las brechas de indecisión. 

"El Alto Rendimiento no espera a los que dudan."

🔍 NOVEDADES TÉCNICAS:
- El motor de búsqueda ha sido optimizado para localizarlas a ustedes y a sus invitados instantáneamente.
- Se ha activado la "Caja Negra" para asegurar que cada gestión de ustedes quede grabada en la historia del sistema.

Seguimos en control total del proceso. Vamos por un cierre impecable.

Atentamente,

Ecosistema IA - Torre de Control CPSL
    """
    
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        text = msg.as_string()
        # server.sendmail(EMAIL_USER, DESTINATARIOS, text) # Comentado para no enviar a correos falsos aún
        server.quit()
        print("Reporte generado y listo para envío real.")
        return True
    except Exception as e:
        print(f"Error al enviar reporte: {e}")
        return False

if __name__ == "__main__":
    enviar_reporte()
