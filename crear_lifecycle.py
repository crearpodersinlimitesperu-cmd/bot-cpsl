from crear_email_core import EmailEngine
from generar_contrato_pdf import generate_boarding_pass_contract
from crear_experience_cloud import ExperienceCloud
from database import SessionLocal, Usuario, TrazabilidadPX
# Handling internal package path for SMSGateway
import sys
from pathlib import Path
import os

# Mocking SMSGateway if not in path or using local if available
try:
    from sms_gateway import SMSGateway # We will create a local proxy/shortcut
except ImportError:
    class SMSGateway:
        def send_sms(self, phone, msg): print(f"[MOCK SMS] To {phone}: {msg}"); return True

class CommunicationLifecycle:
    """
    Coordinates the transactional communication lifecycle (Email + SMS) for CREAR GLOBAL.
    Now integrated with Experience Cloud for behavioral scoring.
    """
    def __init__(self, debug=False):
        self.engine = EmailEngine(debug=debug)
        self.cloud = ExperienceCloud()
        self.sms = SMSGateway()
        self.base_dir = Path(__file__).parent

    def trigger_admission(self, px_data):
        """
        Stage 1: ADMISSION_VALIDATED
        Sent immediately after payment/registration validation.
        Includes the Boarding Pass Contract.
        """
        # 1. Prepare Data & PDF
        px_id = px_data.get('id', 0)
        
        # HYGIENE CHECK: Prevent send if status is known invalid
        db = SessionLocal()
        px = db.query(Usuario).filter(Usuario.id == px_id).first()
        if px and px.email_status in ["INVALID", "BOUNCED"]:
            print(f"[HYGIENE] Skipping dispatch to {px.email} (Status: {px.email_status})")
            db.close()
            return self.trigger_recovery_sms(px_data)
        
        # Close session early if not needed for bounce update
        db.close()

        print(f"   [STEP 1] Generating contract PDF...")
        token = self.engine.generate_px_token(px_id, equipo=px_data.get('equipo', 'E28'))
        
        # Professional PDF Naming: Contrato_C1_E28_NOMBRE.pdf
        nombre_file = str(px_data.get('nombre', 'PX')).upper().replace(" ", "_")
        pdf_filename = f"Contrato_C1_E28_{nombre_file}.pdf"
        pdf_path = self.base_dir / pdf_filename
        
        generate_boarding_pass_contract(px_data, token, str(pdf_path))
        
        # 2. Prepare Communication
        subject = f"Confirmación Oficial — Capítulo 1 | Equipo {px_data.get('equipo', 'E28')} Lima"
        
        # Inyectar instrucción de respuesta humana para reputación
        reply_prompt = "<p style='color: #b49632; font-weight: bold;'>IMPORTANTE: Por favor, responda a este correo con la palabra 'RECIBIDO' para confirmar la validación exitosa de su contrato institucional.</p>"
        
        placeholders = {
            "GREETING": f"ADMISIÓN OFICIAL — {px_data.get('nombre', '').upper()}",
            "CONTENT": f"""
            <p>Usted ha sido admitido formalmente en el programa de transformacion de alto rendimiento de <b>CREAR GLOBAL</b>.</p>
            {reply_prompt}
            <div class="info-box" style="background-color: #fcfcfc; border-left: 4px solid #b49632; padding: 25px; margin: 30px 0; border-radius: 0 8px 8px 0; border: 1px solid #eeeeee;">
                <b style="color: #1a1a2e; text-transform: uppercase; letter-spacing: 1px;">Detalles de su Expediente</b><br/>
                ID Institucional: <span style="color: #b49632; font-weight: bold;">{token}</span><br/>
                Participante: {px_data.get('nombre', 'PX')}<br/>
                Documento: {px_data.get('documento', 'N/A')}<br/>
                Programa: Capitulo Uno - Equipo {px_data.get('equipo', 'E28')}<br/>
                Estado: <span style="color: #27ae60; font-weight: bold;">ACEPTADO</span>
            </div>
            
            <div style="text-align: center; margin: 30px 0;">
                <p style="font-size: 11px; color: #b49632; text-transform: uppercase; letter-spacing: 2px; font-weight: bold; margin-bottom: 10px;">Insignia de Admisión</p>
                <img src="cid:pin_vuelo" alt="Yo Vuelo Con Los Míos" width="140" style="display: inline-block; width: 140px;" />
            </div>

            <p>Adjunto a esta comunicacion encontrara su <b>Boarding Pass Institucional</b> y Contrato de Terminos. Este documento es su comprobante oficial de admision y debe ser conservado para su expediente personal.</p>
            
            <table border="0" cellpadding="0" cellspacing="0" width="100%">
                <tr>
                    <td align="center" style="padding: 30px 0;">
                        <a href="https://crearglobal.com" style="background-color: #b49632; color: #ffffff; padding: 18px 40px; text-decoration: none; border-radius: 4px; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; font-size: 14px;">Acceder al Portal del Participante</a>
                    </td>
                </tr>
            </table>
            
            <p style="font-size: 13px; color: #888888; text-align: center;">Su lugar ha sido reservado y blindado institucionalmente.</p>
            """
        }
        
        preheader = "Su admisión ha sido validada institucionalmente."
        html = self.engine.load_template("", placeholders, preheader=preheader)
        
        print(f"   [STEP 2] Dispatching institutional email...")
        # 3. Dispatch
        success, msg = self.engine.send_enterprise_email(
            to=px_data['email'],
            subject=subject,
            body_html=html,
            attachments=[str(pdf_path)],
            px_id=px_id,
            metadata={"lifecycle_stage": "ADMISSION_VALIDATED", "token": token}
        )
        
        if not success and "BOUNCE" in msg.upper():
            print(f"   [HYGIENE] Bounce detected: {msg}")
            # Re-open session to update status
            db = SessionLocal()
            px = db.query(Usuario).filter(Usuario.id == px_id).first()
            if px:
                px.email_status = "BOUNCED"
                px.last_bounce_reason = msg
                px.bounce_count = (px.bounce_count or 0) + 1
                db.commit()
                self.trigger_recovery_sms(px_data)
            db.close()
        
        # 4. Behavioral Record (Experience Cloud)
        if success:
            self.cloud.record_interaction(
                px_data.get('id', 0), 
                "ADMISSION_SENT", 
                metadata={"canal": "EMAIL", "stage": "ADMITTED"}
            )
        
        # Cleanup PDF if needed or move to a secure storage
        if os.path.exists(pdf_path) and not self.engine.debug:
            os.remove(pdf_path)
            
        return success, msg

    def trigger_recovery_sms(self, px_data):
        """Triggers the SMS recovery flow for invalid emails."""
        phone = px_data.get('telefono')
        if not phone:
            return False, "HYGIENE_FAILURE: No phone for recovery"
        
        msg = (
            "Hola, detectamos un inconveniente con tu correo registrado en CREAR GLOBAL. "
            "Por favor responde este mensaje con tu correo actualizado para asegurar la correcta recepcion de tu contrato oficial."
        )
        self.sms.send_sms(phone, msg)
        return False, "HYGIENE_INTERVENTION_TRIGGERED"

if __name__ == "__main__":
    # Test lifecycle
    lifecycle = EmailLifecycle(debug=True)
    test_px = {
        "id": 88,
        "nombre": "EMPLEADO DE PRUEBA",
        "documento": "99999999",
        "equipo": "E28",
        "email": "test@crearglobal.com"
    }
    s, m = lifecycle.trigger_admission(test_px)
    print(f"Lifecycle Admission Test: {s} - {m}")
