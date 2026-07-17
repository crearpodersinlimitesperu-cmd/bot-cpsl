"""
MOTOR DE CAMPAÑAS POR CORREO — CPSL Lima
==========================================
Genera y programa correos personalizados para:
1. PX rezagados C1 → Invitación C1 E28 (29-31 mayo)
2. IMOs de PX pendientes → Llamado a reenrolar
Programado para domingo 10 mayo, 8:00 AM Lima.
"""
import sqlite3
import pandas as pd
import smtplib
import os
import sys
import json
import time
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from gatekeeper import Gatekeeper
from crear_email_core import EmailEngine

gk = Gatekeeper()
engine = EmailEngine()

sys.stdout.reconfigure(encoding='utf-8')

TZ = ZoneInfo("America/Lima")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "torre_control.db")

# ── Config email ──
GMAIL_USER = "crearpodersinlimitesperu@gmail.com"
GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "")
if not GMAIL_PASS:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    GMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "")

GMAIL_PASS = GMAIL_PASS.replace('"', '').replace("'", "").replace(" ", "")

HORA_ENVIO = 8  # 8 AM Lima
BATCH_SIZE = 15  # Correos por lote
DELAY_ENTRE_LOTES = 65  # Segundos entre lotes (Gmail rate limit)
DELAY_ENTRE_CORREOS = 4  # Segundos entre correos individuales

# ── Archivos de estado ──
ESTADO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campana_email_estado.json")
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campana_email_log.json")

def ahora():
    return datetime.now(TZ)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def cargar_emails_contacts():
    """Carga emails desde contacts.csv (2,742 disponibles)."""
    contacts_path = r"C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv"
    gc_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Google_Contacts_EQUIPO27.csv"
    
    email_map = {}  # telefono -> email
    name_email = {}  # nombre_normalizado -> email
    
    # Contacts campaña (2,742 emails)
    if os.path.exists(contacts_path):
        df = pd.read_csv(contacts_path, dtype=str)
        for _, row in df.iterrows():
            email = str(row.get('E-mail 1 - Value', '')).strip().lower()
            if not email or '@' not in email or email == 'nan':
                email = str(row.get('E-mail 2 - Value', '')).strip().lower()
            if not email or '@' not in email or email == 'nan':
                continue
            
            # Extraer teléfono
            phone = str(row.get('Phone 1 - Value', '')).strip()
            phone = re.sub(r'[^\d]', '', phone)
            if phone.startswith('51') and len(phone) > 9:
                phone = phone[2:]
            
            nombre = str(row.get('Name', '') or '').strip().upper()
            if phone and len(phone) >= 9:
                email_map[phone] = email
            if nombre:
                name_email[nombre] = email
    
    # Google Contacts E27 (275)
    if os.path.exists(gc_path):
        df2 = pd.read_csv(gc_path, dtype=str)
        for _, row in df2.iterrows():
            email = str(row.get('E-mail Address', '')).strip().lower()
            if not email or '@' not in email:
                continue
            nombre = str(row.get('Name', '') or '').strip().upper()
            phone = str(row.get('Phone 1 - Value', '')).strip()
            phone = re.sub(r'[^\d]', '', phone)
            if phone.startswith('51') and len(phone) > 9:
                phone = phone[2:]
            if phone and len(phone) >= 9:
                email_map[phone] = email
            if nombre:
                name_email[nombre] = email
    
    print(f"  📧 Emails cargados: {len(email_map)} por teléfono + {len(name_email)} por nombre")
    return email_map, name_email

def buscar_email_px(px, email_map, name_email):
    """Busca el email de un PX por teléfono o nombre."""
    tel = str(px['telefono']).strip()
    if tel in email_map:
        return email_map[tel]
    
    # 3. Fuzzy: coincidencias más estrictas (Nombre completo contenido en el nombre de contacto)
    nombre_full = f"{px['nombre']} {px['apellido']}".strip().upper()
    for k, v in name_email.items():
        if nombre_full in k:
            return v
    
    return None

# ══════════════════════════════════════════════════════════════
# PLANTILLAS DE CORREO
# ══════════════════════════════════════════════════════════════

