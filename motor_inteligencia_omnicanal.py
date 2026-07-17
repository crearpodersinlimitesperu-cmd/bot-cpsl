import imaplib
import email
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configurar salida
sys.stdout.reconfigure(encoding='utf-8')

# CONFIGURACION
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
OUTPUT_CSV = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\PATRONES_MAESTROS_2AÑOS.csv")

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_omnicanal_sonica():
    print("--- INICIANDO AUDITORIA OMNICANAL SONICA (2 AÑOS) ---")
    
    queries = {
        "REBOTE": 'FROM "mailer-daemon@googlemail.com"',
        "RECHAZO": '(OR BODY "no interesa" BODY "devolucion")',
        "CONFIRMACION": '(OR BODY "voucher" BODY "pago")'
    }

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        with open(OUTPUT_CSV, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Email', 'Fecha', 'Tipo', 'Muestra'])
            
            for tipo, query in queries.items():
                print(f"Buscando patrones de {tipo}...")
                status, messages = mail.search(None, query)
                if status != "OK": continue
                
                ids = messages[0].split()
                print(f"   Encontrados {len(ids)} correos potenciales.")
                
                procesados = 0
                for i in reversed(ids):
                    procesados += 1
                    if procesados % 100 == 0: 
                        print(f"   Procesando {procesados} de {len(ids)}...")
                        f.flush()
                    
                    status, data = mail.fetch(i, "(BODY[TEXT] INTERNALDATE)")
                    if status != "OK" or not data: continue
                    
                    body = data[0][1].decode(errors='ignore')
                    date_match = re.search(r'\d{2}-\w{3}-\d{4}', str(data[1]))
                    fecha = date_match.group(0) if date_match else "Unknown"

                    target_email = extract_email(body) if tipo == "REBOTE" else extract_email(body) # En rechazo/conf el email suele estar en el cuerpo o firma
                    if not target_email and tipo != "REBOTE":
                        # Si no hay email en el cuerpo, no podemos vincularlo facilmente sin el RFC822 completo (header)
                        # Pero podemos intentar buscar el remitente en un segundo fetch ligero
                        pass

                    if target_email and target_email.lower() != EMAIL_USER.lower():
                        writer.writerow([target_email, fecha, tipo, body[:100].strip().replace('\n', ' ')])
            
            print(f"--- AUDITORIA OMNICANAL FINALIZADA: {OUTPUT_CSV} ---")

        mail.logout()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    auditoria_omnicanal_sonica()
