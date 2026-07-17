import base64
from pathlib import Path

def corregir_logo_premium_pro():
    img_path = Path(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
    logo_base64 = base64.b64encode(img_path.read_bytes()).decode()
    
    # Template Premium Pro con Logo Inyectado (Indestructible)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700;800;900&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Montserrat', sans-serif; background-color: #050a14; margin: 0; padding: 0; }}
            .wrapper {{ background-color: #050a14; padding: 40px 10px; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #0a111e; border: 1px solid #1e293b; border-radius: 12px; overflow: hidden; }}
            .hero {{ background: linear-gradient(135deg, #1B5B9A 0%, #0a111e 100%); padding: 60px 40px; text-align: center; border-bottom: 2px solid #D4AF37; }}
            .hero img {{ max-width: 220px; height: auto; filter: brightness(0) invert(1); }}
            .content {{ padding: 50px; color: #e2e8f0; line-height: 1.8; }}
            .greeting {{ font-size: 28px; font-weight: 900; color: #ffffff; margin-bottom: 25px; text-transform: uppercase; }}
            .highlight {{ background: linear-gradient(90deg, #D4AF37, #f7dc6f); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 900; }}
            .pass-card {{ background-color: #111b2d; border-left: 5px solid #D4AF37; padding: 30px; margin: 40px 0; border-radius: 8px; }}
            .footer {{ background-color: #050a14; color: #475569; padding: 50px; text-align: center; font-size: 11px; }}
            .legal {{ font-size: 10px; color: #334155; line-height: 1.5; text-align: justify; margin-top: 40px; }}
            .cta-button {{ display: inline-block; padding: 20px 45px; background: linear-gradient(90deg, #D4AF37, #f1c40f); color: #000000; text-decoration: none; border-radius: 4px; font-weight: 900; font-size: 14px; text-transform: uppercase; }}
        </style>
    </head>
    <body>
        <div class="wrapper">
            <div class="container">
                <div class="hero">
                    <!-- Logo Inyectado (No depende de enlaces externos) -->
                    <img src="data:image/png;base64,{logo_base64}" alt="Crear Global Official">
                </div>
                <div class="content">
                    <div class="greeting">HOLA, <span class="highlight">ROCIO</span>:</div>
                    <p>Has tomado la decisión de no conformarte. Tu inscripción al <b>Capítulo Uno — Equipo 28 Lima</b> es una declaración absoluta de poder y coherencia con la visión que tienes para tu vida.</p>
                    <div class="pass-card">
                        <b>📌 ENTRENAMIENTO:</b> CAPÍTULO UNO – EQUIPO 28<br>
                        <b>📍 SEDE:</b> LIMA, PERÚ<br>
                        <b>⚡ ESTADO:</b> <span style="color: #10b981;">PAGO VALIDADO ✅</span>
                    </div>
                    <div style="text-align: center;">
                        <a href="https://crearglobal.com/" class="cta-button">ACCESO AL PORTAL DE PODER</a>
                    </div>
                    <p style="text-align: center; font-weight: 800; color: #D4AF37; margin-top: 40px; font-size: 20px;">NOS VEMOS EN LA ARENA.</p>
                    <div class="legal">
                        <b>AVISOS LEGALES Y ACUERDOS INNEGOCIABLES:</b><br>
                        • <b>COMPROMISO FINANCIERO:</b> El pago es personal e intransferible y no está sujeto a devolución.<br>
                        • <b>RESPONSABILIDAD CIVIL:</b> El participante es responsable de su bienestar. Renuncia a reclamos (Art. 11 del Código Civil peruano).
                    </div>
                </div>
                <div class="footer">
                    © 2026 CREAR GLOBAL • LIMA PERÚ
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_premium_pro_fixed.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Premium Pro corregido en: {output_path}")

if __name__ == "__main__":
    corregir_logo_premium_pro()
