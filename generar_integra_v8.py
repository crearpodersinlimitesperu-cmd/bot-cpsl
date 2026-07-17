import base64
from pathlib import Path
from datetime import datetime

def generar_html_integro_v8_final():
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
            .section-separator {{ color: #D4AF37; margin: 30px 0; font-weight: bold; text-align: center; }}
            .highlight {{ color: #ffffff; font-weight: 800; }}
            .gold-text {{ color: #D4AF37; font-weight: 700; }}
            .bullet-list {{ list-style: none; padding-left: 0; }}
            .bullet-list li {{ margin-bottom: 10px; padding-left: 20px; position: relative; }}
            .bullet-list li::before {{ content: '•'; position: absolute; left: 0; color: #D4AF37; font-weight: bold; }}
            .check-list {{ list-style: none; padding-left: 0; }}
            .check-list li {{ margin-bottom: 10px; padding-left: 20px; position: relative; color: #10b981; font-weight: 700; }}
            .check-list li::before {{ content: '✓'; position: absolute; left: 0; color: #10b981; font-weight: bold; }}
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
                    <p>Estimado(a) <span class="highlight">ROCÍO JARA AMPUERO</span>,</p>
                    <p>Le damos la bienvenida oficialmente a la experiencia <b>CAPÍTULO 1 — EQUIPO 28 | CREAR PODER SIN LÍMITES PERÚ</b>.</p>
                    <p>Su inscripción ha sido validada exitosamente y su participación ha quedado registrada en nuestro sistema interno de formación y gestión. Este correo constituye la confirmación formal de su acceso al programa.</p>
                    <div class="section-separator">━━━━━━━━━━━━━━━━━━<br>CONFIRMACIÓN DE INSCRIPCIÓN<br>━━━━━━━━━━━━━━━━━━</div>
                    <p>
                        <b>Participante:</b> ROCÍO JARA AMPUERO<br>
                        <b>DNI / CE / Pasaporte:</b> 07938881<br>
                        <b>Código de Participante:</b> 07938881<br>
                        <b>Equipo:</b> E28<br>
                        <b>Ciudad:</b> Lima, Perú<br>
                        <b>Estado de Pago:</b> <span style="color: #10b981;">VALIDADO ✅</span><br>
                        <b>Fecha de Inscripción:</b> {fecha_actual}<br>
                        <b>Hora de Registro:</b> {hora_actual}
                    </p>
                    <div class="section-separator">━━━━━━━━━━━━━━━━━━<br>FECHAS Y HORARIOS DEL ENTRENAMIENTO<br>━━━━━━━━━━━━━━━━━━</div>
                    <p><b>CAPÍTULO 1 — ENTRENAMIENTO PRESENCIAL</b></p>
                    <p>Viernes: 9:00 AM a 10:00 PM aprox.<br>Sábado: 9:00 AM a 10:00 PM aprox.<br>Domingo: 9:00 AM a 10:00 PM aprox.</p>
                    <p><b>Importante:</b> La estructura del entrenamiento es progresiva y acumulativa. La participación completa y puntual en TODOS los segmentos es obligatoria.</p>
                    <p><b>No está permitido:</b></p>
                    <ul class="bullet-list">
                        <li>retirarse antes del cierre diario</li>
                        <li>faltar parcialmente a sesiones</li>
                        <li>ingresar tarde de manera reiterativa</li>
                        <li>ausentarse temporalmente durante dinámicas críticas</li>
                    </ul>
                    <div class="section-separator">━━━━━━━━━━━━━━━━━━<br>DOCUMENTACIÓN CONTRACTUAL<br>━━━━━━━━━━━━━━━━━━</div>
                    <p>Adjunto a este correo encontrará:</p>
                    <ul class="check-list">
                        <li>Contrato de Términos y Condiciones del Servicio</li>
                        <li>Declaración de aceptación digital personalizada</li>
                        <li>Registro de fecha y hora de aceptación</li>
                        <li>Condiciones de participación y continuidad</li>
                    </ul>
                    <div class="section-separator">━━━━━━━━━━━━━━━━━━<br>SOBRE SU DECISIÓN<br>━━━━━━━━━━━━━━━━━━</div>
                    <p>Miles de personas pasan años esperando “el momento correcto”. Muy pocas toman la decisión de avanzar. <span class="gold-text">Hoy usted dio un paso distinto.</span> Gracias por elegir una experiencia diseñada para personas dispuestas a elevar sus estándares, liderazgo y resultados.</p>
                </div>
                <div class="footer">
                    <b>CREAR PODER SIN LÍMITES PERÚ</b><br><b>CREACIÓN CUÁNTICA E.I.R.L.</b><br>RUC 20612592811<br><br>© 2026 CREAR GLOBAL — Todos los derechos reservados.
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    output_path = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\browser\bienvenida_rocio_integra_v8_final.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML Integra v8 Final generado en: {output_path}")

if __name__ == "__main__":
    generar_html_integro_v8_final()
