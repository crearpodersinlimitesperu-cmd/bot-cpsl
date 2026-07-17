import json
from datetime import datetime, timedelta
from database import SessionLocal, Usuario, TrazabilidadPX

# Mocking SMSGateway if not in path or using local if available
try:
    from sms_gateway import SMSGateway
except ImportError:
    class SMSGateway:
        def send_sms(self, phone, msg): print(f"[MOCK SMS] To {phone}: {msg}"); return True

class ExperienceWatchtower:
    """
    Proactive monitoring system for CREAR GLOBAL.
    Triggers alerts based on behavioral data and inactivity.
    """
    
    INACTIVITY_THRESHOLD_DAYS = 3
    LOW_SCORE_THRESHOLD = 10
    
    COORDINATOR_PHONES = {
        "DIANA": "999888777", # Placeholder, should be in DB or Env
        "JOYCE": "999111222"
    }

    def __init__(self):
        self.sms = SMSGateway()

    def scan_for_risks(self):
        """Scans the database for at-risk participants."""
        db = SessionLocal()
        alerts = []
        try:
            participants = db.query(Usuario).filter(Usuario.tipo == "PX", Usuario.journey_stage != "INACTIVE").all()
            now = datetime.utcnow()

            for px in participants:
                risk_factors = []
                
                # Check 1: Inactivity
                if px.last_interaction:
                    days_inactive = (now - px.last_interaction).days
                    if days_inactive >= self.INACTIVITY_THRESHOLD_DAYS:
                        risk_factors.append(f"INACTIVITY_{days_inactive}_DAYS")
                elif (now - px.created_at).days >= 1:
                    risk_factors.append("NO_INITIAL_INTERACTION")

                # Check 2: Low Score in Admitted Stage
                if px.journey_stage == "ADMITTED" and (px.px_score or 0) < self.LOW_SCORE_THRESHOLD:
                    risk_factors.append("LOW_ENGAGEMENT_ADMITTED")

                # Check 3: Contract Pending
                if px.journey_stage == "ADMITTED" and not px.tc_accepted_at:
                    risk_factors.append("PENDING_CONTRACT")

                if risk_factors:
                    alerts.append({
                        "px_id": px.id,
                        "nombre": px.nombre,
                        "coordinator": px.cc_asignada,
                        "factors": risk_factors,
                        "score": px.px_score,
                        "stage": px.journey_stage
                    })
            
            return alerts
        finally:
            db.close()

    def trigger_coordinator_notifications(self, alerts):
        """Simulates sending alerts to Joyce/Diana."""
        if not alerts:
            print("[WATCHTOWER] No risks detected. Operation stable.")
            return

        print(f"[WATCHTOWER] ALERT: {len(alerts)} participants require attention!")
        for alert in alerts:
            msg = (
                f"CREAR ALERT: PX {alert['nombre']} (Score: {alert['score']}) "
                f"en etapa {alert['stage']} requiere atencion. Factores: {', '.join(alert['factors'])}"
            )
            print(msg)
            
            # Send SMS to Coordinator
            coord_upper = str(alert['coordinator']).upper()
            phone = self.COORDINATOR_PHONES.get(coord_upper)
            if phone:
                self.sms.send_sms(phone, msg)
            else:
                print(f"[WATCHTOWER] No phone found for coordinator {alert['coordinator']}")

if __name__ == "__main__":
    watchtower = ExperienceWatchtower()
    risks = watchtower.scan_for_risks()
    watchtower.trigger_coordinator_notifications(risks)
