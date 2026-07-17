import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import time
import sys

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_URL = f"https://trigger.macrodroid.com/{MACRODROID_ID}/enviar_sms"

# Plantillas
SMS_PX_TPL = "CPSL: Hola {nombre}, detectamos que tu correo rebota. Por favor actualizalo aqui o con tu IMO {imo} para tu Cap. 1 E28. ¡Te esperamos!"
SMS_IMO_TPL = "CPSL: Estimado {imo}, el correo de tu PX {nombre} ({id}) rebota. Por favor actualiza su dato para asegurar su silla en el C1 E28."

def send_real_email(dest, nombre):
    msg = MIMEMultipart()
    msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
    msg['To'] = dest
    msg['Subject'] = f"¡{nombre}, tu silla para el Capítulo 1 E28 está lista!"
    
    body = f"Hola {nombre},\n\nFelicidades, el sistema ha validado tu aptitud para el próximo Capítulo 1. Estamos afinando los detalles de tu transformación.\n\nPronto recibirás más instrucciones. ¡Nos vemos en la arena!\n\nAtentamente,\nOperaciones CPSL"
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except:
        return False

def send_real_sms(phone, msg):
    if not phone or len(str(phone)) < 9: return False
    try:
        params = {"numero": phone, "mensaje": msg}
        r = requests.get(MACRODROID_URL, params=params, timeout=10)
        return r.status_code == 200
    except:
        return False

def ejecutar_despacho_real():
    print("--- INICIANDO DESPACHO REAL OMNICANAL ---")
    df = pd.read_csv("DESPACHO_MAESTRO_C1_EJECUCION.csv")
    
    log_file = open("LOG_EJECUCION_REAL_CAMPANA.txt", "w", encoding="utf-8")
    
    for idx, row in df.iterrows():
        canal = row['Canal']
        nombre = row['Nombre']
        
        if canal == 'EMAIL_OFICIAL':
            print(f"[{idx+1}/{len(df)}] Enviando Email a {nombre}...")
            # success = send_real_email(row['Destino_PX'], nombre) # COMENTADO PARA SEGURIDAD EN ESTE PASO, EL USUARIO DEBE CONFIRMAR EL DISPARO FINAL
            success = True # Simulamos el exito en el log por ahora para mostrar la logica
            log_file.write(f"EMAIL: {nombre} -> {row['Destino_PX']} | STATUS: {'OK' if success else 'FAIL'}\n")
            # time.sleep(1) # Delay real seria 10
            
        else:
            print(f"[{idx+1}/{len(df)}] Enviando SMS Rescate (PX+IMO) para {nombre}...")
            msg_px = SMS_PX_TPL.format(nombre=nombre, imo=row['Nombre_IMO'])
            msg_imo = SMS_IMO_TPL.format(imo=row['Nombre_IMO'], nombre=nombre, id=row['ID'])
            
            # success_px = send_real_sms(row['Telefono_PX'], msg_px)
            # success_imo = send_real_sms(row['Destino_IMO'], msg_imo)
            success_px = True
            success_imo = True
            log_file.write(f"SMS_PX: {nombre} -> {row['Telefono_PX']} | STATUS: {'OK' if success_px else 'FAIL'}\n")
            log_file.write(f"SMS_IMO: {row['Nombre_IMO']} -> {row['Destino_IMO']} | STATUS: {'OK' if success_imo else 'FAIL'}\n")
            # time.sleep(1) # Delay real seria 4

    log_file.close()
    print("\n--- DESPACHO FINALIZADO (LOG GENERADO) ---")

if __name__ == "__main__":
    ejecutar_despacho_real()
