from crear_experience_cloud import ExperienceCloud
from database import SessionLocal, Usuario, init_db
import json

def simulate_px_journey():
    print("--- CREAR EXPERIENCE CLOUD SIMULATION ---")
    init_db()
    
    db = SessionLocal()
    # Create a fresh mock participant
    px = Usuario(
        nombre="PX SIMULADO",
        email="sim@crearglobal.com",
        documento="88776655",
        tipo="PX",
        journey_stage="NEW",
        px_score=0
    )
    db.add(px)
    db.commit()
    px_id = px.id
    print(f"[OK] PX Created with ID: {px_id} | Stage: {px.journey_stage}")

    cloud = ExperienceCloud()

    # Step 1: Admission Sent
    print("\n[ACTION] Sending Admission Email...")
    cloud.record_interaction(px_id, "EMAIL_OPEN", {"canal": "EMAIL"})
    
    # Refresh PX
    db.refresh(px)
    print(f"[SCORE] Interaction Recorded. New Score: {px.px_score} | Stage: {px.journey_stage}")

    # Step 2: Contract Interaction
    print("\n[ACTION] Participant Clicks on Contract...")
    cloud.record_interaction(px_id, "EMAIL_CLICK", {"canal": "EMAIL", "link": "contract_download"})
    
    db.refresh(px)
    print(f"[SCORE] High Engagement detected. Score: {px.px_score}")

    # Step 3: Contract Signed (Major Milestone)
    print("\n[ACTION] Participant Signs Contract!")
    cloud.record_interaction(px_id, "CONTRACT_SIGNED", {"canal": "SYSTEM"})
    
    db.refresh(px)
    print(f"[JOURNEY] Stage Transition! New Stage: {px.journey_stage} | Score: {px.px_score}")

    # Step 4: Engagement Surge
    print("\n[ACTION] Multiple interactions recorded...")
    cloud.record_interaction(px_id, "EMAIL_REPLY", {"canal": "EMAIL"})
    cloud.record_interaction(px_id, "FORM_SUBMITTED", {"canal": "WEB"})
    
    db.refresh(px)
    print(f"[FINAL STATE] Score: {px.px_score} | Stage: {px.journey_stage}")
    
    if px.journey_stage == "ENGAGED":
        print("[OK] PX reached 'ENGAGED' status automatically.")

    # NBA Check
    nba = cloud.get_next_best_action(px_id)
    print(f"\n[INTELLIGENCE] Next Best Action (NBA): {nba}")

    db.close()

if __name__ == "__main__":
    simulate_px_journey()
