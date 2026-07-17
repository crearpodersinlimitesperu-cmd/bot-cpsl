"""
Módulo para el monitoreo cada 4 horas de la bandeja de entrada de Gmail.
Escanea rebotes de correos y respuestas de SMS.
"""
import email
import imaplib
import json
import re
import sqlite3
import time
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

import pandas as pd
import requests

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"
CONFIG_PATH = BASE_DIR / "config_scanner.json"

def registrar_log(categoria, evento, detalle, estado="OK"):
    """Registra un evento en la base de datos de logs."""
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def decodificar_header(h):
    """Decodifica los encabezados de los correos electrónicos."""
    if not h:
        return ""
    decoded = decode_header(h)
    parts = []
    for text, encoding in decoded:
        if isinstance(text, bytes):
            parts.append(text.decode(encoding if encoding else 'utf-8', errors='ignore'))
        else:
            parts.append(str(text))
    return "".join(parts)

def procesar_respuesta_px(telefono, texto, config):
    """Procesa el texto de una respuesta de un participante y actualiza su estado."""
    intent = "NO_REPLY"
    if any(k in texto.lower() for k in config['regex_patterns']['confirmacion'].split('|')):
        intent = "CONFIRMED"
    elif any(k in texto.lower() for k in config['regex_patterns']['baja'].split('|')):
        intent = "OPT_OUT"

    new_email = None
    email_match = re.search(config['regex_patterns']['email'], texto)
    if email_match:
        new_email = email_match.group(0).lower()
        intent = "RECEIVED_EMAIL"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Limpiar telefono (ultimos 9 digitos)
    clean_tel = "".join(filter(str.isdigit, telefono))[-9:]

    update_fields = ["estado_respuesta_sms = ?", "fecha_ultima_interaccion = ?", "observaciones = ?"]
    params = [intent, datetime.now().isoformat(), texto[:250]]

    if new_email:
        update_fields.append("email = ?")
        params.append(new_email)

    params.append(f"%{clean_tel}")
    params.append(f"%{clean_tel}")

    query = f"UPDATE participantes SET {', '.join(update_fields)} WHERE telefono LIKE ? OR tel_imo LIKE ?"
    cursor.execute(query, params)
    rows = cursor.rowcount
    conn.commit()
    conn.close()

    if rows > 0:
        registrar_log('SMS_SYNC', 'SUCCESS', f"Tel: {clean_tel} | Intent: {intent} | Email: {new_email}")
    return rows

def escanear_bounces_profundo_v2(mail, config):
    """Escanea la carpeta '[Gmail]/Todos' buscando correos de rebote."""
    print("--- 1. ESCANEANDO BOUNCES (TODOS) ---")
    target_folder = '"[Gmail]/Todos"'
    status, _ = mail.select(target_folder, readonly=True)
    if status != "OK":
        mail.select("INBOX", readonly=True)

    since_date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE {since_date})')

    if status != "OK" or not messages[0]:
        return 0

    email_ids = messages[0].split()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    bounce_count = 0

    for e_id in email_ids[::-1][:50]: # Buffer de 50
        _, data = mail.fetch(e_id, "(RFC822)")
        for response_part in data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                asunto = decodificar_header(msg.get("Subject")).lower()
                if any(x in asunto for x in ['undelivered', 'failure', 'bounce', 'reboto']):
                    cuerpo = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    cuerpo += part.get_payload(decode=True).decode('utf-8', errors='ignore')
                                except Exception:  # pylint: disable=broad-exception-caught
                                    pass
                    else:
                        try:
                            cuerpo = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except Exception:  # pylint: disable=broad-exception-caught
                            pass

                    match = re.search(config['regex_patterns']['email'], cuerpo)
                    if match:
                        failed = match.group(0).lower()
                        if failed != config['email_config']['email_user'].lower():
                            cursor.execute(
                                "UPDATE participantes SET email='REBOTE', estado_respuesta_sms='EMAIL_BOUNCED' WHERE email = ?",
                                (failed,)
                            )
                            if cursor.rowcount > 0:
                                bounce_count += cursor.rowcount
                                registrar_log('BOUNCE_DEEP', 'SUCCESS', f"Rebote: {failed}")
    conn.commit()
    conn.close()
    return bounce_count

def escanear_respuestas_sms_real(mail, config):
    """Escanea la bandeja de entrada buscando correos que representen mensajes SMS recibidos."""
    print("--- 2. ESCANEANDO RESPUESTAS SMS (INBOX) ---")
    mail.select("INBOX")
    since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
    status, messages = mail.search(None, f'(SINCE {since_date} SUBJECT "SMS from")')

    if status != "OK" or not messages[0]:
        return 0

    processed = 0
    email_ids = messages[0].split()
    for e_id in email_ids:
        _, data = mail.fetch(e_id, "(RFC822)")
        for part in data:
            if isinstance(part, tuple):
                msg = email.message_from_bytes(part[1])
                asunto = decodificar_header(msg.get("Subject"))
                match = re.search(r"(\+?\d{9,13})", asunto)
                if match:
                    tel = match.group(1)
                    cuerpo = ""
                    if msg.is_multipart():
                        for p in msg.walk():
                            if p.get_content_type() == "text/plain":
                                try:
                                    cuerpo += p.get_payload(decode=True).decode('utf-8', errors='ignore')
                                except Exception:  # pylint: disable=broad-exception-caught
                                    pass
                    else:
                        try:
                            cuerpo = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                        except Exception:  # pylint: disable=broad-exception-caught
                            pass

                    texto = cuerpo.strip().split('\n')[0][:250]
                    if procesar_respuesta_px(tel, texto, config) > 0:
                        processed += 1
        mail.store(e_id, '+FLAGS', '\\Seen')
    return processed

def ejecutar_ciclo_real():
    """Ejecuta un ciclo completo de escaneo de rebotes y respuestas SMS."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    try:
        mail = imaplib.IMAP4_SSL(config['email_config']['imap_server'])
        mail.login(config['email_config']['email_user'], config['email_config']['email_pass'])
        bounces = escanear_bounces_profundo_v2(mail, config)
        respuestas = escanear_respuestas_sms_real(mail, config)
        mail.logout()
        print(f"Ciclo completado. Rebotes: {bounces}, SMS: {respuestas}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error: {e}")
        registrar_log('CICLO_4H', 'ERROR', str(e), 'FALLIDO')

if __name__ == "__main__":
    ejecutar_ciclo_real()
