from crear_email_core import EmailEngine
import os
from pathlib import Path

def test_standard_email():
    # Initialize engine (debug=True for simulation)
    engine = EmailEngine(debug=True)
    
    # Load standardized template
    template_path = Path(__file__).parent / "templates" / "base_standard.html"
    
    placeholders = {
        "GREETING": "¡HOLA, JOSE!",
        "CONTENT": """
            <p>Este es un correo de prueba del <b>Sistema Estandarizado de Comunicaciones CREAR</b>.</p>
            <p>Estamos validando que las plantillas, el motor de envío y la trazabilidad funcionen correctamente.</p>
            <div class="info-box">
                <b>ESTADO DEL SISTEMA:</b> <span style="color: #27ae60;">OPERATIVO ✅</span><br>
                <b>VERSIÓN:</b> 1.0.0 (Enterprise Core)<br>
                <b>MODO:</b> Depuración / Simulación
            </div>
            <a href="#" class="button">VALIDAR SISTEMA</a>
        """
    }
    
    try:
        html = engine.load_template(template_path, placeholders)
        
        # Send test email
        success, msg = engine.send_email(
            to="jose.sanchez@crearpsl.com",
            subject="Validación de Sistema de Comunicaciones Core",
            body_html=html,
            px_id=999 # Test ID
        )
        
        if success:
            print(f"[OK] Prueba exitosa: {msg}")
        else:
            print(f"[ERROR] Error en prueba: {msg}")
            
    except Exception as e:
        print(f"[FATAL] Error inesperado: {e}")

if __name__ == "__main__":
    test_standard_email()
