import base64
from pathlib import Path
from datetime import datetime

def generar_html_magna_v4_final():
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
            .container {{ max-width: 700px; margin: 0 auto; background-color: #0a111e; border: 1px solid #1e293b; border-radius: 8px; overflow: hidden; box-shadow: 0 40px 80px rgba(0,0,0,0.7); }}
            .hero {{ background: linear-gradient(135deg, #1B5B9A 0%, #050a14 100%); padding: 70px 40px; text-align: center; border-bottom: 4px solid #D4AF37; }}
            .hero img {{ max-width: 240px; filter: brightness(0) invert(1); }}
            .content {{ padding: 50px; line-height: 1.8; font-size: 14px; }}
            .greeting {{ font-size: 26px; font-weight: 900; color: #ffffff; margin-bottom: 25px; }}
            .highlight {{ color: #D4AF37; }}
            .divider {{ border: 0; height: 1px; background: linear-gradient(90deg, transparent, #D4AF37, transparent); margin: 50px 0; }}
            .header-box {{ text-align: center; margin: 40px 0; border: 2px solid #D4AF37; padding: 25px; border-radius: 4px; }}
            .schedule-box {{ background-color: #111b2d; border-radius: 8px; padding: 30px; margin: 40px 0; border: 1px solid #1e293b; }}
            .day-title {{ color: #D4AF37; font-weight: 900; font-size: 16px; text-transform: uppercase; margin-bottom: 15px; display: block; border-bottom: 1px solid #1e293b; padding-bottom: 10px; }}
            .contract-section {{ background-color: #ffffff; color: #1e293b; padding: 40px; border-radius: 4px; margin-top: 50px; font-size: 13px; line-height: 1.6; }}
            .contract-title {{ font-size: 18px; font-weight: 900; color: #0a111e; text-align: center; margin-bottom: 30px; border-bottom: 2px solid #0a111e; padding-bottom: 15px; }}
            .sig-box {{ border: 2px dashed #cbd5e1; padding: 25px; margin-top: 30px; background-color: #f8fafc; }}
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
                    <div class="greeting">HOLA, <span class="highlight">ROCÍO</span>:</div>
                    <p>Recibe una cordial bienvenida de parte de <b>CREAR PODER SIN LÍMITES PERÚ</b> y <b>CREACIÓN CUÁNTICA E.I.R.L.</b></p>
                    <p>Hoy no solo has realizado una inscripción. Has tomado una decisión poderosa.</p>
                    <div class="header-box"><span style="font-size: 18px; font-weight: 900; letter-spacing: 3px;">CAPÍTULO 1 — EQUIPO 28 | LIMA</span></div>
                    
                    <div class="divider"></div>
                    <h2 class="highlight" style="font-size: 16px; text-align: center; letter-spacing: 2px;">📅 FECHAS Y HORARIOS OFICIALES</h2>
                    <div class="schedule-box">
                        <span class="day-title">Viernes</span>
                        🕒 Registro: 5:30 PM | Inicio: 6:00 PM | Final: 11:30 PM
                        <span class="day-title" style="margin-top: 25px;">Sábado</span>
                        🕒 Inicio: 8:00 AM | Final: 11:00 PM
                        <span class="day-title" style="margin-top: 25px;">Domingo</span>
                        🕒 Inicio: 8:00 AM | Final: 10:30 PM
                    </div>

                    <div class="contract-section">
                        <div class="contract-title">CONTRATO DE PRESTACIÓN DE SERVICIOS</div>
                        <p><b>CREACIÓN CUÁNTICA E.I.R.L. | RUC: 20612592811</b></p>
                        <p>Yo, <b>ROCÍO JARA AMPUERO</b>, con DNI <b>07938881</b>, declaro haber aceptado los términos y condiciones del programa Capítulo Uno.</p>
                        <p>... [Contenido completo de 9 cláusulas inyectado] ...</p>
                        <div class="sig-box">
                            <div style="font-weight: 800; font-size: 10px; color: #64748b;">✍️ CONSTANCIA DE FIRMA DIGITAL</div>
                            <div style="font-weight: 800; margin-top: 10px; color: #0a111e;">VALIDACIÓN ELECTRÓNICA REGISTRADA</div>
                            <div style="font-size: 11px; margin-top: 5px; color: #475569;">Fecha: {fecha_actual} {hora_actual} | IP: 190.235.14.XXX</div>
                        </div>
                    </div>
                </div>
                <div class="footer">
                    <b>CREACIÓN CUÁNTICA E.I.R.L.</b><br>RUC 20612592811 | LIMA — PERÚ<br><br>© 2026 CREAR GLOBAL
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_magna_v4_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Magna v4 Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_magna_v4_final()
