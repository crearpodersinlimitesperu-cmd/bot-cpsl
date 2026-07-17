import smtplib
import os
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Enterprise Dependencies
try:
    from database import SessionLocal, LogEnvio, TrazabilidadPX
except ImportError:
    SessionLocal = None

class EmailEngine:
    """
    CREAR GLOBAL — Transactional Communication Engine (V2 Enterprise)
    Hardened for Deliverability & Perception Engineering.
    """
    def __init__(self, provider="GMAIL", debug=False):
        load_dotenv(Path(__file__).parent / ".env")
        self.debug = debug
        self.provider = provider
        
        # SMTP Configuration (Standard Fallback)
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.user = os.environ.get("GMAIL_APP_USER", "crearpodersinlimitesperu@gmail.com")
        self.password = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")
        
        # Institutional Brand Assets
        self.base_dir = Path(__file__).parent
        self.logo_path = self.base_dir / "assets" / "logo_principal.png"
        self.logo_white_path = self.base_dir / "assets" / "logo_white.png"
        self.pin_path = self.base_dir / "assets" / "pin_vuelo.jpg"
        self.default_template = self.base_dir / "templates" / "base_enterprise.html"

    def generate_px_token(self, px_id, equipo="E28", year="2026", city="LIM", chapter="C1"):
        """Generates an institutional traceable token."""
        return f"PX-{year}-{city}-{chapter}-{equipo}-{str(px_id).zfill(6)}"

    def load_template(self, template_path, placeholders, preheader=""):
        """Loads modular HTML templates and supports dynamic placeholders + preheader injection."""
        path = Path(template_path) if template_path else self.default_template
        
        if not path.is_file():
            path = self.default_template
            
        content = path.read_text(encoding="utf-8")
        
        # Inject Preheader
        content = content.replace("{{PREHEADER}}", preheader)
        
        for key, value in placeholders.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    def send_enterprise_email(self, to, subject, body_html, attachments=None, px_id=0, metadata=None):
        """
        Executes a luxury-level transactional dispatch.
        - CID Asset Orchestration
        - Legal Traceability
        - Attachment Hashing
        """
        if self.debug:
            print(f"[ENTERPRISE DEBUG] Simulated dispatch to {to}: {subject}")
            return True, "Simulated Dispatch OK"

        if not self.password:
            return False, "CREDENTIALS_MISSING"

        # Create high-fidelity message
        msg = MIMEMultipart("related")
        msg['From'] = f"CREAR GLOBAL Official <{self.user}>"
        msg['To'] = to
        msg['Subject'] = subject
        
        # Ensure institutional headers
        msg.add_header('X-Entity-Ref-ID', str(px_id))
        msg.add_header('X-Priority', '1 (Highest)')

        msg_alt = MIMEMultipart("alternative")
        msg.attach(msg_alt)
        msg_alt.attach(MIMEText(body_html, 'html', 'utf-8'))

        # CID Assets Injection
        if self.logo_path.exists():
            with open(self.logo_path, "rb") as f:
                logo = MIMEImage(f.read())
                logo.add_header("Content-ID", "<logo_crear>")
                logo.add_header("Content-Disposition", "inline", filename="logo.png")
                msg.attach(logo)
        
        if self.pin_path.exists():
            with open(self.pin_path, "rb") as f:
                pin = MIMEImage(f.read())
                pin.add_header("Content-ID", "<pin_vuelo>")
                pin.add_header("Content-Disposition", "inline", filename="pin.jpg")
                msg.attach(pin)

        # Secure Attachment Handling
        attachment_hashes = []
        if attachments:
            for file_path in attachments:
                path = Path(file_path)
                if path.exists():
                    with open(path, "rb") as f:
                        file_data = f.read()
                        attachment_hashes.append(hashlib.sha256(file_data).hexdigest())
                        
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(file_data)
                        encoders.encode_base64(part)
                        part.add_header("Content-Disposition", f'attachment; filename="{path.name}"')
                        msg.attach(part)

        # Institutional Delivery
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            
            self._audit_log(to, subject, 200, px_id, attachment_hashes)
            return True, "DISPATCH_SUCCESS"
        except Exception as e:
            self._audit_log(to, subject, 500, px_id, attachment_hashes, error=str(e))
            return False, f"DISPATCH_FAILURE: {str(e)}"

    def _audit_log(self, to, subject, status, px_id, attachment_hashes, error=None):
        """Mandatory audit logging for operational excellence."""
        if not SessionLocal: return
        db = SessionLocal()
        try:
            log = LogEnvio(
                destino=to, 
                tipo="OUT", 
                canal="EMAIL", 
                mensaje=subject, 
                status_code=status,
                error=error
            )
            db.add(log)
            
            if px_id:
                meta = {
                    "provider": self.provider,
                    "hashes": attachment_hashes,
                    "timestamp_local": datetime.now().isoformat()
                }
                traz = TrazabilidadPX(
                    px_id=px_id, 
                    canal="EMAIL", 
                    tipo_evento="INSTITUTIONAL_DISPATCH", 
                    contenido=f"Subject: {subject}", 
                    metadatos=str(meta)
                )
                db.add(traz)
            db.commit()
        except Exception as e:
            print(f"[AUDIT ERROR] {e}")
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    engine = EmailEngine(debug=True)
    print("CREAR GLOBAL Enterprise Engine (V2) initialized.")
