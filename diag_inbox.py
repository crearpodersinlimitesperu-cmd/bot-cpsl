"""
Módulo de diagnóstico para visualizar los últimos correos recibidos en la bandeja de entrada.
Ayuda a verificar que la conexión IMAP sea correcta y a ver los asuntos de los correos.
"""
import email
import imaplib
from email.header import decode_header

def diagnosticar_inbox():
    """Conecta a Gmail y muestra el asunto de los últimos 5 correos."""
    try:
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login('crearpodersinlimitesperu@gmail.com', 'bgsl xjus xsmn pzqd')
        mail.select('inbox')

        print("--- ULTIMOS 5 CORREOS EN INBOX ---")
        _, messages = mail.search(None, 'ALL')
        ids = messages[0].split()[-5:]

        for e_id in ids:
            _, data = mail.fetch(e_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            asunto = msg.get("Subject")
            # Decodificar
            decoded = decode_header(asunto)
            final_subject = ""
            for text, encoding in decoded:
                if isinstance(text, bytes):
                    final_subject += text.decode(encoding if encoding else 'utf-8', errors='ignore')
                else:
                    final_subject += str(text)
            print(f"ID: {e_id.decode()} | Asunto: {final_subject}")

        mail.logout()
    except imaplib.IMAP4.error as e:
        print(f"Error de IMAP: {e}")
    except Exception as e:  # pylint: disable=broad-exception-caught
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    diagnosticar_inbox()
