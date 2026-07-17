import json
from datetime import datetime
from database import SessionLocal, Usuario, TrazabilidadPX

class ExperienceCloud:
    """
    The Intelligence Core of CREAR GLOBAL.
    Manages behavioral scoring and journey states.
    """
    
    SCORING_WEIGHTS = {
        "EMAIL_OPEN": 5,
        "EMAIL_CLICK": 10,
        "EMAIL_REPLY": 25,
        "CONTRACT_SIGNED": 50,
        "WA_REPLY": 15,
        "FORM_SUBMITTED": 30,
        "BOUNCE": -20,
        "UNSUBSCRIBE": -100
    }

    JOURNEY_STAGES = [
        "NEW",              # Just entered the system
        "ADMITTED",         # Contract sent
        "VALIDATED",        # Contract signed
        "ENGAGED",          # High interaction
        "READY_FOR_FLIGHT", # All requirements met
        "AT_RISK",          # Low interaction / No response
        "INACTIVE"          # Dropped out
    ]

    def __init__(self):
        pass

    def record_interaction(self, px_id, event_type, metadata=None):
        """Records a behavioral event and updates the PX score."""
        db = SessionLocal()
        try:
            px = db.query(Usuario).filter(Usuario.id == px_id).first()
            if not px:
                return False, "PX_NOT_FOUND"

            # Update Score
            points = self.SCORING_WEIGHTS.get(event_type, 0)
            px.px_score = (px.px_score or 0) + points
            px.last_interaction = datetime.utcnow()

            # Record Traceability
            traz = TrazabilidadPX(
                px_id=px_id,
                canal=metadata.get("canal", "SYSTEM") if metadata else "SYSTEM",
                tipo_evento="BEHAVIORAL_INTERACTION",
                contenido=f"Event: {event_type} | Points: {points}",
                metadatos=json.dumps(metadata) if metadata else None
            )
            db.add(traz)

            # Auto-update Journey Stage based on score/events
            self._evaluate_journey_state(px, event_type)

            db.commit()
            return True, f"Score updated: {px.px_score}"
        except Exception as e:
            db.rollback()
            return False, str(e)
        finally:
            db.close()

    def _evaluate_journey_state(self, px, last_event):
        """Internal logic to advance the participant through the journey."""
        # Logic for state transitions
        if last_event == "CONTRACT_SIGNED":
            px.journey_stage = "VALIDATED"
        
        if px.px_score >= 100 and px.journey_stage == "VALIDATED":
            px.journey_stage = "ENGAGED"
            
        if px.px_score >= 200:
            px.journey_stage = "READY_FOR_FLIGHT"
            
        # At-risk detection
        # (This would usually be triggered by a cron job checking 'last_interaction', 
        # but we can do a basic check here if needed)
        pass

    def get_engagement_profile(self, px_id):
        """Infers an engagement profile based on behavioral tags and speed."""
        # Future: Use heuristics to tag PX
        # e.g., "FAST_EXECUTION", "DETAIL_ORIENTED"
        return "STANDARD_ENGAGEMENT"

    def get_next_best_action(self, px_id):
        """Decides the most appropriate next communication based on stage and score."""
        db = SessionLocal()
        px = db.query(Usuario).filter(Usuario.id == px_id).first()
        db.close()

        if not px: return "NO_ACTION"

        if px.journey_stage == "NEW":
            return "TRIGGER_ADMISSION"
        elif px.journey_stage == "ADMITTED" and px.px_score < 10:
            return "SEND_SOFT_REMINDER"
        elif px.journey_stage == "AT_RISK":
            return "ESC_TO_COORDINATOR"
        
        return "MAINTAIN_ENGAGEMENT"

if __name__ == "__main__":
    cloud = ExperienceCloud()
    print("Experience Cloud initialized.")
