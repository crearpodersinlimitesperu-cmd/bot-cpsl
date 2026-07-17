import sqlite3
import re
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'

class Gatekeeper:
    def __init__(self):
        # Reglas operativas estrictas CPSL
        self.allowed_cc_c1_c2 = ['dmoscoso', 'jmarin', 'Diana Moscoso', 'Joyce Marin', 'Joyce Marín']
        self.allowed_cc_mj = ['lvalencia', 'Linid Valencia']
        
    def _log_bloqueo(self, participante_id, canal, motivo):
        try:
            conn = sqlite3.connect(CAJA_NEGRA_PATH)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                           ('GATEKEEPER', 'ENVIO_BLOQUEADO', f"ID: {participante_id} | Canal: {canal} | Motivo: {motivo}", 'BLOQUEADO'))
            conn.commit()
            conn.close()
        except:
            pass
            
    def _validar_email(self, email):
        if not email or str(email).strip() == "" or str(email).upper() == "REBOTE" or str(email).upper() == "NAN":
            return False, "Correo vacío, nulo o marcado como REBOTE."
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return False, "Formato de correo inválido."
        return True, ""
        
    def _validar_telefono(self, telefono):
        tel = "".join(filter(str.isdigit, str(telefono)))
        if len(tel) < 9:
            return False, "Teléfono inválido (menos de 9 dígitos)."
        return True, ""

    def validate_send(self, participante_id, canal, campana_tipo="C1"):
        """
        Valida si es seguro enviar una comunicación a un participante.
        canal: 'EMAIL' o 'SMS'
        campana_tipo: 'C1', 'C2', 'MJ'
        Retorna: (is_valid, reason)
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT nombre, apellido, email, telefono, estado, cc_nombre, c1, c2, maestria 
                FROM participantes WHERE id = ?
            ''', (participante_id,))
            px = cursor.fetchone()
            conn.close()
            
            if not px:
                self._log_bloqueo(participante_id, canal, "Participante no existe en DB.")
                return False, "Participante no encontrado."
                
            nombre, apellido, email, telefono, estado, cc_nombre, c1, c2, maestria = px
            
            # 1. Validar Identidad (Canal)
            if canal.upper() == 'EMAIL':
                valid, msg = self._validar_email(email)
                if not valid:
                    self._log_bloqueo(participante_id, canal, msg)
                    return False, msg
            elif canal.upper() == 'SMS':
                valid, msg = self._validar_telefono(telefono)
                if not valid:
                    self._log_bloqueo(participante_id, canal, msg)
                    return False, msg
            else:
                return False, "Canal desconocido."
                
            # 2. Validar Estado Desertor
            if estado and str(estado).strip().upper() == 'DESERTOR':
                self._log_bloqueo(participante_id, canal, "Participante es DESERTOR.")
                return False, "Estado DESERTOR no apto para campañas regulares."
                
            # 3. Validar Reglas de Negocio (Asignación)
            cc_clean = str(cc_nombre).strip() if cc_nombre else ""
            
            if campana_tipo in ['C1', 'C2']:
                if not any(allowed.lower() in cc_clean.lower() for allowed in self.allowed_cc_c1_c2):
                    motivo = f"CC '{cc_clean}' NO tiene permisos para enviar campañas {campana_tipo}."
                    self._log_bloqueo(participante_id, canal, motivo)
                    return False, motivo
                    
            elif campana_tipo == 'MJ':
                if not any(allowed.lower() in cc_clean.lower() for allowed in self.allowed_cc_mj):
                    motivo = f"CC '{cc_clean}' NO tiene permisos para enviar campañas MJ."
                    self._log_bloqueo(participante_id, canal, motivo)
                    return False, motivo
                    
            return True, "Validación exitosa."
            
        except Exception as e:
            self._log_bloqueo(participante_id, canal, f"Error interno Gatekeeper: {e}")
            return False, f"Error interno: {e}"

# PRUEBA RÁPIDA (Si se ejecuta directamente)
if __name__ == "__main__":
    gk = Gatekeeper()
    # Asume que el ID 1 existe en la BD
    valido, razon = gk.validate_send(participante_id=1, canal='EMAIL', campana_tipo='C1')
    print(f"Validación ID 1: {valido} -> {razon}")
