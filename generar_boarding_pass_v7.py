import base64
from pathlib import Path
from datetime import datetime

def generar_html_boarding_pass_v7_final():
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
            .wrapper {{ background-color: #050a14; padding: 40px 10px; }}
            .container {{ max-width: 680px; margin: 0 auto; background-color: #0a111e; border: 1px solid #1e293b; border-radius: 4px; overflow: hidden; box-shadow: 0 50px 100px rgba(0,0,0,0.8); }}
            .hero {{ background: linear-gradient(135deg, #1B5B9A 0%, #050a14 100%); padding: 70px 40px; text-align: center; border-bottom: 4px solid #D4AF37; }}
            .hero img {{ max-width: 230px; filter: brightness(0) invert(1); }}
            .content {{ padding: 50px; line-height: 1.8; font-size: 14px; }}
            .greeting {{ font-size: 24px; font-weight: 800; color: #ffffff; margin-bottom: 25px; }}
            .highlight {{ color: #D4AF37; }}
            .divider {{ border: 0; height: 1px; background: linear-gradient(90deg, transparent, #D4AF37, transparent); margin: 50px 0; }}
            .boarding-pass {{ background-color: #111b2d; border: 1px dashed #D4AF37; padding: 40px; border-radius: 4px; }}
            .pass-title {{ font-size: 11px; font-weight: 900; color: #D4AF37; letter-spacing: 4px; text-transform: uppercase; margin-bottom: 30px; text-align: center; }}
            .pass-grid {{ display: flex; flex-wrap: wrap; }}
            .pass-item {{ width: 50%; margin-bottom: 20px; }}
            .pass-label {{ font-size: 9px; font-weight: 700; color: #64748b; text-transform: uppercase; letter-spacing: 1px; display: block; }}
            .pass-value {{ font-size: 13px; font-weight: 800; color: #ffffff; display: block; margin-top: 4px; }}
            .decision-box {{ background: linear-gradient(135deg, rgba(212, 175, 55, 0.05) 0%, transparent 100%); padding: 40px; border-radius: 4px; border-left: 3px solid #D4AF37; margin-top: 50px; }}
            .footer {{ background-color: #050a14; color: #475569; padding: 60px; text-align: center; font-size: 11px; border-top: 1px solid #1e293b; }}
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
                    <p>Le damos la bienvenida oficialmente a la experiencia <b>CAPÍTULO 1 — EQUIPO 28 | CREAR PODER SIN LÍMITES PERÚ</b>.</p>
                    <p>Su inscripción ha sido validada exitosamente y su participación ha quedado registrada en nuestro sistema interno de formación y gestión. Este correo constituye la confirmación formal de su acceso al programa.</p>
                    <div class="divider"></div>
                    <div class="boarding-pass">
                        <div class="pass-title">CONFIRMACIÓN DE INSCRIPCIÓN</div>
                        <div class="pass-grid">
                            <div class="pass-item"><span class="pass-label">Participante:</span><span class="pass-value">ROCÍO JARA AMPUERO</span></div>
                            <div class="pass-item"><span class="pass-label">DNI / Pasaporte:</span><span class="pass-value">07938881</span></div>
                            <div class="pass-item"><span class="pass-label">Equipo:</span><span class="pass-value">E28 — LIMA</span></div>
                            <div class="pass-item"><span class="pass-label">Estado Pago:</span><span class="pass-value" style="color: #10b981;">VALIDADO ✅</span></div>
                        </div>
                    </div>
                    <div class="decision-box">
                        <h3 class="highlight" style="font-size: 14px; margin-top: 0;">SOBRE SU DECISIÓN</h3>
                        <p style="margin-bottom: 0;">Miles de personas pasan años esperando “el momento correcto”. Muy pocas toman la decisión de avanzar. Hoy usted dio un paso distinto. Gracias por elegir una experiencia diseñada para personas dispuestas a elevar sus estándares, liderazgo y resultados.</p>
                    </div>
                    <p style="text-align: center; font-weight: 900; color: #ffffff; font-size: 18px; margin-top: 50px; letter-spacing: 4px;">NOS VEMOS EN CAPÍTULO 1.</p>
                </div>
                <div class="footer">
                    <b>CREACIÓN CUÁNTICA E.I.R.L. | RUC 20612592811</b><br>© 2026 CREAR GLOBAL — Todos los derechos reservados.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_boarding_pass_v7_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Boarding Pass v7 Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_boarding_pass_v7_final()
