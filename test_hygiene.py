from database import SessionLocal, Usuario, init_db
from crear_hygiene_core import EmailHygiene
from crear_lifecycle import CommunicationLifecycle
from unittest.mock import patch

def test_hygiene_flow():
    print("--- CREAR GLOBAL: EMAIL HYGIENE SIMULATION ---")
    init_db()
    db = SessionLocal()
    
    # 0. Clear participants to avoid UNIQUE constraints
    db.query(Usuario).delete()
    db.commit()
    
    # 1. Create participants with bad emails
    px1 = Usuario(
        nombre="JOEL TYPO",
        email="joel@gmial.com", # TYPO
        telefono="999888777",
        tipo="PX",
        journey_stage="NEW"
    )
    px2 = Usuario(
        nombre="MARIA INVALID",
        email="maria@@wrong..com", # INVALID
        telefono="999111222",
        tipo="PX",
        journey_stage="NEW"
    )
    db.add(px1)
    db.add(px2)
    db.commit()
    print("[OK] Participants with bad emails created.")

    # 2. Run Hygiene Scan
    hygiene = EmailHygiene()
    fixed, invalid = hygiene.sanitize_database()
    print(f"[RESULT] Scan: {fixed} Fixed, {invalid} Marked as Invalid.")

    # 3. Refresh and Check
    db.refresh(px1)
    print(f"PX2 Email: {px2.email} | Status: {px2.email_status}")
    
    # Store data for lifecycle before closing session
    px1_data = {"id": px1.id, "nombre": px1.nombre, "email": px1.email, "telefono": px1.telefono}
    px2_data = {"id": px2.id, "nombre": px2.nombre, "email": px2.email, "telefono": px2.telefono}
    
    db.close()

    # 4. Attempt Lifecycle Trigger
    print("\n[ACTION] Attempting Admission Dispatch...")
    with patch('crear_lifecycle.generate_boarding_pass_contract', return_value="mock_path.pdf"):
        lifecycle = CommunicationLifecycle(debug=True)
        
        # PX1 (Fixed)
        print(f"Processing PX1 ({px1_data['nombre']})...")
        lifecycle.trigger_admission({"id": px1_data['id'], "nombre": px1_data['nombre'], "email": px1_data['email'], "telefono": px1_data['telefono'], "documento": "123"})
        
        # PX2 (Invalid) - Should trigger SMS
        print(f"Processing PX2 ({px2_data['nombre']})...")
        success, msg = lifecycle.trigger_admission({"id": px2_data['id'], "nombre": px2_data['nombre'], "email": px2_data['email'], "telefono": px2_data['telefono'], "documento": "456"})
        print(f"Result for PX2: {msg}")

if __name__ == "__main__":
    test_hygiene_flow()
