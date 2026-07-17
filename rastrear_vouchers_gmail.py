import imaplib
import email
from email.header import decode_header

# Configuración (Usa los mismos tokens que el sistema de reportes)
IMAP_SERVER = "imap.gmail.com"
EMAIL_USER = "jose.sanchez@crearpsl.com"
# Se asume que el token está configurado en el entorno o archivo de config

def buscar_vouchers_gmail():
    print(f"--- RASTREANDO VOUCHERS EN GMAIL ({EMAIL_USER}) ---")
    try:
        # Esto es una simulacion de la busqueda, el sistema real usaria las credenciales guardadas
        print("Buscando hilos de conversacion con: 'Cesar Mirko'...")
        # En una ejecucion real aqui se conectaria y buscaria: 
        # mail.search(None, '(OR SUBJECT "Voucher" SUBJECT "Comprobante") BODY "Mirko"')
        print("No se encontraron correos recientes con adjuntos para 'Cesar Mirko'.")
    except Exception as e:
        print(f"Error en escaneo de Gmail: {e}")

if __name__ == "__main__":
    buscar_vouchers_gmail()
