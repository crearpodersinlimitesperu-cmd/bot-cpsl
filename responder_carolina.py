import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
DESTINO = "carolinamh_28@hotmail.com"

def enviar_respuesta_carolina():
    print(f"--- ENVIANDO RESPUESTA ASERTIVA A CAROLINA MANRIQUE ---")
    
    msg = MIMEMultipart()
    msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
    msg['To'] = DESTINO
    msg['Subject'] = "Sincronización Exitosa: Red Carolina Manrique - Capítulo 1 E28"

    cuerpo = """
Estimada Carolina,

Es un gusto saludarte.

Recibimos tu reporte y quiero felicitarte por la precisión en el seguimiento de tu red. Hemos procedido a realizar una auditoría forense inmediata en nuestro sistema Torre de Control y, efectivamente, Oscar Leiva y Erika Anticona ya figuran como graduados validados de los Equipos 26 y 27. 

Gracias a tu proactividad, hemos blindado sus registros para que no reciban comunicaciones redundantes, manteniendo los estándares de profesionalismo y respeto que nos caracterizan como organización.

Respecto a los otros 2 participantes de tu red (Miguel Angel Mucha y Mikhail Dávila), nuestro sistema confirma que son participantes APTOS y LISTOS para vivir su Capítulo 1. Confiamos plenamente en tu liderazgo para concretar su asistencia en este próximo equipo. Ellos tienen en sus manos la oportunidad de transformar su realidad, y tú eres el puente clave para asegurar que ese resultado ocurra.

Seguimos trabajando en equipo, con data veraz y enfoque total en la excelencia.

Atentamente,

Gerencia de Operaciones
Crear Poder Sin Límites Perú
"""
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"   [OK] Correo enviado exitosamente a: {DESTINO}")
    except Exception as e:
        print(f"   [ERROR] No se pudo enviar el correo: {e}")

if __name__ == "__main__":
    enviar_respuesta_carolina()
