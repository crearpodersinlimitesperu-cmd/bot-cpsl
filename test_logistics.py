from database import SessionLocal, Entrenador, VueloLogistica
from crear_logistics_engine import LogisticsEngine
from datetime import datetime, timedelta
import random

def test_logistics_flight_tracking():
    print("--- CREAR GLOBAL: LOGISTICS CLOUD SIMULATION ---")
    db = SessionLocal()
    
    try:
        # 1. Create a Trainer
        entrenador = db.query(Entrenador).filter(Entrenador.email == "trainer@crearglobal.com").first()
        if not entrenador:
            entrenador = Entrenador(
                nombre="ALEJANDRO ENTRENADOR",
                email="trainer@crearglobal.com",
                telefono="999555111",
                rol="TRAINER"
            )
            db.add(entrenador)
            db.commit()
            db.refresh(entrenador)
            print("[OK] Entrenador creado.")

        # 2. Schedule a Flight
        ahora = datetime.utcnow()
        vuelo = VueloLogistica(
            entrenador_id=entrenador.id,
            codigo_vuelo=f"LA{random.randint(1000,9999)}",
            aerolinea="LATAM Airlines",
            origen="BOG (Bogotá)",
            destino="LIM (Lima)",
            fecha_hora_salida_prog=ahora + timedelta(hours=24),
            fecha_hora_llegada_prog=ahora + timedelta(hours=27),
            estado="PROGRAMADO",
            terminal_puerta="T2 - Puerta 14"
        )
        db.add(vuelo)
        db.commit()
        db.refresh(vuelo)
        print(f"[OK] Vuelo {vuelo.codigo_vuelo} programado.")

        engine = LogisticsEngine(debug=True)

        # 3. Simulate Reminder (24h before)
        print("\n[SIMULATING] 24h Reminder...")
        engine.send_flight_alert(vuelo.id, alert_type="REMINDER")

        # 4. Simulate Flight Delay
        print("\n[SIMULATING] Flight Delay Detected...")
        vuelo.estado = "RETRASADO"
        vuelo.fecha_hora_salida_real = vuelo.fecha_hora_salida_prog + timedelta(hours=2)
        vuelo.fecha_hora_llegada_real = vuelo.fecha_hora_llegada_prog + timedelta(hours=2)
        vuelo.notas_logistica = "Retraso operativo de la aerolínea. El transporte en destino ha sido notificado."
        db.commit()
        
        # Dispatch Urgent Alert
        engine.send_flight_alert(vuelo.id, alert_type="UPDATE")

    finally:
        db.close()

if __name__ == "__main__":
    test_logistics_flight_tracking()
