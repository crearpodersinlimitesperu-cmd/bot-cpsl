import imaplib
import email
from email.header import decode_header
import sqlite3
import re
from datetime import datetime, timedelta
from pathlib import Path

# CONFIGURACION
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\patrones_forenses_v2.db")

def inicializar_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS historial_interacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            fecha TEXT,
            tipo_interaccion TEXT,
            contenido_clave TEXT,
            fuente TEXT
        )
    """)
    conn.commit()
    conn.close()

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_relampago():
    print("--- INICIANDO AUDITORIA RELAMPAGO (ULTIMOS 2 AÑOS) ---")
    inicializar_db()
    
    date_cutoff = (datetime.now() - timedelta(days=24*30)).strftime("%d-%b-%Y")
    queries = {
        "REBOTE": f'(SINCE {date_cutoff} OR SUBJECT "Failure" SUBJECT "Delivery Status Notification")',
        "RECHAZO": f'(SINCE {date_cutoff} OR BODY "no interesa" BODY "devolucion")',
        "CONFIRMACION": f'(SINCE {date_cutoff} OR BODY "voucher" BODY "pago")'
    }

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        for tipo, query in queries.items():
            print(f"Buscando patrones de {tipo}...")
            status, messages = mail.search(None, query)
            if status != "OK": continue
            
            ids = messages[0].split()
            print(f"   Encontrados {len(ids)} correos potenciales.")
            
            for i in ids: # Procesar TODOS los encontrados
                status, data = mail.fetch(i, "(RFC822)")
                if status != "OK": continue
                
                msg = email.message_from_bytes(data[0][1])
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            body = part.get_payload(decode=True).decode(errors='ignore')
                else:
                    body = msg.get_payload(decode=True).decode(errors='ignore')
                
                from_ = str(msg.get("From", "")).lower()
                target_email = extract_email(body) if tipo == "REBOTE" else extract_email(from_)
                
                if target_email:
                    c.execute("""
                        INSERT INTO historial_interacciones (email, fecha, tipo_interaccion, contenido_clave, fuente)
                        VALUES (?, ?, ?, ?, ?)
                    """, (target_email, str(msg.get("Date")), tipo, body[:150], "GMAIL_FAST_SCAN"))
            
            conn.commit()
            print(f"   [OK] {tipo} procesado.")

        conn.close()
        mail.logout()
        print("--- AUDITORIA RELAMPAGO FINALIZADA ---")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    auditoria_relampago()
