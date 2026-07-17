"""
BIENVENIDA PREMIUM + INDICACIONES — C1 E28 Cambio de Cupo
==========================================================
Envía correo de bienvenida con indicaciones + SMS a los 7 APTOS.
Envía copia al IMO confirmando el envío.
Imágenes de indicaciones adjuntas al correo.
"""
import os
import sys
import re
import time
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

if sys.stdout.encoding != 'utf-8':
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "").replace('"', '').replace("'", "").replace(" ", "")

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

IMG_INDICACIONES = r"C:\Users\josem\Downloads\Imágenes\IC1E28.jpeg"
IMG_BANNER = r"C:\Users\josem\Downloads\Imágenes\Indicaciones C1E28.jpeg"
LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "logo_principal.png")

# ══════════════════════════════════════════════════════════════
# 7 APTOS CONFIRMADOS POR EL USUARIO
# ══════════════════════════════════════════════════════════════
APTOS = [
    {
        "nombre_completo": "Brian Steventh Torres Yañez",
        "nombre_pref": "Brian",
        "email": "xdbrian.steventh@gmail.com",
        "telefono": "910236499",
        "dni": "1523660",
        "imo_nombre": "David Jesus Rodríguez La Riva",
        "imo_email": "daverod24tech@gmail.com",
        "imo_tel": "927788191",
    },
    {
        "nombre_completo": "Bryan Iván Diaz Guerra",
        "nombre_pref": "Bryan",
        "email": "Ivandg1211@gmail.com",
        "telefono": "927943882",
        "dni": "71942750",
        "imo_nombre": "Antony Leo Altamirano Llacchuas",
        "imo_email": "Llaccant@gmail.com",
        "imo_tel": "958110726",
    },
    {
        "nombre_completo": "Erica Magali Perea Noguni",
        "nombre_pref": "Magali",
        "email": "ericaperea26@hotmail.com",
        "telefono": "900490075",
        "dni": "10202624",
        "imo_nombre": "Yuli Inés Machado Quiñones",
        "imo_email": "yulimachado@gmail.com",
        "imo_tel": "950088740",
    },
    {
        "nombre_completo": "Alexander Alvarado Velasco",
        "nombre_pref": "Alex",
        "email": "alex.aav.1998@gmail.com",
        "telefono": "988494485",
        "dni": "74591237",
        "imo_nombre": "Giovana Palomino",
        "imo_email": "lawellness.giovanapalomino@gmail.com",
        "imo_tel": "993717944",
    },
    {
        "nombre_completo": "Marizol Ñanga Espinoza Eguizabal",
        "nombre_pref": "Marisolsita",
        "email": "marizolespinozae49@gmail.com",
        "telefono": "955495024",
        "dni": "9909616",
        "imo_nombre": "Giovana Palomino Marcos",
        "imo_email": "lawellness.giovanapalomino@gmail.com",
        "imo_tel": "993717944",
    },
    {
        "nombre_completo": "Samira Margarita Berrospi Chachayma",
        "nombre_pref": "Sami",
        "email": "Berropisamira040@gmail.com",
        "telefono": "902774466",
        "dni": "76522459",
        "imo_nombre": "Blanca Luz Chachayma Marcos",
        "imo_email": "Blancamarvl@gmail.com",
        "imo_tel": "",
    },
    {
        "nombre_completo": "Nery Escalante Ramirez",
        "nombre_pref": "Nery",
        "email": "nery-san@hotmail.com",
        "telefono": "957328767",
        "dni": "21428247",
        "imo_nombre": "Vannia Sthef Mitac Escalante",
        "imo_email": "vanniamitac@gmail.com",
        "imo_tel": "956237980",
    },
    {
        "nombre_completo": "Paul Yhonadan Valentin Vargas",
        "nombre_pref": "Paul",
        "email": "paulyhonadan_valentin@gmail.com",
        "telefono": "989685398",
        "dni": "75093610",
        "imo_nombre": "Aurelio Valentin Mariano",
        "imo_email": "Aurelio_valentin@hotmail.com",
        "imo_tel": "979310770",
    },
]

def limpiar_tel(t):
    t = re.sub(r'[^\d]', '', str(t))
    if t.startswith('51') and len(t) > 9:
        t = t[2:]
    return t

