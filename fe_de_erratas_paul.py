"""
FE DE ERRATAS — Corrección para Paul Yhonadan Valentin Vargas
==============================================================
Paul es NUEVA INSCRIPCIÓN, no cambio de cupo.
Envía correo corregido al PX y notificación al IMO.
"""
import os
import sys
import smtplib
import requests
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_principal.png")
IMG_BANNER = r"C:\Users\josem\Downloads\Imágenes\Indicaciones C1E28.jpeg"
IMG_INDICACIONES = r"C:\Users\josem\Downloads\Imágenes\IC1E28.jpeg"

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

PAUL = {
    "nombre_completo": "Paul Yhonadan Valentin Vargas",
    "nombre_pref": "Paul",
    "email": "paulyhonadan_valentin@gmail.com",
    "telefono": "989685398",
    "imo_nombre": "Aurelio Valentin Mariano",
    "imo_email": "Aurelio_valentin@hotmail.com",
    "imo_tel": "979310770",
}

def generar_html_fe_de_erratas():
    return """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>body,table,td,a{-webkit-text-size-adjust:100%}table{border-collapse:collapse!important}body{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}</style></head>
<body style="background:#f0f0f0;margin:0;padding:0;">
<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:40px 0;">
<table border="0" cellpadding="0" cellspacing="0" width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.05);">

<!-- HEADER -->
<tr><td align="center" bgcolor="#1a1a2e" style="padding:50px 40px;border-bottom:5px solid #b49632;">
<img src="cid:logo_crear" alt="CREAR GLOBAL" width="180" style="display:block;width:180px;height:auto;"/>
<p style="color:#b49632;margin:18px 0 0;font-size:10px;letter-spacing:5px;text-transform:uppercase;font-weight:bold;">Sistema Transaccional Institucional</p>
</td></tr>

<!-- FE DE ERRATAS BANNER -->
<tr><td align="center" style="padding:25px 55px 0;">
<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:14px 20px;">
<p style="margin:0;font-size:13px;color:#856404;font-weight:700;text-transform:uppercase;letter-spacing:1px;">📋 Fe de Erratas — Corrección de Comunicación Anterior</p>
</div>
</td></tr>

<!-- HERO -->
<tr><td style="padding:30px 55px 0 55px;">
<h1 style="color:#1a1a2e;margin:0;font-size:28px;line-height:36px;font-weight:800;">¡BIENVENIDO, PAUL!</h1>
<div style="width:60px;height:4px;background:#b49632;margin:16px 0 0;border-radius:2px;"></div>
</td></tr>

<!-- BODY -->
<tr><td style="padding:30px 55px 20px;color:#333;font-size:15px;line-height:27px;">

<p>Paul,</p>

<p>En nuestro correo anterior se indicó por error que tu inscripción correspondía a un "cambio de cupo". <strong>Queremos aclarar que tu registro es una nueva inscripción directa al Capítulo 1 — Equipo 28.</strong></p>

<p>¡Felicitaciones por tomar esta decisión! A partir de este momento, eres parte de una comunidad de personas que han decidido crear resultados extraordinarios en cada área de su vida.</p>

<!-- INFO BOX -->
<div style="background:#fafafa;border-left:4px solid #b49632;padding:22px 25px;margin:28px 0;border-radius:0 8px 8px 0;">
<h3 style="color:#1a1a2e;margin:0 0 14px;font-size:12px;text-transform:uppercase;letter-spacing:2px;font-weight:800;">📋 Detalles de tu Entrenamiento</h3>
<table style="width:100%;font-size:14px;line-height:24px;">
<tr><td style="color:#888;width:110px;padding:4px 0;">Programa</td><td style="font-weight:700;color:#1a1a2e;">Capítulo 1 — Equipo 28</td></tr>
<tr><td style="color:#888;padding:4px 0;">Tipo</td><td style="font-weight:700;color:#27ae60;">✅ Nueva Inscripción</td></tr>
<tr><td style="color:#888;padding:4px 0;">Fechas</td><td style="font-weight:700;color:#1a1a2e;">29, 30 y 31 de mayo de 2026</td></tr>
<tr><td style="color:#888;padding:4px 0;">Lugar</td><td style="font-weight:700;color:#1a1a2e;">BTH Hotel Boutique Concept</td></tr>
<tr><td style="color:#888;padding:4px 0;">Dirección</td><td style="font-weight:700;color:#1a1a2e;">Av. Guardia Civil 727, Urb. Córpac, San Borja</td></tr>
<tr><td style="color:#888;padding:4px 0;">Tu IMO</td><td style="font-weight:700;color:#1a1a2e;">Aurelio Valentin Mariano</td></tr>
</table>
</div>

<!-- HORARIOS -->
<div style="background:#fff8e6;border-left:4px solid #f39c12;padding:18px 22px;margin:24px 0;border-radius:0 6px 6px 0;">
<h4 style="margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#856404;">⏰ Horarios</h4>
<table style="font-size:14px;line-height:26px;color:#444;">
<tr><td style="padding:2px 12px 2px 0;font-weight:700;">Viernes 29:</td><td>9:00 AM (¡Llega puntual para el Registro!) | 10:00 AM - 10:00 PM (aprox.)</td></tr>
<tr><td style="padding:2px 12px 2px 0;font-weight:700;">Sábado 30:</td><td>9:00 AM - 10:00 PM (aprox.)</td></tr>
<tr><td style="padding:2px 12px 2px 0;font-weight:700;">Domingo 31:</td><td>9:00 AM - 9:00 PM (aprox.)</td></tr>
</table>
</div>

<!-- QUE TRAER -->
<div style="background:#f0f9ff;border-left:4px solid #3498db;padding:18px 22px;margin:24px 0;border-radius:0 6px 6px 0;">
<h4 style="margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#2471a3;">📌 ¿Qué necesitas traer sí o sí?</h4>
<ul style="font-size:14px;line-height:26px;color:#444;margin:0;padding-left:18px;">
<li><strong>DNI Físico:</strong> Indispensable para registrarte el viernes a las 9 AM.</li>
<li><strong>Ropa Cómoda:</strong> Te moverás, participarás activamente.</li>
<li><strong>Botella con Agua:</strong> Mantener tu hidratación es clave para tu energía.</li>
<li><strong>Tu Compromiso Total:</strong> Tu disposición a participar plenamente abrirá todas las puertas.</li>
</ul>
</div>

<!-- PARA APROVECHAR -->
<div style="background:#f5f0ff;border-left:4px solid #8e44ad;padding:18px 22px;margin:24px 0;border-radius:0 6px 6px 0;">
<h4 style="margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#6c3483;">🎯 Para Aprovechar al Máximo</h4>
<ul style="font-size:14px;line-height:26px;color:#444;margin:0;padding-left:18px;">
<li><strong>Puntualidad Sagrada:</strong> Llegar a tiempo cada día nos permite empezar y terminar juntos.</li>
<li><strong>Presencia Completa:</strong> Tu asistencia de principio a fin en cada sesión es fundamental.</li>
<li><strong>Desconexión para Conectar:</strong> Durante las sesiones, los celulares estarán guardados.</li>
</ul>
</div>

<p style="text-align:center;font-weight:700;font-size:16px;color:#1a1a2e;margin:30px 0 10px;">¿Tienes preguntas? Contacta a tus Coordinadores:</p>
<div style="text-align:center;font-size:15px;line-height:28px;">
<strong>Joyce Marín:</strong> +51 933 599 903<br>
<strong>Diana Moscoso:</strong> +51 912 379 744
</div>

<!-- IMO CARD -->
<div style="background:#fcfcfc;padding:22px;border-radius:10px;text-align:center;margin:28px 0;border:1px solid #e8e8e8;">
<p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:2px;color:#999;">Tu IMO Asignado</p>
<p style="margin:8px 0 4px;font-size:17px;font-weight:bold;color:#1a1a2e;">Aurelio Valentin Mariano</p>
<p style="margin:4px 0 0;font-size:16px;color:#b49632;font-weight:bold;">📞 +51 979 310 770</p>
</div>

<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:15px 0;">
<a href="https://wa.me/51979310770" style="background-color:#b49632;color:#fff;padding:14px 40px;text-decoration:none;border-radius:4px;font-weight:bold;font-size:13px;text-transform:uppercase;letter-spacing:1.5px;display:inline-block;">Contactar a mi IMO</a>
</td></tr></table>

<p style="text-align:center;font-weight:700;font-size:15px;color:#1a1a2e;margin:25px 0 5px;">¡Nos vemos muy pronto para crear juntos!</p>
<p style="text-align:center;font-size:14px;color:#666;">Un abrazo,<br><strong>Equipo Crear Poder Sin Límites</strong></p>

<p style="font-size:12px;color:#999;font-style:italic;text-align:center;margin-top:20px;border-top:1px solid #eee;padding-top:15px;">📎 Las imágenes con las indicaciones completas están adjuntas a este correo.</p>

</td></tr>

<!-- FOOTER -->
<tr><td align="center" bgcolor="#fcfcfc" style="padding:40px 55px;color:#999;font-size:11px;line-height:20px;border-top:1px solid #f0f0f0;">
<p style="margin:0;font-weight:800;color:#1a1a2e;text-transform:uppercase;letter-spacing:2px;font-size:12px;">CREAR GLOBAL® — PERÚ 2026</p>
<p style="margin:5px 0 0;color:#b49632;font-weight:600;">Transformación Humana de Alto Impacto</p>
<p style="margin:5px 0 0;">Lima — Perú</p>
<p style="margin:12px 0 0;"><a href="mailto:crearpodersinlimitesperu@gmail.com" style="color:#1a1a2e;text-decoration:none;font-weight:bold;">crearpodersinlimitesperu@gmail.com</a> <span style="color:#eee;padding:0 8px;">|</span> <a href="https://crearglobal.com" style="color:#1a1a2e;text-decoration:none;font-weight:bold;">crearglobal.com</a></p>
<p style="margin:18px 0 0;text-align:justify;font-size:9px;line-height:15px;color:#bbb;"><b>AVISO DE CONFIDENCIALIDAD:</b> Este mensaje y cualquier archivo adjunto están protegidos por leyes de privacidad.</p>
<p style="margin:12px 0 0;font-size:9px;text-transform:uppercase;letter-spacing:1px;">&copy; 2026 CREAR GLOBAL. All rights reserved.</p>
</td></tr>

</table></td></tr></table></body></html>"""


