import json
from database import SessionLocal, Usuario, TrazabilidadPX, DecisionIA
from datetime import datetime

class OrquestadorIA:
    def __init__(self, db_session):
        self.db = db_session
        self.agente_nombre = "ORQUESTADOR_MULTIAGENTE_IA"

    def agente_clasificador_intencion(self, texto):
        """Analiza el texto de una respuesta para detectar la intencion del PX."""
        t = texto.lower()
        
        # Logica de clasificacion (Simulacion de IA avanzada)
        if any(w in t for w in ["si", "confirmado", "asistire", "voy", "listo", "cuenta conmigo"]):
            return "CONFIRMADO", 1.0
        if any(w in t for w in ["no", "stop", "parar", "baja", "quitar", "no quiero"]):
            return "SOLICITA_BAJA", 1.0
        if any(w in t for w in ["duda", "pregunta", "donde", "cuando", "precio", "hora"]):
            return "DUDA_TECNICA", 0.9
        if any(w in t for w in ["devolucion", "dinero", "reembolso"]):
            return "DEVOLUCION", 0.95
            
        return "INDETERMINADO", 0.5

    def agente_auditor_mensaje(self, mensaje):
        """Revisa si el mensaje cumple con los estandares de cultura CPSL."""
        # Check simple de palabras prohibidas o estilo robótico
        if len(mensaje) < 10: return False, "Mensaje demasiado corto/no enrolador"
        if "asunto urgente" in mensaje.lower(): return False, "Suena a spam tradicional"
        
        return True, "Mensaje alineado con Cultura CPSL"

    def procesar_respuesta_px(self, px_id, canal, texto):
        """Coordina la clasificacion y actualiza la trazabilidad."""
        intencion, score = self.agente_clasificador_intencion(texto)
        
        # Registrar decision en Caja Negra
        d = DecisionIA(
            entidad_id=px_id,
            agente="AGENTE_CLASIFICADOR",
            decision=intencion,
            justificacion=f"Intencion detectada en respuesta via {canal}",
            score_confianza=score
        )
        self.db.add(d)
        
        # Actualizar Trazabilidad
        t = TrazabilidadPX(
            px_id=px_id,
            canal=canal,
            tipo_evento="RESPUESTA",
            contenido=texto,
            metadatos=json.dumps({"intencion": intencion, "score": score})
        )
        self.db.add(t)
        self.db.commit()
        
        print(f"   [IA] PX {px_id} clasificado como: {intencion} ({score*100}%)")
        return intencion

if __name__ == "__main__":
    db = SessionLocal()
    ia = OrquestadorIA(db)
    # Probar clasificacion
    test_texts = [
        "Si confirmo mi asistencia al C1",
        "Por favor denme de baja de la lista, STOP",
        "Tengo una duda sobre el horario de inicio"
    ]
    for txt in test_texts:
        res, score = ia.agente_clasificador_intencion(txt)
        print(f"Texto: '{txt}' -> Clasificacion: {res} ({score})")
    db.close()