def generar_html_bienvenida(px):
    nombre_pref = px['nombre_pref']
    imo_nombre = px['imo_nombre']
    imo_tel = limpiar_tel(px['imo_tel'])
    imo_tel_fmt = f"+51 {imo_tel[:3]} {imo_tel[3:6]} {imo_tel[6:]}" if len(imo_tel) >= 9 else imo_tel

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>body,table,td,a{{-webkit-text-size-adjust:100%}}table{{border-collapse:collapse!important}}body{{margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif}}</style></head>
<body style="background:#f0f0f0;margin:0;padding:0;">
<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:40px 0;">
<table border="0" cellpadding="0" cellspacing="0" width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,0.05);">

<!-- HEADER -->
<tr><td align="center" bgcolor="#1a1a2e" style="padding:50px 40px;border-bottom:5px solid #b49632;">
<img src="cid:logo_crear" alt="CREAR GLOBAL" width="180" style="display:block;width:180px;height:auto;"/>
<p style="color:#b49632;margin:18px 0 0;font-size:10px;letter-spacing:5px;text-transform:uppercase;font-weight:bold;">Sistema Transaccional Institucional</p>
</td></tr>

<!-- HERO -->
<tr><td style="padding:50px 55px 0 55px;">
<h1 style="color:#1a1a2e;margin:0;font-size:28px;line-height:36px;font-weight:800;">¡BIENVENIDO/A, {nombre_pref.upper()}!</h1>
<div style="width:60px;height:4px;background:#b49632;margin:16px 0 0;border-radius:2px;"></div>
</td></tr>

<!-- BODY -->
<tr><td style="padding:35px 55px 20px;color:#333;font-size:15px;line-height:27px;">

<p>{nombre_pref},</p>

<p>¡Felicitaciones! Tu inscripción al <strong>Capítulo 1 — Equipo 28</strong> ha sido procesada exitosamente a través del cambio de cupo autorizado por tu IMO.</p>

<p>A partir de este momento, eres parte de una comunidad de profesionales que han decidido operar desde un nivel superior de compromiso, claridad y resultados.</p>

<!-- INFO BOX -->
<div style="background:#fafafa;border-left:4px solid #b49632;padding:22px 25px;margin:28px 0;border-radius:0 8px 8px 0;">
<h3 style="color:#1a1a2e;margin:0 0 14px;font-size:12px;text-transform:uppercase;letter-spacing:2px;font-weight:800;">📋 Detalles de tu Entrenamiento</h3>
<table style="width:100%;font-size:14px;line-height:24px;">
<tr><td style="color:#888;width:110px;padding:4px 0;">Programa</td><td style="font-weight:700;color:#1a1a2e;">Capítulo 1 — Equipo 28</td></tr>
<tr><td style="color:#888;padding:4px 0;">Fechas</td><td style="font-weight:700;color:#1a1a2e;">29, 30 y 31 de mayo de 2026</td></tr>
<tr><td style="color:#888;padding:4px 0;">Lugar</td><td style="font-weight:700;color:#1a1a2e;">BTH Hotel Boutique Concept</td></tr>
<tr><td style="color:#888;padding:4px 0;">Dirección</td><td style="font-weight:700;color:#1a1a2e;">Av. Guardia Civil 727, Urb. Córpac, San Borja</td></tr>
<tr><td style="color:#888;padding:4px 0;">Tu IMO</td><td style="font-weight:700;color:#1a1a2e;">{imo_nombre}</td></tr>
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
<p style="margin:8px 0 4px;font-size:17px;font-weight:bold;color:#1a1a2e;">{imo_nombre}</p>
<p style="margin:4px 0 0;font-size:16px;color:#b49632;font-weight:bold;">📞 {imo_tel_fmt}</p>
</div>

<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:15px 0;">
<a href="https://wa.me/51{imo_tel}" style="background-color:#b49632;color:#fff;padding:14px 40px;text-decoration:none;border-radius:4px;font-weight:bold;font-size:13px;text-transform:uppercase;letter-spacing:1.5px;display:inline-block;">Contactar a mi IMO</a>
</td></tr></table>