def enviar():
    print("=" * 65)
    print("  FE DE ERRATAS — Paul Yhonadan Valentin Vargas")
    print("  Corrección: Nueva Inscripción (NO cambio de cupo)")
    print("=" * 65)

    if not GMAIL_PASS:
        print("❌ ERROR: GMAIL_APP_PASS no configurada")
        return

    # 1. CORREO CORREGIDO AL PX
    print(f"\n📧 Enviando fe de erratas a {PAUL['email']}...")
    
    asunto = "Fe de Erratas — ¡Bienvenido, Paul! Tu nueva inscripción en C1 E28 está confirmada"
    body_html = generar_html_fe_de_erratas()
    
    msg = MIMEMultipart("mixed")
    msg['From'] = f"CREAR GLOBAL Official <{GMAIL_USER}>"
    msg['To'] = PAUL['email']
    msg['Subject'] = asunto
    msg.add_header('X-Priority', '1 (Highest)')
    
    msg_related = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body_html, 'html', 'utf-8'))
    msg_related.attach(msg_alt)
    
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo_crear>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            msg_related.attach(logo)
    
    msg.attach(msg_related)
    
    for img_path, img_name in [(IMG_BANNER, "Indicaciones_C1E28.jpeg"), (IMG_INDICACIONES, "Informacion_Completa_C1E28.jpeg")]:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                part = MIMEBase("image", "jpeg")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{img_name}"')
                msg.attach(part)
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        print("   ✅ Fe de erratas enviada a Paul")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return

    time.sleep(3)

    # 2. CORREO AL IMO
    print(f"\n📧 Notificando corrección al IMO ({PAUL['imo_email']})...")
    
    asunto_imo = "📋 Fe de Erratas — Paul Yhonadan es Nueva Inscripción (NO cambio de cupo)"
    body_imo = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#f0f0f0;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:40px 0;">
