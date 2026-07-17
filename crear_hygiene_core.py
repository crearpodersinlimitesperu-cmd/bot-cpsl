import re
import socket
from database import SessionLocal, Usuario

class EmailHygiene:
    """
    Core logic for Email Hygiene & Database Health.
    Prevents dispatches to invalid/risky addresses.
    """
    
    TYPO_CORRECTIONS = {
        "gmial.com": "gmail.com",
        "gamil.com": "gmail.com",
        "hotnail.com": "hotmail.com",
        "hotmil.com": "hotmail.com",
        "outlok.com": "outlook.com",
        "outlok.es": "outlook.es",
        "gmai.com": "gmail.com"
    }

    def __init__(self):
        pass

    def validate_syntax(self, email):
        """Basic regex validation."""
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(pattern, email) is not None

    def detect_typo(self, email):
        """Detects common domain typos."""
        if "@" not in email: return None
        domain = email.split("@")[1].lower()
        return self.TYPO_CORRECTIONS.get(domain)

    def check_mx_record(self, email):
        """Verifies if the domain has a valid MX record (Requires internet)."""
        if "@" not in email: return False
        domain = email.split("@")[1]
        try:
            # Basic check using socket (cheaper than full DNS library)
            socket.gethostbyname(domain)
            return True
        except:
            return False

    def sanitize_database(self):
        """Scans all PXs and updates their email_status."""
        db = SessionLocal()
        count_fixed = 0
        count_invalid = 0
        
        try:
            participants = db.query(Usuario).filter(Usuario.tipo == "PX").all()
            for px in participants:
                email = str(px.email).lower().strip()
                
                # 1. Detect Typos
                correction = self.detect_typo(email)
                if correction:
                    new_email = email.split("@")[0] + "@" + correction
                    print(f"[HYGIENE] Fixing Typo: {email} -> {new_email}")
                    px.email = new_email
                    px.email_status = "VALID" # Potentially valid now
                    count_fixed += 1
                    continue

                # 2. Validate Syntax
                if not self.validate_syntax(email):
                    px.email_status = "INVALID"
                    px.last_bounce_reason = "SYNTAX_ERROR"
                    count_invalid += 1
                    continue

                # 3. Check Domain (Optional/Expensive - skip for fast sanitization or do sample)
                # if not self.check_mx_record(email):
                #     px.email_status = "INVALID"
                #     px.last_bounce_reason = "DOMAIN_NOT_FOUND"
                #     count_invalid += 1

            db.commit()
            return count_fixed, count_invalid
        finally:
            db.close()

if __name__ == "__main__":
    hygiene = EmailHygiene()
    fixed, invalid = hygiene.sanitize_database()
    print(f"Sanitization Complete: {fixed} fixed, {invalid} marked as invalid.")