<p style="text-align:center;font-weight:700;font-size:15px;color:#1a1a2e;margin:25px 0 5px;">¡Nos vemos muy pronto para crear juntos!</p>
<p style="text-align:center;font-size:14px;color:#666;">Un abrazo,<br><strong>Equipo Crear Poder Sin Límites</strong></p>

<p style="font-size:12px;color:#999;font-style:italic;text-align:center;margin-top:20px;border-top:1px solid #eee;padding-top:15px;">📎 Las imágenes con las indicaciones completas están adjuntas a este correo.<br>También se te ha enviado un SMS de confirmación.</p>

</td></tr>

<!-- FOOTER -->
<tr><td align="center" bgcolor="#fcfcfc" style="padding:40px 55px;color:#999;font-size:11px;line-height:20px;border-top:1px solid #f0f0f0;">
<p style="margin:0;font-weight:800;color:#1a1a2e;text-transform:uppercase;letter-spacing:2px;font-size:12px;">CREAR GLOBAL® — PERÚ 2026</p>
<p style="margin:5px 0 0;color:#b49632;font-weight:600;">Transformación Humana de Alto Impacto</p>
<p style="margin:5px 0 0;">Lima — Perú</p>
<p style="margin:12px 0 0;"><a href="mailto:crearpodersinlimitesperu@gmail.com" style="color:#1a1a2e;text-decoration:none;font-weight:bold;">crearpodersinlimitesperu@gmail.com</a> <span style="color:#eee;padding:0 8px;">|</span> <a href="https://crearglobal.com" style="color:#1a1a2e;text-decoration:none;font-weight:bold;">crearglobal.com</a></p>
<p style="margin:18px 0 0;text-align:justify;font-size:9px;line-height:15px;color:#bbb;"><b>AVISO DE CONFIDENCIALIDAD:</b> Este mensaje y cualquier archivo adjunto están protegidos por leyes de privacidad. La integridad del mensaje está garantizada por el sistema de auditoría operativa de CREACIÓN CUÁNTICA E.I.R.L. (RUC 20612592811).</p>
<p style="margin:12px 0 0;font-size:9px;text-transform:uppercase;letter-spacing:1px;">&copy; 2026 CREAR GLOBAL. All rights reserved.</p>
</td></tr>

