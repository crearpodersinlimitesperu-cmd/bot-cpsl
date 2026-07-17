import base64
from pathlib import Path

def generar_html_global():
    img_path = Path(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
    logo_base64 = base64.b64encode(img_path.read_bytes()).decode()
    
    # Template con estilos de Crearglobal.com
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Montserrat', sans-serif; background-color: #f7f9fc; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.05); border: 1px solid #e1e8ed; }}
            .header {{ background-color: #1B5B9A; padding: 50px; text-align: center; border-bottom: 4px solid #D4AF37; }}
            .header img {{ max-width: 200px; height: auto; filter: brightness(0) invert(1); }}
            .content {{ padding: 45px; color: #2C3E50; line-height: 1.8; }}
            .greeting {{ font-size: 26px; font-weight: 800; color: #1B5B9A; margin-bottom: 25px; text-transform: uppercase; letter-spacing: -0.5px; }}
            .highlight {{ color: #D4AF37; }}
            .info-box {{ background-color: #f8fbff; border: 1px solid #d1e3f8; border-left: 5px solid #1E73BE; padding: 25px; margin: 35px 0; }}
            .info-title {{ font-weight: 700; font-size: 13px; color: #1B5B9A; text-transform: uppercase; margin-bottom: 15px; }}
            .footer {{ background-color: #1B5B9A; color: #ffffff; padding: 40px; text-align: center; font-size: 12px; border-top: 4px solid #D4AF37; }}
            .legal {{ font-size: 10px; color: #7f8c8d; line-height: 1.6; border-top: 1px solid #eee; padding-top: 25px; margin-top: 40px; }}
            .cta {{ display: inline-block; padding: 18px 35px; background-color: #1E73BE; color: #ffffff; text-decoration: none; border-radius: 2px; font-weight: 700; margin-top: 25px; text-transform: uppercase; font-size: 14px; letter-spacing: 1px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="data:image/png;base64,{logo_base64}" alt="Crear Global">
            </div>
            <div class="content">
                <div class="greeting">¡BIENVENIDA AL JUEGO, <span class="highlight">ROCIO</span>!</div>
                <p>Has tomado la decisión de no conformarte. Tu inscripción al <b>CAPÍTULO 1 — EQUIPO 28 LIMA</b> es una declaración de poder y coherencia con tu visión.</p>
                <div class="info-box">
                    <div class="info-title">Estatus de Inscripción</div>
                    <b>ENTRENAMIENTO:</b> Capítulo 1 — Equipo 28<br>
                    <b>PAGO:</b> <span style="color: #27ae60; font-weight: 700;">VALIDADO ✅</span><br>
                    <b>ID:</b> 07938881
                </div>
                <div style="text-align: center;">
                    <a href="https://crearglobal.com/" class="cta">ACCEDER AL PORTAL GLOBAL</a>
                </div>
                <div class="legal">
                    <b>AVISO LEGAL:</b> El pago es personal e intransferible. No tiene devolución.<br><br>
                    <b>RESPONSABILIDAD CIVIL:</b> El participante es responsable de cualquier daño. Renuncia a reclamos (Art. 11 Código Civil).
                </div>
            </div>
            <div class="footer">
                &copy; 2026 CREAR GLOBAL • LIMA
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_global_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Global generado en: {output_path}")

if __name__ == "__main__":
    generar_html_global()
