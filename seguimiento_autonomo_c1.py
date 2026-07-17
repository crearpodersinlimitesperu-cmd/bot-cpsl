import imaplib
import email
import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path

# CONFIGURACION
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
APTOS_FILE = Path("PX_LISTOS_PARA_CONTACTO_FINAL.csv")

def detectar_y_actuar_rebotes():
    print(f"--- INICIANDO SEGUIMIENTO AUTONOMO REBOTES: {datetime.now().strftime('%H:%M')} ---")
    
    if not APTOS_FILE.exists():
        print("No hay lista de aptos para procesar.")
        return

    df_aptos = pd.read_csv(APTOS_FILE)
    emails_watch = set(df_aptos['Correo'].dropna().astype(str).str.lower().tolist())
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar fallos de entrega
        status, messages = mail.search(None, '(OR SUBJECT "Failure" SUBJECT "Delivery Status Notification")')
        if status != "OK": return
        
        rebotes_detectados = []
        
        for e_id in messages[0].split()[-50:]: # Revisar los ultimos 50 rebotes
            status, data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
            
            # Buscar si el email fallido es uno de los nuestros
            for target_mail in emails_watch:
                if target_mail in body.lower():
                    # ¡REBOTE DETECTADO!
                    px_info = df_aptos[df_aptos['Correo'].str.lower() == target_mail].iloc[0]
                    rebotes_detectados.append(px_info)
                    break
        
        if rebotes_detectados:
            print(f"Se detectaron {len(rebotes_detectados)} rebotes criticos.")
            for px in rebotes_detectados:
                # PROTOCOLO SMS (Simulado por ahora para aprobacion o ejecucion directa)
                msg_px = f"HOLA {px['NombreCompleto']}, TU CORREO {px['Correo']} REBOTO. POR FAVOR RESPONDE ESTE SMS CON TU CORREO ACTUALIZADO PARA C1."
                msg_imo = f"HOLA {px['Nombre IMO']}, EL CORREO DEL PX {px['NombreCompleto']} REBOTO. POR FAVOR AYUDANOS A ACTUALIZARLO."
                
                print(f"[SMS ENVIADO A PX {px['TelefonoMovil']}]: {msg_px}")
                print(f"[SMS ENVIADO A IMO {px['Tel. IMO']}]: {msg_imo}")
                
                # Aqui se llamaria al Gateway de SMS
        else:
            print("No se detectaron rebotes para la lista de Diana/Joyce en los ultimos correos.")
            
        mail.logout()
    except Exception as e:
        print(f"Error en seguimiento autonomo: {e}")

if __name__ == "__main__":
    detectar_y_actuar_rebotes()