</table></td></tr></table></body></html>"""


def generar_html_imo(px):
    nombre_pref = px['nombre_pref']
    imo_pref = px['imo_nombre'].split()[0].title()
    tel_px = limpiar_tel(px['telefono'])
    
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#f0f0f0;margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;">
<table border="0" cellpadding="0" cellspacing="0" width="100%"><tr><td align="center" style="padding:40px 0;">
<table border="0" cellpadding="0" cellspacing="0" width="600" style="background:#fff;border:1px solid #ddd;border-radius:8px;overflow:hidden;box-shadow:0 8px 25px rgba(0,0,0,0.05);">
<tr><td align="center" bgcolor="#1a1a2e" style="padding:35px 40px;border-bottom:4px solid #b49632;">
<img src="cid:logo_crear" alt="CREAR" width="140" style="display:block;width:140px;height:auto;"/>
<p style="color:#b49632;margin:12px 0 0;font-size:9px;letter-spacing:4px;text-transform:uppercase;">Notificación Institucional</p>
</td></tr>
<tr><td style="padding:40px 50px;color:#333;font-size:15px;line-height:26px;">
<h2 style="color:#1a1a2e;font-size:18px;margin:0 0 20px;">✅ Confirmación de Cambio de Cupo Procesado</h2>
<p>{imo_pref},</p>
<p>Te confirmamos que el cambio de cupo que solicitaste ha sido procesado exitosamente. Se han realizado los siguientes envíos institucionales al nuevo participante:</p>
<table style="width:100%;border-collapse:collapse;margin:20px 0;border:1px solid #eee;border-radius:8px;overflow:hidden;">
<tr style="background:#f8f9fa;"><th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;">Canal</th><th style="padding:10px 16px;text-align:left;font-size:11px;text-transform:uppercase;color:#888;">Estado</th></tr>
<tr><td style="padding:12px 16px;border-top:1px solid #f0f0f0;">📧 Correo de Bienvenida + Indicaciones</td><td style="padding:12px 16px;border-top:1px solid #f0f0f0;color:#27ae60;font-weight:bold;">✅ Enviado a {px['email']}</td></tr>
<tr><td style="padding:12px 16px;border-top:1px solid #f0f0f0;">📱 SMS de Confirmación</td><td style="padding:12px 16px;border-top:1px solid #f0f0f0;color:#27ae60;font-weight:bold;">✅ Enviado a +51 {tel_px}</td></tr>
</table>
<div style="background:#fafafa;border-left:4px solid #27ae60;padding:18px 22px;margin:20px 0;border-radius:0 8px 8px 0;">
<h4 style="margin:0 0 10px;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;color:#666;">Participante Registrado</h4>
<table style="font-size:14px;line-height:24px;">
<tr><td style="color:#888;width:100px;">Nombre</td><td style="font-weight:600;">{px['nombre_completo']}</td></tr>
<tr><td style="color:#888;">Prefiere</td><td style="font-weight:600;">{nombre_pref}</td></tr>
<tr><td style="color:#888;">Equipo</td><td style="font-weight:600;">C1 — Equipo 28</td></tr>
<tr><td style="color:#888;">Fechas</td><td style="font-weight:600;">29, 30 y 31 de mayo de 2026</td></tr>
<tr><td style="color:#888;">Lugar</td><td style="font-weight:600;">BTH Hotel, Av. Guardia Civil 727, San Borja</td></tr>
</table>
</div>
<div style="background:#fff8e6;border-left:4px solid #f39c12;padding:16px 20px;margin:20px 0;border-radius:0 6px 6px 0;">
<p style="margin:0;font-size:14px;color:#856404;"><strong>Recordatorio:</strong> Como IMO enrolador, eres 100% responsable de realizar el seguimiento, las llamadas de bienvenida y todo lo necesario para asegurar que <strong>{nombre_pref}</strong> asista y complete su Capítulo 1.</p>
</div>
</td></tr>
<tr><td align="center" bgcolor="#fcfcfc" style="padding:25px 50px;font-size:10px;color:#999;border-top:1px solid #f0f0f0;">
<p style="margin:0;"><strong>CREAR GLOBAL®</strong> — Sistema Institucional — Lima, Perú 2026</p>
</td></tr>
</table></td></tr></table></body></html>"""


def enviar_correo_bienvenida(px, dry_run=False):
    """Envía correo de bienvenida con indicaciones adjuntas al PX."""
    nombre_pref = px['nombre_pref']
    asunto = f"¡Bienvenido/a, {nombre_pref}! Tu lugar en Capítulo 1 — Equipo 28 está confirmado"
    body_html = generar_html_bienvenida(px)
    
    msg = MIMEMultipart("mixed")
    msg['From'] = f"CREAR GLOBAL Official <{GMAIL_USER}>"
    msg['To'] = px['email']
    msg['Subject'] = asunto
    msg.add_header('X-Priority', '1 (Highest)')
    
    # Related part (HTML + inline images)
    msg_related = MIMEMultipart("related")
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body_html, 'html', 'utf-8'))
    msg_related.attach(msg_alt)
    
    # Logo inline
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo_crear>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            msg_related.attach(logo)
    
    msg.attach(msg_related)
    
    # Attach indication images
    for img_path, img_name in [(IMG_BANNER, "Indicaciones_C1E28.jpeg"), (IMG_INDICACIONES, "Informacion_Completa_C1E28.jpeg")]:
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                part = MIMEBase("image", "jpeg")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f'attachment; filename="{img_name}"')
                msg.attach(part)
    
    if dry_run:
        print(f"  [DRY RUN] Correo PX → {px['email']} | Asunto: {asunto}")
        return True
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"  ❌ Error enviando a {px['email']}: {e}")
        return False


