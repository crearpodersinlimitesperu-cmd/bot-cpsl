import smtplib
import os
import pandas as pd
import json
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace(" ", "")

def enviar_fe_de_erratas():
    csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\recipientes_fe_de_erratas.csv'
    if not os.path.exists(csv_path):
        print("No se encontró la lista de recipientes.", flush=True)
        return

    df = pd.read_csv(csv_path)
    df_emails = df.drop_duplicates(subset=['email'])
    
    print(f"--- INICIANDO ENVÍO DE FE DE ERRATAS A {len(df_emails)} EMAILS ---", flush=True)
    
    enviados = 0
    errores = 0
    
    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(GMAIL_USER, GMAIL_PASS)
        
        for _, row in df_emails.iterrows():
            destinatario = row['email']
            
            msg = MIMEMultipart()
            msg["From"] = f"CPSL Lima <{GMAIL_USER}>"
            msg["To"] = destinatario
            msg["Subject"] = "[IMPORTANTE] Fe de Erratas — Rectificación de Información C1 E28"
            
            cuerpo = f"""<html><body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="background: #0f3460; padding: 20px; text-align: center; color: white;">
                <h2>FE DE ERRATAS — CPSL LIMA</h2>
            </div>
            <p>Hola,</p>
            <p>Te escribimos desde <strong>Crear Poder Sin Límites Perú</strong>.</p>
            <p>Recientemente recibiste un correo electrónico respecto a tu participación en el <strong>Capítulo 1 — Equipo 28</strong>. Lamentablemente, debido a un error técnico en nuestro sistema de automatización, parte de la información enviada pudo ser incorrecta.</p>
            <p>Queremos rectificar los siguientes puntos:</p>
            <ul>
                <li><strong>Nombres:</strong> Si el saludo o el asunto no correspondía con tu nombre, te pedimos una sincera disculpa. Tus datos oficiales en nuestra base de datos están seguros.</li>
                <li><strong>Coordinación:</strong> Si el correo mencionaba a una coordinadora anterior (Zuley), te confirmamos que tu coordinadora oficial es <strong>Diana Moscoso</strong> o <strong>Joyce Marín</strong>.</li>
                <li><strong>Asistencia previa:</strong> Si ya completaste el Capítulo 1, por favor ignora el mensaje anterior; estamos actualizando nuestras listas de graduados.</li>
            </ul>
            <p>Agradecemos tu comprensión. Operamos en un nivel de alto rendimiento y este error técnico no refleja el estándar de excelencia que buscamos entregarte en la cancha.</p>
            <p>Atentamente,<br><strong>Equipo de Sistemas CPSL Lima</strong></p>
            <p style="font-size: 11px; color: #888;">Si no deseas recibir más correos, responde con la palabra BAJA.</p>
            </body></html>"""
            
            msg.attach(MIMEText(cuerpo, "html"))
            
            try:
                server.send_message(msg)
                enviados += 1
                print(f"[{enviados}] Enviado a {destinatario}", flush=True)
                time.sleep(3)
            except Exception as e:
                errores += 1
                print(f"Error enviando a {destinatario}: {e}", flush=True)
                if "Daily user sending limit exceeded" in str(e):
                    print("Límite diario de Gmail alcanzado. Abortando.", flush=True)
                    break
        
        server.quit()
    except Exception as e:
        print(f"Error de conexión: {e}", flush=True)
    
    print(f"\n--- FIN DE PROCESO ---", flush=True)
    print(f"Enviados: {enviados} | Errores: {errores}", flush=True)

if __name__ == "__main__":
    enviar_fe_de_erratas()
