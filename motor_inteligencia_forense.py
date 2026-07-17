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

def inicializar_db_patrones():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS historial_interacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            fecha TEXT,
            tipo_interaccion TEXT, -- REBOTE, RECHAZO, CONFIRMACION, PREGUNTA, DEVOLUCION
            contenido_clave TEXT,
            fuente TEXT
        )
    """)
    conn.commit()
    conn.close()

def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+', str(text))
    return match.group(0).lower() if match else None

def auditoria_forense_masiva(meses=24):
    print(f"--- INICIANDO AUDITORIA FORENSE MASIVA ({meses} MESES) ---")
    inicializar_db_patrones()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("[Gmail]/Todos")
        
        # Calcular fecha de inicio
        date_cutoff = (datetime.now() - timedelta(days=meses*30)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'SINCE "{date_cutoff}"')
        
        if status != "OK": return
        
        ids = messages[0].split()
        total_ids = len(ids)
        print(f"Total correos detectados en el periodo: {total_ids}")
        
        conn = sqlite3.connect(DB_PATH)
        conn.execute("PRAGMA journal_mode=WAL")
        c = conn.cursor()
        
        registros = 0
        procesados = 0
        # Procesar en bloques de 100 para eficiencia
        for i in reversed(ids):
            procesados += 1
            if procesados % 100 == 0:
                print(f"Procesando correo {procesados} de {total_ids}...")
                
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
            
            subject = str(msg.get("Subject", "")).upper()
            from_ = str(msg.get("From", "")).lower()
            date_str = str(msg.get("Date", ""))
            
            # CLASIFICACION POR PATRONES
            tipo = "OTRO"
            if "FAILURE" in subject or "MAILER-DAEMON" in from_:
                tipo = "REBOTE"
            elif any(kw in body.upper() for kw in ["NO INTERESA", "NO LLAMAR", "DE BAJA", "RETIRENME"]):
                tipo = "RECHAZO"
            elif any(kw in body.upper() for kw in ["VOUCHER", "PAGO", "DEPOSITO", "CONFIRMO"]):
                tipo = "CONFIRMACION"
            elif any(kw in body.upper() for kw in ["DEVOLUCION", "REEMBOLSO", "MI DINERO"]):
                tipo = "SOLICITUD_DEVOLUCION"

            if tipo != "OTRO":
                target_email = extract_email(body) if tipo == "REBOTE" else extract_email(from_)
                
                if target_email:
                    print(f"   [!] Patron detectado: {tipo} para {target_email}")
                    c.execute("""
                        INSERT INTO historial_interacciones (email, fecha, tipo_interaccion, contenido_clave, fuente)
                        VALUES (?, ?, ?, ?, ?)
                    """, (target_email, date_str, tipo, body[:200], "GMAIL_FORENSIC"))
                    registros += 1
            
            if procesados % 10 == 0:
                conn.commit()
                # print(f"Auditados {registros} patrones relevantes...")

        conn.commit()
        conn.close()
        mail.logout()
        print(f"Auditoria finalizada. Patrones maestros capturados: {registros}")
        
    except Exception as e:
        print(f"Error en auditoria: {e}")

if __name__ == "__main__":
    auditoria_forense_masiva(24)
