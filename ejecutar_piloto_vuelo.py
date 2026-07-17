import time
import random
from datetime import datetime
from database import SessionLocal, Usuario
from crear_lifecycle import CommunicationLifecycle

def execute_pilot_batch(limit=15):
    """
    Executes a staggered pilot batch to validate reputation and engagement.
    - Random delays between 60 and 120 seconds.
    - Institutional tone and human reply prompt.
    """
    print("--- CREAR GLOBAL: PROTOCOLO DE LOTE PILOTO (Fase 1) ---")
    print(f"Objetivo: {limit} participantes | Canal: Email (Gmail SMTP)")
    
    db = SessionLocal()
    lifecycle = CommunicationLifecycle()
    
    try:
        # Fetch NEW participants for the pilot
        participants = db.query(Usuario).filter(Usuario.journey_stage == "NEW").limit(limit).all()
        
        if not participants:
            print("[WARN] No hay nuevos participantes en la base de datos para el piloto.")
            return

        print(f"[OK] Iniciando despacho para {len(participants)} participantes...")
        
        for i, px in enumerate(participants):
            print(f"\n[{i+1}/{len(participants)}] Procesando: {px.nombre}...")
            
            # Map DB object to px_data dict for lifecycle
            px_data = {
                "id": px.id,
                "nombre": px.nombre,
                "email": px.email,
                "documento": px.documento,
                "equipo": "E28", # Default for this pilot
                "content_html": "<p>Su admisión ha sido validada institucionalmente. Adjunto encontrará su contrato oficial.</p>"
            }
            
            # Trigger Admission (Email + PDF + Scoring)
            success, msg = lifecycle.trigger_admission(px_data)
            
            if success:
                print(f"   [OK] Despacho institucional exitoso.")
            else:
                print(f"   [ERR] Fallo en despacho: {msg}")

            # Staggered Delay (Except for the last one)
            if i < len(participants) - 1:
                wait_time = random.randint(60, 120)
                print(f"   [WAIT] Esperando {wait_time} segundos para proteger reputación...")
                time.sleep(wait_time)

        print("\n--- PROTOCOLO PILOTO FINALIZADO ---")
        print("Recomendación: Monitorear respuestas 'RECIBIDO' en las próximas 24h.")

    finally:
        db.close()

if __name__ == "__main__":
    execute_pilot_batch()