def generar_correo_px(nombre_pref, cc_nombre, cc_tel, equipo):
    """Correo profesional de alto rendimiento para PX rezagado C1."""
    asunto = f"{nombre_pref}, tu compromiso con Capítulo 1 tiene fecha — 29 de mayo"
    
    # Standardized content using base_enterprise.html structure
    template_path = os.path.join(os.path.dirname(__file__), "templates", "base_enterprise.html")
    
    contenido_html = f"""
<p>{nombre_pref},</p>

<p>Cuando te inscribiste en Capítulo 1, tomaste una decisión que habla de quién estás eligiendo ser.
Esa decisión sigue vigente. Y el espacio que reservaste para vivir esta experiencia tiene fecha y lugar confirmados.</p>

<div class="info-box" style="background-color: #fcfcfc; border-left: 4px solid #b49632; padding: 25px; margin: 30px 0; border-radius: 0 8px 8px 0;">
    <h3 style="color: #1a1a2e; margin: 0 0 12px; font-size: 15px; text-transform: uppercase; letter-spacing: 1px;">Detalles de tu Entrenamiento</h3>
    <p style="margin: 6px 0; font-size: 15px;">Programa: <strong>Capítulo 1 — Equipo 28</strong></p>
    <p style="margin: 6px 0; font-size: 15px;">Fechas: <strong>29, 30 y 31 de mayo de 2026</strong></p>
    <p style="margin: 6px 0; font-size: 15px;">Sede: Lima, Perú</p>
</div>

<p>Capítulo 1 es un entrenamiento diseñado para profesionales que han decidido operar desde un nivel superior de compromiso, claridad y resultados.
No se trata de motivación temporal. Se trata de <b>instalar distinciones que transforman la manera en que produces resultados en cada área de tu vida</b>.</p>

<p>Tu coordinadora institucional, <b>{cc_nombre}</b>, es la persona designada para acompañarte en la logística y confirmación de tu participación. Comuníquate directamente con ella:</p>

<div style="background: #fdfdfd; padding: 25px; border-radius: 10px; text-align: center; margin: 24px 0; border: 1px solid #e0e0e0;">
    <p style="margin: 4px 0; font-size: 18px; font-weight: bold; color: #1a1a2e;">{cc_nombre}</p>
    <p style="margin: 4px 0; font-size: 17px; color: #b49632; font-weight: bold;">{cc_tel}</p>
</div>

<p>Si ya tienes confirmada tu asistencia, puede responder este correo institucional con la palabra <b>CONFIRMADO</b>.</p>

<table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
        <td align="center" style="padding: 20px 0;">
            <a href="https://wa.me/{cc_tel.replace('+', '').replace(' ', '')}" style="background-color: #b49632; color: #ffffff; padding: 15px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Coordinar con mi CC</a>
        </td>
    </tr>
</table>
"""
    placeholders = {
        "GREETING": f"CONFIRMACIÓN INSTITUCIONAL — {nombre_pref.upper()}",
        "CONTENT": contenido_html
    }
    
    try:
        cuerpo_final = engine.load_template(template_path, placeholders)
        return asunto, cuerpo_final
    except:
        # Fallback to old simple body if template fails
        return asunto, contenido_html

