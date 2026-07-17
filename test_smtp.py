import smtplib
import os
from dotenv import load_dotenv

load_dotenv(r'C:\Users\josem\Downloads\bot-cpsl-review\.env')
user = "crearpodersinlimitesperu@gmail.com"
password = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace(" ", "")

print(f"Intentando login para {user}...")
try:
    server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10)
    server.login(user, password)
    print("Login exitoso!")
    server.quit()
except Exception as e:
    print(f"Error: {e}")
