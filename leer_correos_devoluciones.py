import imaplib
import email
from email.header import decode_header
import os
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def registrar_log(categoria, evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def extract_phone(text):
    """Extrae teléfonos de 9 dígitos del texto."""
    matches = re.findall(r'9\d{8}', str(text))
    return matches[0] if matches else None

def procesar_correos():
    print("--- INICIANDO ESCANEO MAESTRO DE CORREOS ---")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Buscar correos de las últimas 72 horas (ampliado para auditoría total)
        status, messages = mail.search(None, 'ALL')
        if status != "OK": return "Error en búsqueda"

        email_ids = messages[0].split()
        # Ampliamos a los últimos 200 correos para no perder rebotes antiguos
        email_ids = email_ids[-200:]

        updates_confirm = 0
        updates_bounce = 0
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        for e_id in reversed(email_ids):
            status, data = mail.fetch(e_id, "(RFC822)")
            if status != "OK": continue
            
            msg = email.message_from_bytes(data[0][1])
            from_ = str(msg.get("From", "")).lower()
            subject = str(msg.get("Subject", "")).lower()
            
            # Obtener cuerpo del mensaje
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')

            # 1. DETECTAR REBOTES (Mailer Daemon)
            if "mailer-daemon" in from_ or "failure" in subject:
                tel = extract_phone(body)
                if tel:
                    cursor.execute("UPDATE participantes SET resultado_gestion = 'REBOTE_MAIL', es_pendiente_real = 'SI' WHERE telefono = ?", (tel,))
                    if cursor.rowcount > 0: updates_bounce += 1
                continue

            # 2. DETECTAR CONFIRMACIONES / PAGOS
            keywords_pago = ["pago", "voucher", "transferencia", "confirmado", "ya deposité"]
            if any(kw in body.lower() or kw in subject for kw in keywords_pago):
                tel = extract_phone(body)
                # Intentar buscar por correo si no hay teléfono en el cuerpo
                mail_sender = re.findall(r'[\w\.-]+@[\w\.-]+', from_)
                sender_addr = mail_sender[0] if mail_sender else ""
                
                if tel:
                    cursor.execute("UPDATE participantes SET c2 = 'SI', es_pendiente_real = 'NO', resultado_gestion = 'PAGO_CONFIRMADO_MAIL' WHERE telefono = ?", (tel,))
                elif sender_addr:
                    cursor.execute("UPDATE participantes SET c2 = 'SI', es_pendiente_real = 'NO', resultado_gestion = 'PAGO_CONFIRMADO_MAIL' WHERE email = ?", (sender_addr,))
                
                if cursor.rowcount > 0: updates_confirm += 1

        conn.commit()
        conn.close()
        mail.logout()

        res = f"Proceso finalizado. Confirmados: {updates_confirm}. Rebotes detectados: {updates_bounce}."
        print(res)
        registrar_log("EMAIL_SYNC", "PROCESAR_CORREOS", res)
        return res

    except Exception as e:
        err = f"Error crítico en Email Sync: {e}"
        print(err)
        registrar_log("EMAIL_SYNC", "ERROR", err, "FALLO")
        return err

if __name__ == "__main__":
    procesar_correos()
