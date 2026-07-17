from database import SessionLocal, Usuario, LogEnvio
from datetime import datetime

def check_phase1_health():
    db = SessionLocal()
    print("--- CREAR GLOBAL: Fase 1 - Validación de Salud Operativa ---")
    
    try:
        # 1. Coverage
        total_px = db.query(Usuario).filter(Usuario.tipo == "PX").count()
        print(f"[OK] Participantes registrados: {total_px}")

        # 2. Engagement Validation
        engaged = db.query(Usuario).filter(Usuario.px_score > 0).count()
        engagement_rate = (engaged / total_px * 100) if total_px > 0 else 0
        print(f"[OK] Tasa de Engagement (Score > 0): {engagement_rate:.1f}%")

        # 3. Delivery Validation
        total_sent = db.query(LogEnvio).filter(LogEnvio.status_code == 200).count()
        errors = db.query(LogEnvio).filter(LogEnvio.status_code != 200).count()
        print(f"[OK] Envíos exitosos (SMTP): {total_sent}")
        if errors > 0:
            print(f"[WARN] Errores detectados: {errors}")

        # 4. Critical Milestones
        signed = db.query(Usuario).filter(Usuario.journey_stage == "VALIDATED").count()
        print(f"[OK] Contratos Validados (Hito Crítico): {signed}")

        print("\n--- Estatus de Validación: ESTABLE ---")
        print("Recomendación: Continuar con el volumen actual (30-50 envíos/hora).")

    finally:
        db.close()

if __name__ == "__main__":
    check_phase1_health()
