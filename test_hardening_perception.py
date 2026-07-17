from crear_lifecycle import EmailLifecycle
import os
from pathlib import Path

def validate_hardening_phase():
    print("--- CREAR GLOBAL HARDENING VALIDATION ---")
    
    # Initialize Lifecycle (Debug Mode)
    lifecycle = EmailLifecycle(debug=True)
    
    # Mock Participant
    px_data = {
        "id": 184,
        "nombre": "ROCIO JARA AMPUERO",
        "documento": "07938881",
        "equipo": "E28",
        "email": "rjampuero@gmail.com"
    }
    
    print(f"[STAGE 1] Triggering Admission for PX-{px_data['id']}...")
    success, msg = lifecycle.trigger_admission(px_data)
    
    if success:
        print(f"[SUCCESS] Admission Lifecycle triggered: {msg}")
        
        # Verify Token Logic
        token = lifecycle.engine.generate_px_token(px_data['id'], px_data['equipo'])
        print(f"[VERIFY] Institutional Token: {token}")
        if token == "PX-2026-LIM-C1-E28-000184":
            print("[OK] Token matches Enterprise naming standard.")
        else:
            print("[ERROR] Token naming standard mismatch.")
            
        # Verify Template Components (Simulated)
        template_path = Path(__file__).parent / "templates" / "base_enterprise.html"
        html_content = template_path.read_text(encoding="utf-8")
        
        if "{{PREHEADER}}" in html_content:
            print("[OK] Preheader hook detected in base template.")
        else:
            print("[ERROR] Preheader hook missing in base template.")
            
        if "prefers-color-scheme: dark" in html_content:
            print("[OK] Dark Mode safeguards detected in CSS.")
        else:
            print("[ERROR] Dark Mode safeguards missing.")
            
    else:
        print(f"[FAILED] {msg}")

if __name__ == "__main__":
    validate_hardening_phase()
