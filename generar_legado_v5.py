import base64
from pathlib import Path
from datetime import datetime

def generar_html_legado_v5_final():
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
            .greeting {{ font-size: 24px; font-weight: 900; color: #ffffff; margin-bottom: 15px; }}
            .highlight {{ color: #D4AF37; }}
            .section-divider {{ border: 0; height: 1px; background: linear-gradient(90deg, transparent, #D4AF37, transparent); margin: 40px 0; }}
            .section-title {{ font-size: 14px; font-weight: 900; color: #D4AF37; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 25px; text-align: center; }}
            .data-box {{ background-color: #111b2d; border: 1px solid #1e293b; padding: 30px; border-radius: 4px; }}
            .data-row {{ margin-bottom: 10px; display: flex; justify-content: space-between; }}
            .data-label {{ color: #64748b; font-weight: 700; font-size: 11px; text-transform: uppercase; }}
            .data-value {{ color: #ffffff; font-weight: 800; }}
            .important-box {{ background-color: #fef2f2; border-left: 5px solid #ef4444; padding: 25px; margin: 30px 0; color: #1e293b; font-size: 13px; }}
            .schedule-row {{ background-color: #111b2d; padding: 15px 25px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #1e293b; display: flex; justify-content: space-between; align-items: center; }}
            .footer {{ background-color: #050a14; color: #475569; padding: 60px; text-align: center; font-size: 11px; border-top: 1px solid #1e293b; }}
            .legal-tag {{ color: #10b981; font-weight: 800; font-size: 10px; border: 1px solid #10b981; padding: 2px 8px; border-radius: 20px; }}
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
                    <p>Reciba una cordial bienvenida a la experiencia oficial de:</p>
                    <p style="font-size: 18px; font-weight: 900; color: #ffffff; text-align: center; margin: 30px 0; letter-spacing: 2px;">CREAR PODER SIN LÍMITES PERÚ<br><span style="font-size: 13px; color: #D4AF37; letter-spacing: 4px;">CAPÍTULO 1 — EQUIPO 28 | LIMA</span></p>
                    
                    <div class="section-divider"></div>
                    <div class="section-title">DETALLE DE INSCRIPCIÓN</div>
                    <div class="data-box">
                        <div class="data-row"><span class="data-label">Participante:</span><span class="data-value">ROCÍO JARA AMPUERO</span></div>
                        <div class="data-row"><span class="data-label">Documento:</span><span class="data-value">07938881</span></div>
                        <div class="data-row"><span class="data-label">ID Participación:</span><span class="data-value">IMO-07938881</span></div>
                        <div class="data-row"><span class="data-label">Estado:</span><span class="data-value" style="color: #10b981;">VALIDADA ✅</span></div>
                    </div>

                    <div class="section-divider"></div>
                    <div class="section-title">FECHAS Y HORARIOS OFICIALES</div>
                    <div class="schedule-row"><span>Viernes:</span><b>09:00 a.m. — 10:00 p.m. aprox.</b></div>
                    <div class="schedule-row"><span>Sábado:</span><b>09:00 a.m. — 10:00 p.m. aprox.</b></div>
                    <div class="schedule-row"><span>Domingo:</span><b>09:00 a.m. — 10:00 p.m. aprox.</b></div>

                    <div class="important-box">
                        <b>IMPORTANTE:</b> La participación requiere asistencia completa, puntual y continua. No está permitido ausentarse de ningún segmento.
                    </div>

                    <div class="section-divider"></div>
                    <div class="section-title">VALIDACIÓN DIGITAL DEL CONTRATO</div>
                    <div class="data-box" style="border-left: 5px solid #10b981;">
                        <div class="data-row"><span class="data-label">Fecha Aceptación:</span><span class="data-value">{fecha_actual} {hora_actual}</span></div>
                        <div class="data-row"><span class="data-label">IP Registro:</span><span class="data-value">190.235.14.XXX</span></div>
                        <div class="data-row"><span class="data-label">Sistema:</span><span class="data-value">IMO — Plataforma Oficial</span></div>
                        <div class="data-row"><span class="data-label">Estado Contractual:</span><span class="legal-tag">ACEPTADO DIGITALMENTE ✅</span></div>
                    </div>
                </div>
                <div class="footer">
                    <b>CREACIÓN CUÁNTICA E.I.R.L. | RUC 20612592811</b><br>CREAR PODER SIN LÍMITES PERÚ<br><br>© 2026 Todos los derechos reservados.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_legado_v5_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Legado v5 Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_legado_v5_final()