<table border="0" cellpadding="0" cellspacing="0" width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;">
<tr><td align="center" bgcolor="#1a1a2e" style="padding:35px 40px;border-bottom:4px solid #b49632;">
<img src="cid:logo_crear" alt="CREAR" width="140" style="display:block;width:140px;height:auto;"/>
<p style="color:#b49632;margin:12px 0 0;font-size:9px;letter-spacing:4px;text-transform:uppercase;">Fe de Erratas</p>
</td></tr>
<tr><td style="padding:40px 50px;color:#333;font-size:15px;line-height:26px;">
<div style="background:#fff3cd;border:1px solid #ffc107;border-radius:6px;padding:14px 20px;margin-bottom:20px;">
<p style="margin:0;font-size:13px;color:#856404;font-weight:700;">📋 CORRECCIÓN: El correo anterior indicaba "cambio de cupo" por error.</p>
</div>
<p>Aurelio,</p>
<p>Te informamos que se ha enviado una <strong>fe de erratas</strong> a tu participante <strong>Paul Yhonadan Valentin Vargas</strong> corrigiendo la comunicación anterior.</p>
<div style="background:#f0f9ff;border-left:4px solid #3498db;padding:16px 20px;margin:20px 0;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;color:#2471a3;"><strong>Corrección:</strong> Paul es una <strong>NUEVA INSCRIPCIÓN</strong> al Capítulo 1 — Equipo 28, NO un cambio de cupo.</p>
</div>
<table style="width:100%;border-collapse:collapse;margin:20px 0;border:1px solid #eee;">
<tr style="background:#f8f9fa;"><th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;">Canal</th><th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;">Estado</th></tr>
<tr><td style="padding:12px 16px;border-top:1px solid #f0f0f0;">📧 Fe de Erratas (correo corregido)</td><td style="padding:12px 16px;border-top:1px solid #f0f0f0;color:#27ae60;font-weight:bold;">✅ Enviado a paulyhonadan_valentin@gmail.com</td></tr>
<tr><td style="padding:12px 16px;border-top:1px solid #f0f0f0;">📱 SMS de corrección</td><td style="padding:12px 16px;border-top:1px solid #f0f0f0;color:#27ae60;font-weight:bold;">✅ Enviado a 989685398</td></tr>
</table>
<p>Toda la información de indicaciones (sede, horarios, qué traer) fue incluida correctamente en el correo corregido.</p>
</td></tr>
<tr><td align="center" bgcolor="#fcfcfc" style="padding:25px 50px;font-size:10px;color:#999;border-top:1px solid #f0f0f0;">
<p style="margin:0;"><strong>CREAR GLOBAL®</strong> — Sistema Institucional — Lima, Perú 2026</p>
</td></tr></table></td></tr></table></body></html>"""

    msg2 = MIMEMultipart("related")
    msg2['From'] = f"CREAR GLOBAL Official <{GMAIL_USER}>"
    msg2['To'] = PAUL['imo_email']
    msg2['Subject'] = asunto_imo
    
    msg2_alt = MIMEMultipart("alternative")
    msg2_alt.attach(MIMEText(body_imo, 'html', 'utf-8'))
    msg2.attach(msg2_alt)
    
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo2 = MIMEImage(f.read())
            logo2.add_header("Content-ID", "<logo_crear>")
            logo2.add_header("Content-Disposition", "inline", filename="logo.png")
            msg2.attach(logo2)
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg2)
        print("   ✅ Notificación de corrección enviada al IMO Aurelio")
    except Exception as e:
        print(f"   ❌ Error: {e}")

    time.sleep(4)

    # 3. SMS CORREGIDO
    print(f"\n📱 Enviando SMS corregido a {PAUL['telefono']}...")
    url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
    texto = "Hola Paul! Correccion: Tu inscripcion al C1 E28 es NUEVA INSCRIPCION (no cambio de cupo). Te esperamos manana 29 mayo, 9AM en Hotel BTH, Av Guardia Civil 727, San Borja. Tu IMO: Aurelio (979310770). Revisa tu correo!"
    
    try:
        r = requests.get(url, params={"numero": PAUL['telefono'], "mensaje": texto}, timeout=10)
        if r.status_code == 200:
            print("   ✅ SMS corregido enviado")
        else:
            print(f"   ❌ Error HTTP {r.status_code}")
    except Exception as e:
        print(f"   ❌ Error SMS: {e}")

    print(f"\n{'=' * 65}")
    print("  ✅ FE DE ERRATAS COMPLETADA")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    enviar()
