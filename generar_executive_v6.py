import base64
from pathlib import Path
from datetime import datetime

def generar_html_executive_v6_final():
    img_path = Path(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
    logo_base64 = base64.b64encode(img_path.read_bytes()).decode()
    
    fecha_actual = datetime.now().strftime("%d/%m/%Y")
    hora_actual = datetime.now().strftime("%H:%M:%S")
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Montserrat', sans-serif; background-color: #050a14; margin: 0; padding: 0; color: #e2e8f0; -webkit-font-smoothing: antialiased; }}
            .wrapper {{ background-color: #050a14; padding: 50px 10px; }}
            .container {{ max-width: 750px; margin: 0 auto; background-color: #0a111e; border: 1px solid #1e293b; border-radius: 4px; overflow: hidden; box-shadow: 0 50px 100px rgba(0,0,0,0.8); }}
            .hero {{ background: linear-gradient(135deg, #1B5B9A 0%, #050a14 100%); padding: 80px 40px; text-align: center; border-bottom: 4px solid #D4AF37; }}
            .hero img {{ max-width: 250px; filter: brightness(0) invert(1); }}
            .content {{ padding: 60px; line-height: 1.9; font-size: 14px; letter-spacing: 0.3px; }}
            .greeting {{ font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 30px; letter-spacing: 1px; }}
            .highlight {{ color: #D4AF37; }}
            .section-title {{ font-size: 13px; font-weight: 900; color: #D4AF37; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 35px; text-align: center; border-bottom: 1px solid #1e293b; padding-bottom: 15px; }}
            .data-grid {{ display: flex; flex-wrap: wrap; margin-bottom: 40px; }}
            .data-item {{ width: 50%; margin-bottom: 20px; }}
            .data-label {{ font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 2px; display: block; }}
            .data-value {{ font-size: 14px; font-weight: 800; color: #ffffff; display: block; margin-top: 5px; }}
            .info-card {{ background-color: #111b2d; border: 1px solid #1e293b; padding: 35px; border-radius: 4px; margin: 40px 0; text-align: center; }}
            .commitment-box {{ border: 1px solid #D4AF37; padding: 40px; margin-top: 60px; text-align: center; background: rgba(212, 175, 55, 0.03); }}
            .footer {{ background-color: #050a14; color: #475569; padding: 80px; text-align: center; font-size: 11px; border-top: 1px solid #1e293b; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="hero">
                    <img src="data:image/png;base64,{logo_base64}" alt="CREAR GLOBAL">
                </div>
                <div class="content">
                    <div class="greeting">Estimado(a) <span class="highlight">ROCÍO JARA AMPUERO</span>:</div>
                    <p>Bienvenido(a) a una experiencia diseñada para personas que decidieron dejar de observar su vida desde afuera y comenzar a liderarla desde un nuevo nivel de compromiso, presencia y acción.</p>
                    <p>Tu inscripción al programa <b>CAPÍTULO 1 — EQUIPO 28</b> ha sido oficialmente confirmada por <b>CREACIÓN CUÁNTICA E.I.R.L.</b></p>
                    <div class="section-title">CONFIRMACIÓN DE INSCRIPCIÓN</div>
                    <div class="data-grid">
                        <div class="data-item"><span class="data-label">Participante:</span><span class="data-value">ROCÍO JARA AMPUERO</span></div>
                        <div class="data-item"><span class="data-label">Documento:</span><span class="data-value">07938881</span></div>
                        <div class="data-item"><span class="data-label">ID Participante:</span><span class="data-value">IMO-07938881</span></div>
                        <div class="data-item"><span class="data-label">Equipo:</span><span class="data-value">E28 — LIMA</span></div>
                    </div>
                    <div class="info-card">
                        <span class="data-label">FECHAS Y HORARIOS OFICIALES</span>
                        <div style="font-size: 16px; font-weight: 800; color: #ffffff; margin-top: 10px;">15, 16 y 17 de MAYO</div>
                        <div style="color: #D4AF37; font-size: 13px;">09:00 a.m. — 10:00 p.m.</div>
                    </div>
                    <div class="commitment-box">
                        <div style="font-size: 18px; font-weight: 900; color: #D4AF37; letter-spacing: 3px; margin-bottom: 20px;">DECLARACIÓN DE COMPROMISO</div>
                        <p>No has ingresado únicamente a un evento. Has ingresado a un espacio diseñado para desafiar límites, elevar estándares y transformar resultados.</p>
                        <p style="font-weight: 900; color: #ffffff; font-size: 18px; margin-top: 30px; letter-spacing: 4px;">BIENVENIDO(A) A CREAR.</p>
                    </div>
                </div>
                <div class="footer">
                    <b>CREACIÓN CUÁNTICA E.I.R.L. | RUC 20612592811</b><br>© 2026 Todos los derechos reservados.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_executive_v6_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Executive v6 Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_executive_v6_final()
