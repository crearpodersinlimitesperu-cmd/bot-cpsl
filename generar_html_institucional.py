import base64
from pathlib import Path

def generar_html_institucional_final():
    img_path = Path(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
    logo_base64 = base64.b64encode(img_path.read_bytes()).decode()
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800;900&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Montserrat', sans-serif; background-color: #050a14; margin: 0; padding: 0; -webkit-font-smoothing: antialiased; }}
            .wrapper {{ background-color: #050a14; padding: 40px 10px; }}
            .container {{ max-width: 650px; margin: 0 auto; background-color: #0a111e; border: 1px solid #1e293b; border-radius: 4px; overflow: hidden; box-shadow: 0 30px 60px rgba(0,0,0,0.6); }}
            .hero {{ background: linear-gradient(135deg, #1B5B9A 0%, #050a14 100%); padding: 60px 40px; text-align: center; border-bottom: 3px solid #D4AF37; }}
            .hero img {{ max-width: 230px; filter: brightness(0) invert(1); }}
            .content {{ padding: 50px; color: #e2e8f0; line-height: 1.6; font-size: 14px; }}
            .greeting {{ font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 20px; }}
            .highlight {{ color: #D4AF37; }}
            .section-divider {{ border: 0; height: 1px; background: linear-gradient(90deg, transparent, #D4AF37, transparent); margin: 40px 0; }}
            .section-title {{ font-size: 15px; font-weight: 900; color: #D4AF37; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 25px; text-align: center; }}
            .data-box {{ background-color: #111b2d; border: 1px solid #1e293b; padding: 30px; border-radius: 4px; }}
            .data-row {{ margin-bottom: 12px; display: flex; justify-content: space-between; }}
            .data-label {{ color: #64748b; font-weight: 700; text-transform: uppercase; font-size: 11px; }}
            .data-value {{ color: #ffffff; font-weight: 800; }}
            .footer {{ background-color: #050a14; color: #475569; padding: 50px; text-align: center; font-size: 11px; border-top: 1px solid #1e293b; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="hero">
                    <img src="data:image/png;base64,{logo_base64}" alt="CREAR GLOBAL">
                </div>
                <div class="content">
                    <div class="greeting">Hola, <span class="highlight">ROCÍO</span>:</div>
                    <p>Te damos oficialmente la bienvenida a la experiencia:</p>
                    <p style="font-size: 20px; font-weight: 900; color: #D4AF37; text-align: center; margin: 30px 0;">CAPÍTULO 1 — EQUIPO 28 | LIMA</p>
                    <p>Tu inscripción ha sido validada correctamente y tu participación se encuentra confirmada dentro del programa de entrenamiento de <b>CREACIÓN CUÁNTICA E.I.R.L.</b></p>
                    <div class="section-divider"></div>
                    <div class="section-title">DETALLE DE REGISTRO</div>
                    <div class="data-box">
                        <div class="data-row"><span class="data-label">Participante:</span><span class="data-value">ROCÍO</span></div>
                        <div class="data-row"><span class="data-label">Programa:</span><span class="data-value">Capítulo 1 — Equipo 28</span></div>
                        <div class="data-row"><span class="data-label">Estado:</span><span class="data-value" style="color: #10b981;">CONFIRMADA ✅</span></div>
                        <div class="data-row"><span class="data-label">Código:</span><span class="data-value">07938881</span></div>
                    </div>
                    <div class="section-divider"></div>
                    <div class="section-title">DOCUMENTACIÓN CONTRACTUAL</div>
                    <p>Adjunto a este correo encontrarás la versión oficial de los:</p>
                    <p style="text-align: center; font-weight: 700; color: #ffffff;">“Términos y Condiciones del Servicio — Programa Capítulo Uno”</p>
                    <p>Los cuales fueron aceptados y firmados digitalmente durante tu proceso de inscripción. La aceptación digital tiene plena validez conforme a la legislación vigente.</p>
                    <div class="section-divider"></div>
                    <div class="section-title">COMPROMISO DEL PARTICIPANTE</div>
                    <p>Capítulo 1 es una experiencia vivencial diseñada para personas comprometidas con su crecimiento, liderazgo y expansión personal. Tu puntualidad, apertura y responsabilidad serán fundamentales.</p>
                    <p style="text-align: center; font-weight: 800; color: #D4AF37; margin-top: 50px; font-size: 18px;">NOS HONRA ACOMPAÑARTE.</p>
                </div>
                <div class="footer">
                    <b>CREACIÓN CUÁNTICA E.I.R.L.</b><br>
                    RUC 20612592811<br>
                    LIMA — PERÚ<br><br>
                    © 2026 CREAR GLOBAL
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_institucional_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Institucional Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_institucional_final()
