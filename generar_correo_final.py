import base64
from pathlib import Path

def generar_html_final():
    img_path = Path(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
    logo_base64 = base64.b64encode(img_path.read_bytes()).decode()
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; }}
            .container {{ max-width: 600px; margin: 20px auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            .header {{ background-color: #000000; padding: 40px; text-align: center; }}
            .header img {{ max-width: 180px; height: auto; }}
            .content {{ padding: 40px; color: #333333; line-height: 1.6; }}
            .greeting {{ font-size: 24px; font-weight: bold; color: #000000; margin-bottom: 20px; text-transform: uppercase; }}
            .highlight {{ color: #d4af37; font-weight: bold; }}
            .info-box {{ background-color: #f9f9f9; border-left: 4px solid #d4af37; padding: 20px; margin: 30px 0; }}
            .footer {{ background-color: #000000; color: #ffffff; padding: 30px; text-align: center; font-size: 12px; }}
            .legal {{ font-size: 10px; color: #888; border-top: 1px solid #eee; padding-top: 20px; margin-top: 30px; }}
            .cta {{ display: inline-block; padding: 15px 30px; background-color: #d4af37; color: #ffffff; text-decoration: none; border-radius: 50px; font-weight: bold; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="data:image/png;base64,{logo_base64}" alt="Crear Poder Sin Límites">
            </div>
            <div class="content">
                <div class="greeting">¡BIENVENIDA AL JUEGO, <span class="highlight">ROCIO</span>!</div>
                <p>Has tomado la decisión de no conformarte. Tu inscripción al <b>CAPÍTULO 1 — EQUIPO 28 LIMA</b> es el primer paso hacia una versión tuya que aún no has conocido.</p>
                <div class="info-box">
                    <b>ENTRENAMIENTO:</b> Capítulo 1 — Equipo 28<br>
                    <b>ESTADO DE PAGO:</b> <span style="color: #27ae60;">VALIDADO ✅</span><br>
                    <b>ID:</b> 07938881
                </div>
                <a href="#" class="cta">RECLAMA TU LUGAR CON PODER</a>
                <div class="legal">
                    <b>PAGO PERSONAL E INTRANSFERIBLE:</b> El pago realizado es personal e intransferible. No tiene devolución salvo lo establecido por ley.<br><br>
                    <b>RESPONSABILIDAD CIVIL:</b> El participante reconoce que es responsable de cualquier daño causado a sí mismo o a terceros. Renuncia a reclamos ante autoridad competente (Art. 11 Código Civil).
                </div>
            </div>
            <div class="footer">
                &copy; 2026 CREAR PODER SIN LÍMITES PERÚ
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML generado en: {output_path}")

if __name__ == "__main__":
    generar_html_final()
