import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from database import SessionLocal, Usuario, TrazabilidadPX, ReputacionCanal, LogEnvio
from gatekeeper_enterprise import Gatekeeper
from datetime import datetime

# Configuración
EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_URL = f"https://trigger.macrodroid.com/{MACRODROID_ID}/enviar_sms"

class RitmoHumano:
    def __init__(self, db_session):
        self.db = db_session
        self.gk = Gatekeeper(db_session)

    def actualizar_reputacion(self, canal):
        repo = self.db.query(ReputacionCanal).filter(ReputacionCanal.canal == canal).first()
        if not repo:
            repo = ReputacionCanal(canal=canal, envios_hora=0, envios_dia=0)
            self.db.add(repo)
            self.db.flush() # Sincronizar sin commitear aun
        
        repo.envios_hora = (repo.envios_hora or 0) + 1
        repo.envios_dia = (repo.envios_dia or 0) + 1
        self.db.commit()
        return repo

    def verificar_limites(self, canal):
        repo = self.db.query(ReputacionCanal).filter(ReputacionCanal.canal == canal).first()
        if not repo: return True
        
        if canal == "GMAIL":
            if repo.envios_hora >= 50: return False # Max 50/hora
            if repo.envios_dia >= 300: return False # Max 300/dia
        
        if canal == "SMS_GATEWAY":
            if repo.envios_hora >= 100: return False # Control de gateway
            
        return True

    def enviar_email_blindado(self, px_id, asunto, cuerpo):
        # 1. Gatekeeper Check
        aprobado, motivo = self.gk.check_15_puntos(px_id)
        if not aprobado:
            print(f"   [X] Email bloqueado por Gatekeeper: {motivo}")
            return False

        # 2. Limites Check
        if not self.verificar_limites("GMAIL"):
            print("   [!] Limite de reputacion Gmail alcanzado.")
            return False

        px = self.db.query(Usuario).filter(Usuario.id == px_id).first()
        
        # 3. Envio Real
        msg = MIMEMultipart()
        msg['From'] = f"Crear Poder Sin Límites <{EMAIL_USER}>"
        msg['To'] = px.email
        msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            server.quit()
            
            # Registrar Exito
            self.actualizar_reputacion("GMAIL")
            log = LogEnvio(destino=px.email, tipo="OUT", canal="EMAIL", mensaje=asunto, status_code=200)
            self.db.add(log)
            self.db.commit()
            
            print(f"   [OK] Email enviado a {px.nombre}")
            return True
        except Exception as e:
            print(f"   [ERR] Fallo envio Email: {e}")
            return False

    def enviar_sms_blindado(self, px_id, mensaje):
        # 1. Gatekeeper Check
        aprobado, motivo = self.gk.check_15_puntos(px_id)
        if not aprobado:
            print(f"   [X] SMS bloqueado por Gatekeeper: {motivo}")
            return False

        px = self.db.query(Usuario).filter(Usuario.id == px_id).first()
        
        # 2. Envio Real (MacroDroid)
        try:
            params = {"numero": px.telefono, "mensaje": mensaje}
            r = requests.get(MACRODROID_URL, params=params, timeout=10)
            
            if r.status_code == 200:
                self.actualizar_reputacion("SMS_GATEWAY")
                log = LogEnvio(destino=px.telefono, tipo="OUT", canal="SMS", mensaje=mensaje, status_code=200)
                self.db.add(log)
                self.db.commit()
                print(f"   [OK] SMS enviado a {px.nombre}")
                
                # PAUSA RITMO HUMANO (Aleatoria entre 10 y 30 segundos)
                espera = random.randint(10, 30)
                print(f"      [Zzz] Pausa de {espera}s para simular ritmo humano...")
                time.sleep(espera)
                return True
        except Exception as e:
            print(f"   [ERR] Fallo envio SMS: {e}")
            return False

if __name__ == "__main__":
    db = SessionLocal()
    motor = RitmoHumano(db)
    # Probar con el primer PX
    px = db.query(Usuario).first()
    if px:
        print(f"Iniciando despacho de prueba para {px.nombre}...")
        motor.enviar_email_blindado(px.id, "Test Blindaje", "Este es un mensaje con Ritmo Humano.")
    db.close()
