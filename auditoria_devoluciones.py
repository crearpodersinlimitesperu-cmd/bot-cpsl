import imaplib
import email
from email.header import decode_header
import os, sys

# Configurar salida para evitar errores de encoding en Windows
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def analizar_devoluciones_detallado():
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        # Keywords extendidos
        keywords = ["devolucion", "reembolso", "dinero", "fondos", "cancelar", "desistir", "incumplimiento", "estafa", "denuncia"]
        casos = []

        for kw in keywords:
            # Buscamos en los últimos 6 meses (aprox) para no saturar, o buscamos todo si es necesario
            status, messages = mail.search(None, f'(OR SUBJECT "{kw}" BODY "{kw}")')
            if status == "OK":
                for num in messages[0].split():
                    status, data = mail.fetch(num, "(RFC822)")
                    if status == "OK":
                        raw_email = data[0][1]
                        msg = email.message_from_bytes(raw_email)
                        
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")
                        
                        from_ = msg["From"]
                        date = msg["Date"]
                        
                        # Extraer cuerpo para buscar contexto de IMOs
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body = part.get_payload(decode=True).decode(errors='replace')
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode(errors='replace')

                        # Identificar si menciona a un IMO o es un PX
                        tipo = "PX"
                        if "IMO" in body.upper() or "GRADUADO" in body.upper():
                            tipo = "IMO/Aliado"

                        casos.append({
                            "fecha": date,
                            "desde": from_,
                            "asunto": subject,
                            "tipo": tipo,
                            "kw": kw,
                            "extracto": body[:200].replace("\n", " ")
                        })

        mail.logout()
        # Eliminar duplicados por ID de mensaje o asunto+fecha
        casos_unicos = []
        vistos = set()
        for c in casos:
            key = (c['asunto'], c['desde'])
            if key not in vistos:
                casos_unicos.append(c)
                vistos.add(key)
        
        return casos_unicos
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    print("--- INICIANDO AUDITORÍA DE DEVOLUCIONES CPSL ---")
    resultados = analizar_devoluciones_detallado()
    
    if isinstance(resultados, str):
        print(resultados)
    elif not resultados:
        print("No se detectaron solicitudes de devolución.")
    else:
        print(f"Se encontraron {len(resultados)} casos potenciales.\n")
        # Ordenar por fecha (simplificado)
        for i, c in enumerate(resultados, 1):
            print(f"{i}. [{c['fecha']}] | {c['tipo']}")
            print(f"   De: {c['desde']}")
            print(f"   Asunto: {c['asunto']}")
            print(f"   Contexto: {c['extracto']}...")
            print("-" * 50)