def generar_correo_imo(imo_nombre, px_lista, cc_nombre):
    """Correo profesional de alto rendimiento para IMO enrolador."""
    imo_pref = imo_nombre.split()[0].title() if imo_nombre else "Estimado IMO"
    num_px = len(px_lista)
    
    asunto = f"{imo_pref}, {num_px} participante{'s' if num_px > 1 else ''} de tu red requiere{'n' if num_px > 1 else ''} seguimiento — C1 E28"
    
    tabla_px = ""
    for px in px_lista:
        nombre = px.get('nombre_preferido') or px.get('nombre', '').split()[0].title()
        estado = px.get('resultado_gestion', '') or 'Pendiente de gestión'
        tabla_px += f"""<tr>
            <td style="padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px;">{nombre} {px.get('apellido', '')}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px;">{px.get('equipo', '')}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px;">{px.get('telefono', '')}</td>
            <td style="padding: 10px 12px; border-bottom: 1px solid #eee; font-size: 14px;">{estado}</td>
        </tr>"""
    
    template_path = os.path.join(os.path.dirname(__file__), "templates", "base_standard.html")
    
    contenido_html = f"""
<p>{imo_pref},</p>

<p>El siguiente reporte corresponde a participantes de tu red de enrolamiento que aún no han confirmado su asistencia
al <strong>Capítulo 1 — Equipo 28</strong> (29, 30 y 31 de mayo de 2026).</p>

<p>Como IMO enrolador, tu relación con estas personas es el activo más valioso para reactivar su compromiso.
<strong>Una conversación directa tuya tiene mayor impacto que cualquier mensaje masivo.</strong></p>

<div style="margin: 28px 0; background: #fff; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); border: 1px solid #eee;">
    <h3 style="color: #fff; background: #1a1a2e; margin: 0; padding: 14px 16px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Participantes pendientes ({num_px})</h3>
    <table style="width: 100%; border-collapse: collapse;">
        <tr style="background: #f8f9fa;">
            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #666;">Participante</th>
            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #666;">Equipo</th>
            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #666;">Teléfono</th>
            <th style="padding: 12px; text-align: left; font-size: 11px; text-transform: uppercase; color: #666;">Estado</th>
        </tr>
        {tabla_px}
    </table>
</div>

<div class="info-box" style="border-left: 4px solid #1a1a2e;">
    <h4 style="margin: 0 0 10px; color: #1a1a2e; font-size: 14px; text-transform: uppercase;">Protocolo Recomendado</h4>
    <ul style="font-size: 14px; line-height: 1.8; padding-left: 20px; color: #444; margin: 0;">
        <li>Contacto telefónico directo para reconectar con su visión.</li>
        <li>Confirmar fechas: 29, 30 y 31 de mayo en Lima.</li>
        <li>Derivar a <strong>{cc_nombre}</strong> para formalizar la confirmación.</li>
    </ul>
</div>
"""
    placeholders = {
        "GREETING": "REPORTE DE SEGUIMIENTO",
        "CONTENT": contenido_html
    }
    
    try:
        cuerpo_final = engine.load_template(template_path, placeholders)
        return asunto, cuerpo_final
    except:
        return asunto, contenido_html

# ══════════════════════════════════════════════════════════════
# MOTOR DE ENVÍO
# ══════════════════════════════════════════════════════════════

def enviar_correo(destinatario, asunto, cuerpo_html, dry_run=False, px_id=0):
    """Envía un correo individual vía EmailEngine."""
    if dry_run:
        return engine.send_email(destinatario, asunto, cuerpo_html, px_id=px_id)
    
    success, msg = engine.send_enterprise_email(
        to=destinatario, 
        subject=asunto, 
        body_html=cuerpo_html, 
        px_id=px_id,
        metadata={"campaign": "C1E28_REZAGADOS"}
    )
    if not success:
        print(f"  ❌ Error enviando a {destinatario}: {msg}")
    return success

def cargar_estado():
    if os.path.exists(ESTADO_FILE):
        with open(ESTADO_FILE, 'r') as f:
            return json.load(f)
    return {"enviados_px": [], "enviados_imo": [], "errores": [], "inicio": None}

def guardar_estado(estado):
    with open(ESTADO_FILE, 'w', encoding='utf-8') as f:
        json.dump(estado, f, indent=2, ensure_ascii=False, default=str)