def enviar_correo_imo(px, dry_run=False):
    """Envía correo de notificación al IMO."""
    nombre_pref = px['nombre_pref']
    imo_pref = px['imo_nombre'].split()[0].title()
    asunto = f"✅ Confirmación: {nombre_pref} registrado/a en C1 E28 — Correo y SMS enviados"
    body_html = generar_html_imo(px)
    
    msg = MIMEMultipart("related")
    msg['From'] = f"CREAR GLOBAL Official <{GMAIL_USER}>"
    msg['To'] = px['imo_email']
    msg['Subject'] = asunto
    
    msg_alt = MIMEMultipart("alternative")
    msg_alt.attach(MIMEText(body_html, 'html', 'utf-8'))
    msg.attach(msg_alt)
    
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo_crear>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(logo)
    
    if dry_run:
        print(f"  [DRY RUN] Correo IMO → {px['imo_email']} | Asunto: {asunto}")
        return True
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(GMAIL_USER, GMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"  ❌ Error enviando a IMO {px['imo_email']}: {e}")
        return False


def enviar_sms(px, dry_run=False):
    """Envía SMS de bienvenida al PX via MacroDroid."""
    tel = limpiar_tel(px['telefono'])
    imo_first = px['imo_nombre'].split()[0].title()
    imo_tel = limpiar_tel(px['imo_tel'])
    
    texto = (
        f"Hola {px['nombre_pref']}! Bienvenido/a a CREAR - Capitulo 1, Equipo 28 "
        f"(29, 30 y 31 de mayo). Lugar: Hotel BTH, Av Guardia Civil 727, San Borja. "
        f"Vie 9AM registro. Tu IMO: {imo_first} ({imo_tel}). "
        f"Te enviamos un correo con las indicaciones completas. Nos vemos!"
    )
    
    if dry_run:
        print(f"  [DRY RUN] SMS → {tel} | Msg: {texto[:80]}...")
        return True
    
    url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
    try:
        r = requests.get(url, params={"numero": tel, "mensaje": texto}, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"  ❌ Error SMS a {tel}: {e}")
        return False


def ejecutar(dry_run=False):
    modo = "SIMULACIÓN" if dry_run else "ENVÍO REAL"
    print("=" * 65)
    print(f"  BIENVENIDA PREMIUM + INDICACIONES — C1 E28 [{modo}]")
    print(f"  Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Participantes APTOS: {len(APTOS)}")
    print("=" * 65)
    
    if not GMAIL_PASS and not dry_run:
        print("❌ ERROR: GMAIL_APP_PASS no configurada en .env")
        return
    
    resultados = {"correo_px": 0, "correo_imo": 0, "sms": 0, "errores": 0}
    
    for i, px in enumerate(APTOS):
        print(f"\n── [{i+1}/{len(APTOS)}] {px['nombre_completo']} ──")
        
        # 1. Correo bienvenida al PX
        print(f"  📧 Correo bienvenida → {px['email']}")
        if enviar_correo_bienvenida(px, dry_run):
            resultados["correo_px"] += 1
            print(f"     ✅ Correo PX enviado")
        else:
            resultados["errores"] += 1
        
        if not dry_run:
            time.sleep(3)
        
        # 2. SMS al PX
        print(f"  📱 SMS → {limpiar_tel(px['telefono'])}")
        if enviar_sms(px, dry_run):
            resultados["sms"] += 1
            print(f"     ✅ SMS enviado")
        else:
            resultados["errores"] += 1
        
        if not dry_run:
            time.sleep(4)
        
        # 3. Correo al IMO
        print(f"  📧 Correo IMO → {px['imo_email']}")
        if enviar_correo_imo(px, dry_run):
            resultados["correo_imo"] += 1
            print(f"     ✅ Correo IMO enviado")
        else:
            resultados["errores"] += 1
        
        if not dry_run:
            time.sleep(3)
    
    print(f"\n{'=' * 65}")
    print(f"  RESUMEN FINAL")
    print(f"  📧 Correos PX enviados:  {resultados['correo_px']}/{len(APTOS)}")
    print(f"  📱 SMS enviados:         {resultados['sms']}/{len(APTOS)}")
    print(f"  📧 Correos IMO enviados: {resultados['correo_imo']}/{len(APTOS)}")
    print(f"  ❌ Errores:              {resultados['errores']}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Simulación sin enviar")
    parser.add_argument("--enviar", action="store_true", help="Envío real")
    args = parser.parse_args()
    
    if args.preview:
        ejecutar(dry_run=True)
    elif args.enviar:
        ejecutar(dry_run=False)
    else:
        print("Uso: python bienvenida_cambio_cupo_e28.py --preview | --enviar")
