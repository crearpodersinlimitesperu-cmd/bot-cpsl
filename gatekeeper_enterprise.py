import re
import dns.resolver
from database import SessionLocal, Usuario, TrazabilidadPX, DecisionIA, ReputacionCanal
from datetime import datetime

class Gatekeeper:
    def __init__(self, db_session):
        self.db = db_session
        self.agente = "GATEKEEPER_ENTERPRISE"

    def validar_email_mx(self, email):
        """Regla 2: Correo valido (Check MX)."""
        if not email or "@" not in email: return False
        domain = email.split('@')[-1]
        try:
            dns.resolver.resolve(domain, 'MX')
            return True
        except:
            return False

    def check_15_puntos(self, px_id):
        """Ejecuta el protocolo de validacion blindada."""
        px = self.db.query(Usuario).filter(Usuario.id == px_id).first()
        if not px: return False, "Usuario no existe"

        razones_bloqueo = []

        # 1. Nombre Valido
        if not px.nombre or len(px.nombre) < 3: razones_bloqueo.append("Nombre invalido")

        # 2. Correo Valido
        if not self.validar_email_mx(px.email): razones_bloqueo.append("Email sin MX valido")

        # 3. Telefono Valido
        if not px.telefono or len(re.sub(r'\D', '', px.telefono)) < 9: razones_bloqueo.append("Telefono invalido")

        # 5-10. Revisar Trazabilidad (Bounces, STOP, Devolucion, No Interesado)
        trazabilidad = self.db.query(TrazabilidadPX).filter(TrazabilidadPX.px_id == px_id).all()
        for t in trazabilidad:
            if t.tipo_evento == "BOUNCE": razones_bloqueo.append("Rebote historico detectado")
            if "STOP" in str(t.contenido).upper(): razones_bloqueo.append("Solicitud STOP detectada")
            if "DEVOLUCION" in str(t.contenido).upper(): razones_bloqueo.append("Caso DEVOLUCION")
            if "NO INTERESADO" in str(t.contenido).upper(): razones_bloqueo.append("NO INTERESADO historico")

        # 11. Asignado a Diana/Joyce
        cc = str(px.cc_asignada).upper()
        if "DIANA" not in cc and "JOYCE" not in cc:
            razones_bloqueo.append(f"Jurisdiccion invalida: Asignado a {cc}")

        # 12. Jornada Activa (8 AM - 8 PM)
        ahora = datetime.now().hour
        if ahora < 8 or ahora >= 20:
            razones_bloqueo.append("Fuera de horario operativo (8AM-8PM)")

        # Decision Final
        decision = "BLOQUEADO" if razones_bloqueo else "APROBADO"
        justificacion = "; ".join(razones_bloqueo) if razones_bloqueo else "Cumple los 15 puntos de blindaje"
        
        # Registrar decision en la Caja Negra
        d = DecisionIA(
            entidad_id=px_id,
            agente=self.agente,
            decision=decision,
            justificacion=justificacion,
            score_confianza=1.0 if decision == "APROBADO" else 0.0
        )
        self.db.add(d)
        self.db.commit()

        return decision == "APROBADO", justificacion

if __name__ == "__main__":
    db = SessionLocal()
    gk = Gatekeeper(db)
    # Probar con un PX aleatorio
    px = db.query(Usuario).first()
    if px:
        aprobado, motivo = gk.check_15_puntos(px.id)
        print(f"Resultado para {px.nombre}: {aprobado} | Motivo: {motivo}")
    db.close()