def preparar_campana():
    """Prepara la lista de correos a enviar."""
    print("=" * 60)
    print("  PREPARACIÓN DE CAMPAÑA EMAIL — C1 E28")
    print("=" * 60)
    
    email_map, name_email = cargar_emails_contacts()
    conn = get_db()
    
    # 1. PX REZAGADOS
    print("\n📧 CORREOS PARA PX REZAGADOS C1:")
    pendientes = conn.execute("""
        SELECT id, nombre, apellido, nombre_preferido, telefono, equipo, 
               cc_nombre, cc_tel, imo, resultado_gestion, c1, c2
        FROM participantes 
        WHERE (c1='NO' OR c2='NO') AND es_pendiente_real='SI'
    """).fetchall()
    
    correos_px = []
    sin_email_px = 0
    for px in pendientes:
        px_dict = dict(px)
        email = buscar_email_px(px_dict, email_map, name_email)
        if email:
            nombre_pref = px_dict['nombre_preferido'] or px_dict['nombre'].split()[0].title()
            cc = px_dict['cc_nombre'] or 'Coordinadora CPSL'
            cc_tel = px_dict['cc_tel'] or ''
            asunto, cuerpo = generar_correo_px(nombre_pref, cc, cc_tel, px_dict['equipo'])
            correos_px.append({
                "id": px_dict['id'],
                "email": email,
                "nombre": f"{px_dict['nombre']} {px_dict['apellido']}",
                "asunto": asunto,
                "cuerpo": cuerpo,
                "tipo": "PX"
            })
        else:
            sin_email_px += 1
    
    print(f"  ✅ Con email: {len(correos_px)}")
    print(f"  ❌ Sin email: {sin_email_px}")
    
    # 2. IMOs
    print("\n📧 CORREOS PARA IMOs ENROLADORES:")
    imos_data = {}
    for px in pendientes:
        px_dict = dict(px)
        imo = px_dict.get('imo', '')
        if not imo or imo == 'nan':
            continue
        if imo not in imos_data:
            # Obtener tel_imo desde la DB
            tel_imo_row = conn.execute(
                "SELECT tel_imo FROM participantes WHERE imo=? AND tel_imo IS NOT NULL AND tel_imo != '' AND tel_imo != 'nan' LIMIT 1",
                (imo,)
            ).fetchone()
            tel_imo = tel_imo_row[0] if tel_imo_row else ''
            imos_data[imo] = {"px_list": [], "cc": px_dict.get('cc_nombre', ''), "tel_imo": tel_imo}
        imos_data[imo]["px_list"].append(px_dict)
    
    correos_imo = []
    sin_email_imo = 0
    for imo_nombre, data in imos_data.items():
        if len(data["px_list"]) < 1:
            continue
        
        email = None
        
        # Intento 1: Buscar por teléfono del IMO
        tel_imo = re.sub(r'[^\d]', '', str(data.get('tel_imo', '')))
        if tel_imo.startswith('51') and len(tel_imo) > 9:
            tel_imo = tel_imo[2:]
        if tel_imo and tel_imo in email_map:
            email = email_map[tel_imo]
        
        # Intento 2: Por nombre exacto
        if not email:
            imo_upper = imo_nombre.strip().upper()
            email = name_email.get(imo_upper)
        
        # Intento 3: Fuzzy por tokens de nombre
        if not email:
            imo_upper = imo_nombre.strip().upper()
            tokens = imo_upper.split()
            if len(tokens) >= 2:
                for k, v in name_email.items():
                    if tokens[0] in k and tokens[-1] in k:
                        email = v
                        break
        
        if email:
            asunto, cuerpo = generar_correo_imo(imo_nombre, data["px_list"], data["cc"])
            correos_imo.append({
                "email": email,
                "nombre": imo_nombre,
                "asunto": asunto,
                "cuerpo": cuerpo,
                "tipo": "IMO",
                "num_px": len(data["px_list"])
            })
        else:
            sin_email_imo += 1
    
    print(f"  ✅ IMOs con email: {len(correos_imo)} (responsables de {sum(c['num_px'] for c in correos_imo)} PX)")
    print(f"  ❌ IMOs sin email: {sin_email_imo}")
    
    conn.close()
    
    # Guardar lista programada
    campana = {
        "creada": ahora().isoformat(),
        "programada_para": f"{(ahora() + timedelta(days=1)).strftime('%Y-%m-%d')} 08:00",
        "total_correos_px": len(correos_px),
        "total_correos_imo": len(correos_imo),
        "correos_px": correos_px,
        "correos_imo": correos_imo
    }
    
    with open(os.path.join(os.path.dirname(__file__), "campana_email_programada.json"), 'w', encoding='utf-8') as f:
        json.dump(campana, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n{'='*60}")
    print(f"  CAMPAÑA PREPARADA")
    print(f"  📧 PX: {len(correos_px)} correos")
    print(f"  📧 IMO: {len(correos_imo)} correos")
    print(f"  📅 Programada: Domingo 10 mayo, 8:00 AM Lima")
    print(f"  📁 Archivo: campana_email_programada.json")
    print(f"{'='*60}")
    
    return campana

def ejecutar_envio(campana=None, dry_run=False):
    """Ejecuta el envío de correos. Si dry_run=True, solo simula."""
    if not campana:
        path = os.path.join(os.path.dirname(__file__), "campana_email_programada.json")
        with open(path, 'r', encoding='utf-8') as f:
            campana = json.load(f)
    
    estado = cargar_estado()
    estado["inicio"] = ahora().isoformat()
    
    todos = campana["correos_px"] + campana["correos_imo"]
    ya_enviados = set(estado.get("enviados_px", []) + estado.get("enviados_imo", []))
    pendientes = [c for c in todos if c["email"] not in ya_enviados]
    
    print(f"\n{'='*60}")
    print(f"  {'SIMULACIÓN' if dry_run else 'ENVÍO'} DE CAMPAÑA EMAIL")
    print(f"  Total: {len(todos)} | Ya enviados: {len(ya_enviados)} | Pendientes: {len(pendientes)}")
    print(f"{'='*60}")
    
    if not GMAIL_PASS and not dry_run:
        print("  ❌ ERROR: GMAIL_APP_PASS no configurada en .env")
        return
    
    enviados = 0
    errores = 0
    
    for i, correo in enumerate(pendientes):
        if i > 0 and i % BATCH_SIZE == 0:
            print(f"  ⏳ Pausa de {DELAY_ENTRE_LOTES}s (rate limit)...")
            if not dry_run:
                time.sleep(DELAY_ENTRE_LOTES)
                
        # VALIDACIÓN GATEKEEPER ANTES DE ENVIAR
        px_id = correo.get("id", -1)
        if px_id != -1:
            valido, razon = gk.validate_send(participante_id=px_id, canal='EMAIL', campana_tipo='C1')
            if not valido:
                print(f"  ⛔ BLOQUEADO por Gatekeeper [{correo['tipo']} - ID {px_id}]: {razon}")
                errores += 1
                estado["errores"].append({"email": correo["email"], "error": f"Gatekeeper Blocked: {razon}", "ts": ahora().isoformat()})
                guardar_estado(estado)
                continue
        else:
            # Si es IMO sin ID, al menos validamos formato de correo manualmente
            valido, razon = gk._validar_email(correo["email"])
            if not valido:
                print(f"  ⛔ BLOQUEADO por Gatekeeper [{correo['tipo']} - {correo['email']}]: {razon}")
                errores += 1
                continue
        
        ok = enviar_correo(correo["email"], correo["asunto"], correo["cuerpo"], dry_run=dry_run, px_id=px_id)
        
        if ok:
            enviados += 1
            if correo["tipo"] == "PX":
                estado["enviados_px"].append(correo["email"])
            else:
                estado["enviados_imo"].append(correo["email"])
            print(f"  ✅ [{i+1}/{len(pendientes)}] {correo['tipo']} → {correo['email'][:30]}...")
        else:
            errores += 1
            estado["errores"].append({"email": correo["email"], "error": "envio fallido", "ts": ahora().isoformat()})
        
        if not dry_run:
            time.sleep(DELAY_ENTRE_CORREOS)
        
        guardar_estado(estado)
    
    print(f"\n  📊 Resultado: {enviados} enviados, {errores} errores")
    return estado

def esperar_y_enviar():
    """Espera hasta las 8 AM y ejecuta el envío."""
    print(f"\n⏰ Hora actual Lima: {ahora().strftime('%H:%M')}")
    
    target = ahora().replace(hour=HORA_ENVIO, minute=0, second=0, microsecond=0)
    if ahora().hour >= HORA_ENVIO:
        target += timedelta(days=1)
    
    delta = (target - ahora()).total_seconds()
    print(f"⏰ Programado para: {target.strftime('%Y-%m-%d %H:%M')}")
    print(f"⏰ Esperando {delta/3600:.1f} horas...")
    
    while ahora() < target:
        restante = (target - ahora()).total_seconds()
        if restante > 0:
            print(f"  ⏳ Faltan {restante/60:.0f} min...", end='\r')
            time.sleep(min(300, restante))
    
    print(f"\n🚀 ¡HORA DE ENVÍO! {ahora().strftime('%H:%M')}")
    ejecutar_envio()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Motor de campañas email CPSL")
    parser.add_argument("--preparar", action="store_true", help="Prepara la campaña")
    parser.add_argument("--preview", action="store_true", help="Simula el envío (dry run)")
    parser.add_argument("--enviar", action="store_true", help="Envía ahora")
    parser.add_argument("--programar", action="store_true", help="Espera hasta las 8 AM y envía")
    args = parser.parse_args()
    
    if args.preparar:
        preparar_campana()
    elif args.preview:
        ejecutar_envio(dry_run=True)
    elif args.enviar:
        ejecutar_envio()
    elif args.programar:
        esperar_y_enviar()
    else:
        print("Uso: python campana_email_c1e28.py --preparar|--preview|--enviar|--programar")
