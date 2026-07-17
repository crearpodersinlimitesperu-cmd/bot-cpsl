import os
from pathlib import Path
from database import SessionLocal, Entrenador, VueloLogistica
from crear_email_core import EmailEngine

try:
    from sms_gateway import SMSGateway
except ImportError:
    class SMSGateway:
        def send_sms(self, phone, msg): print(f"[MOCK SMS] To {phone}: {msg}"); return True

class LogisticsEngine:
    """
    Orchestrates flight tracking and operational alerts for CREAR GLOBAL.
    """
    def __init__(self, debug=False):
        self.engine = EmailEngine(debug=debug)
        self.sms = SMSGateway()
        self.base_dir = Path(__file__).parent
        self.template_path = self.base_dir / "templates" / "flight_alert_premium.html"

    def _get_status_class(self, status):
        status_map = {
            "PROGRAMADO": "status-programado",
            "RETRASADO": "status-retrasado",
            "CANCELADO": "status-cancelado",
            "EN_VUELO": "status-en_vuelo",
            "ATERRIZADO": "status-programado"
        }
        return status_map.get(status.upper(), "status-programado")

    def _format_time(self, dt_obj):
        if not dt_obj: return "TBD"
        return dt_obj.strftime("%d %b %Y - %H:%M")

    def send_flight_alert(self, vuelo_id, alert_type="REMINDER", notas_adicionales=""):
        """
        Sends a flight alert to the trainer (and optionally logistics staff).
        alert_type: REMINDER (24h/4h) or UPDATE (Delay, Cancellation, Gate change).
        """
        db = SessionLocal()
        try:
            vuelo = db.query(VueloLogistica).filter(VueloLogistica.id == vuelo_id).first()
            if not vuelo:
                return False, "Vuelo no encontrado"

            entrenador = db.query(Entrenador).filter(Entrenador.id == vuelo.entrenador_id).first()
            if not entrenador:
                return False, "Entrenador no encontrado"

            # 1. Determine Context
            is_update = alert_type == "UPDATE"
            subject_prefix = "ACTUALIZACIÓN URGENTE" if is_update else "Recordatorio de Vuelo"
            subject = f"{subject_prefix}: {vuelo.codigo_vuelo} ({vuelo.origen} a {vuelo.destino})"

            if is_update and vuelo.estado == "RETRASADO":
                greeting = f"Atención {entrenador.nombre.split()[0]}, tu vuelo presenta un retraso."
                content = "<p>El itinerario de tu vuelo ha sido modificado. Revisa los nuevos horarios detallados a continuación.</p>"
                preheader = f"Tu vuelo {vuelo.codigo_vuelo} ha sido retrasado."
            elif is_update and vuelo.estado == "CANCELADO":
                greeting = f"URGENTE: {entrenador.nombre.split()[0]}, vuelo cancelado."
                content = "<p style='color: #c0392b; font-weight: bold;'>Tu vuelo ha sido CANCELADO. El equipo de logística se pondrá en contacto contigo inmediatamente para gestionar alternativas.</p>"
                preheader = f"URGENTE: Vuelo {vuelo.codigo_vuelo} CANCELADO."
            else:
                greeting = f"Hola {entrenador.nombre.split()[0]}, este es el itinerario de tu vuelo."
                content = "<p>A continuación encontrarás los detalles operativos para tu próximo vuelo con CREAR GLOBAL.</p>"
                preheader = f"Itinerario confirmado para tu vuelo {vuelo.codigo_vuelo}."

            extra_notes_html = ""
            if notas_adicionales or vuelo.notas_logistica:
                notes = notas_adicionales or vuelo.notas_logistica
                extra_notes_html = f"""
                <div style="background-color: #fff8e1; border-left: 4px solid #f39c12; padding: 15px; margin-bottom: 20px;">
                    <strong style="color: #d35400;">Notas Logísticas:</strong><br/>
                    <span style="font-size: 13px; color: #555;">{notes}</span>
                </div>
                """

            # 2. Render HTML
            placeholders = {
                "GREETING": greeting,
                "CONTENT": content,
                "FLIGHT_STATUS": vuelo.estado.upper(),
                "STATUS_CLASS": self._get_status_class(vuelo.estado),
                "FLIGHT_CODE": vuelo.codigo_vuelo,
                "ORIGIN": vuelo.origen,
                "DESTINATION": vuelo.destino,
                "DEP_TIME": self._format_time(vuelo.fecha_hora_salida_real or vuelo.fecha_hora_salida_prog),
                "ARR_TIME": self._format_time(vuelo.fecha_hora_llegada_real or vuelo.fecha_hora_llegada_prog),
                "TERMINAL_GATE": vuelo.terminal_puerta or "Pendiente confirmación",
                "EXTRA_NOTES": extra_notes_html
            }

            html = self.engine.load_template(str(self.template_path), placeholders, preheader=preheader)

            # 3. Dispatch Email
            print(f"[LOGISTICS] Sending {alert_type} Email to {entrenador.email}...")
            success, msg = self.engine.send_enterprise_email(
                to=entrenador.email,
                subject=subject,
                body_html=html,
                px_id=0, # No PX ID for logistics
                metadata={"module": "LOGISTICS_CLOUD", "vuelo_id": vuelo.id}
            )

            # 4. Dispatch SMS for URGENT updates
            if success and is_update and entrenador.telefono:
                print(f"[LOGISTICS] Sending URGENT SMS to {entrenador.telefono}...")
                sms_msg = f"CREAR ALERTA: Tu vuelo {vuelo.codigo_vuelo} a {vuelo.destino} ha cambiado a estado {vuelo.estado}. Revisa tu correo institucional."
                self.sms.send_sms(entrenador.telefono, sms_msg)

            return success, msg

        finally:
            db.close()

if __name__ == "__main__":
    pass
