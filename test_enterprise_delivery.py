from crear_email_core import EmailEngine
from generar_contrato_pdf import generate_enterprise_contract
import os
from pathlib import Path

def validate_enterprise_system():
    print("--- CREAR GLOBAL ENTERPRISE VALIDATION ---")
    
    # 1. Initialize Engine (Debug Mode)
    engine = EmailEngine(debug=True)
    
    # 2. Mock Participant Data
    px_data = {
        "id": 123,
        "nombre": "JOSE SANCHEZ (TEST)",
        "documento": "07938881",
        "codigo_px": "E28-JS-999",
        "equipo": "E28",
        "email": "jose.sanchez@crearpsl.com"
    }
    
    # 3. Generate Legal Attachment
    contract_path = Path("test_institutional_contract.pdf")
    generate_enterprise_contract(px_data, contract_path)
    print(f"[OK] Legal contract generated: {contract_path}")
    
    # 4. Prepare Enterprise Template
    template_path = Path(__file__).parent / "templates" / "base_enterprise.html"
    
    content_html = f"""
    <p>Usted ha sido admitido formalmente en la red de entrenamiento de alto impacto de <b>CREAR GLOBAL</b>.</p>
    
    <div style="background-color: #f4f4f4; border-left: 4px solid #b49632; padding: 20px; margin: 20px 0;">
        <b style="color: #1a1a2e; text-transform: uppercase;">Detalles de Validación:</b><br/>
        Programa: Capítulo Uno — Equipo {px_data['equipo']}<br/>
        Código Institucional: {px_data['codigo_px']}<br/>
        Estado: <span style="color: #27ae60; font-weight: bold;">ADMITIDO</span>
    </div>
    
    <p>Adjunto encontrará su registro transaccional oficial y contrato de términos. Este documento es inmutable y forma parte de su expediente institucional.</p>
    
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center" style="padding: 20px 0;">
                <a href="https://crearglobal.com" style="background-color: #b49632; color: #ffffff; padding: 15px 30px; text-decoration: none; border-radius: 4px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Confirmar Asistencia</a>
            </td>
        </tr>
    </table>
    """
    
    placeholders = {
        "GREETING": f"BIENVENIDO A CREAR GLOBAL, {px_data['nombre'].split()[0]}",
        "CONTENT": content_html
    }
    
    try:
        final_html = engine.load_template(template_path, placeholders)
        
        # 5. Execute Enterprise Dispatch
        success, msg = engine.send_enterprise_email(
            to=px_data['email'],
            subject="CONFIRMACIÓN OFICIAL — Capítulo Uno | Equipo E28 Lima",
            body_html=final_html,
            attachments=[str(contract_path)],
            px_id=px_data['id']
        )
        
        if success:
            print(f"[SUCCESS] {msg}")
        else:
            print(f"[FAILED] {msg}")
            
    except Exception as e:
        print(f"[FATAL] {e}")
    finally:
        if contract_path.exists():
            os.remove(contract_path)

if __name__ == "__main__":
    validate_enterprise_system()
