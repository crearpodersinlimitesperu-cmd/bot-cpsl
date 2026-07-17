import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime, timedelta
import sys
import pandas as pd
import os

# Configurar salida
sys.stdout.reconfigure(encoding='utf-8')

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def get_bounces_last_12_months():
    print("--- INICIANDO ESCANEO DE REBOTES (ÚLTIMOS 12 MESES) ---")
    
    date_12_months_ago = (datetime.now() - timedelta(days=365)).strftime("%d-%b-%Y")
    bounced_emails = set()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('"[Gmail]/Todos"')
        
        # Búsqueda desde hace 12 meses de "mailer-daemon" o "postmaster"
        search_query = f'(SINCE "{date_12_months_ago}" OR FROM "mailer-daemon@googlemail.com" FROM "postmaster")'
        print(f"Query: {search_query}")
        
        status, messages = mail.search(None, search_query)
        if status == "OK":
            ids = messages[0].split()
            print(f"Encontrados {len(ids)} mensajes potenciales de rebote.")
            
            procesados = 0
            for i in reversed(ids):
                procesados += 1
                if procesados % 100 == 0: 
                    print(f"Procesando {procesados} de {len(ids)}...")
                
                status, data = mail.fetch(i, "(RFC822)")
                if status != "OK": continue
                
                msg = email.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                            break
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                
                # Extract the failing email
                failed_email = extract_email(body)
                if not failed_email:
                    failed_email = extract_email(str(msg.get("Subject")))

                if failed_email and failed_email.lower() != EMAIL_USER.lower():
                    bounced_emails.add(failed_email.lower())
            
            print("--- ESCANEO FINALIZADO ---")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")
        
    return list(bounced_emails)

def update_final_list(bounced_list):
    aptos_path = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana_Final.csv"
    if not os.path.exists(aptos_path):
        print(f"Error: {aptos_path} not found.")
        return
        
    df = pd.read_csv(aptos_path, encoding='utf-8-sig')
    initial_len = len(df)
    
    # Filter out new bounces
    bounces_set = set(bounced_list)
    df['Correo_Norm'] = df['Correo'].astype(str).str.lower().str.strip()
    
    df_clean = df[~df['Correo_Norm'].isin(bounces_set)].copy()
    df_clean = df_clean.drop(columns=['Correo_Norm'])
    
    new_bounces_found = initial_len - len(df_clean)
    print(f"\n--- ACTUALIZACIÓN DE LISTA FINAL ---")
    print(f"Total en lista antes: {initial_len}")
    print(f"Rebotes de 12 meses aplicados. Eliminados adicionales: {new_bounces_found}")
    print(f"Total lista final definitiva: {len(df_clean)}")
    
    df_clean.to_csv(aptos_path, index=False, encoding='utf-8-sig')
    print("Archivo actualizado con éxito.")

if __name__ == "__main__":
    bounces = get_bounces_last_12_months()
    print(f"\nTotal correos rebotados únicos extraídos: {len(bounces)}")
    
    if bounces:
        # Save bounces
        bounces_df = pd.DataFrame({'Email': bounces})
        bounces_df.to_csv(r"c:\Users\josem\Downloads\Rebotes_12_Meses.csv", index=False)
        update_final_list(bounces)

