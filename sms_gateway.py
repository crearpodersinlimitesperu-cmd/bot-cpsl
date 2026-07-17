import os
import logging
import requests
import time
from pathlib import Path
from dotenv import load_dotenv

# Load from .env in current folder
load_dotenv(Path(__file__).parent / ".env")

class SMSGateway:
    """
    Bridge to MacroDroid SMS Gateway.
    Used for urgent notifications and coordinator alerts.
    """
    def __init__(self):
        self.device_id = os.environ.get("MACRODROID_DEVICE_ID")
        self.event_name = os.environ.get("MACRODROID_EVENT_NAME", "enviar_sms")

    def send_sms(self, to_phone, message):
        """Sends an SMS via MacroDroid Trigger."""
        if not self.device_id:
            print(f"[SMS SIMULATION] To {to_phone}: {message}")
            return True

        # Normalize phone
        clean_phone = "".join(filter(str.isdigit, str(to_phone)))[-9:]
        
        url = f"https://trigger.macrodroid.com/{self.device_id}/{self.event_name}"
        params = {'numero': clean_phone, 'mensaje': message}

        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print(f"[SMS OK] Triggered for {clean_phone}")
                return True
            else:
                print(f"[SMS ERR] Status {r.status_code}")
                return False
        except Exception as e:
            print(f"[SMS ERR] {e}")
            return False

if __name__ == "__main__":
    gw = SMSGateway()
    gw.send_sms("999000111", "CREAR GLOBAL: Test de Infraestructura SMS")
