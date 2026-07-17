"""
Módulo para simular una respuesta de SMS enviando un correo electrónico a la bandeja de entrada.
Se utiliza para pruebas del sistema de monitoreo.
"""
import smtplib
from email.message import EmailMessage

def simular_respuesta_sms():
    """Envía un correo de prueba que simula un mensaje SMS recibido via Gmail."""
    msg = EmailMessage()
    msg.set_content('Mi nuevo correo es juancarlos_test@gmail.com')
    msg['Subject'] = 'SMS from +51927928029'
    msg['To'] = 'crearpodersinlimitesperu@gmail.com'
    msg['From'] = 'crearpodersinlimitesperu@gmail.com'

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login('crearpodersinlimitesperu@gmail.com', 'bgsl xjus xsmn pzqd')
            s.send_message(msg)
        print("--- EMAIL DE SIMULACION ENVIADO ---")
        print("Asunto: SMS from +51927928029")
        print("Cuerpo: Mi nuevo correo es juancarlos_test@gmail.com")
    except smtplib.SMTPException as e:
        print(f"Error SMTP enviando simulacion: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error inesperado enviando simulacion: {e}")

if __name__ == "__main__":
    simular_respuesta_sms()
