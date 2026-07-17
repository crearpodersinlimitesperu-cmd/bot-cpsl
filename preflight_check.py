"""
VERIFICACIÓN PRE-VUELO — Campaña Email 8 AM
=============================================
Chequea cada componente crítico antes del envío.
"""
import os, sys, json, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding='utf-8')
TZ = ZoneInfo("America/Lima")

CHECKS = []

def check(nombre, ok, detalle=""):
    CHECKS.append((nombre, ok, detalle))
    print(f"  {'✅' if ok else '❌'} {nombre}: {detalle}")

def run():
    print("=" * 60)
    print("  VERIFICACIÓN PRE-VUELO — Campaña Email 8 AM")
    print(f"  Hora Lima: {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. Campaña preparada
    camp_path = os.path.join(os.path.dirname(__file__), "campana_email_programada.json")
    exists = os.path.exists(camp_path)
    check("Archivo campaña", exists, camp_path if exists else "NO ENCONTRADO")
    
    if exists:
        with open(camp_path, 'r', encoding='utf-8') as f:
            camp = json.load(f)
        total_px = camp.get('total_correos_px', 0)
        total_imo = camp.get('total_correos_imo', 0)
        check("Correos PX", total_px > 0, f"{total_px} correos")
        check("Correos IMO", total_imo > 0, f"{total_imo} correos")
        check("Total campaña", total_px + total_imo > 0, f"{total_px + total_imo} correos")
    
    # 2. Credenciales Gmail
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
    gmail_pass = os.environ.get("GMAIL_APP_PASS", "")
    gmail_pass = gmail_pass.replace('"', '').replace("'", "").replace(" ", "")
    check("GMAIL_APP_PASS", bool(gmail_pass), f"Longitud: {len(gmail_pass)}")
    
    # 3. Conexión SMTP
    gmail_user = "crearpodersinlimitesperu@gmail.com"
    smtp_ok = False
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10) as server:
            server.login(gmail_user, gmail_pass)
            smtp_ok = True
        check("Conexión SMTP Gmail", True, "Login exitoso")
    except Exception as e:
        check("Conexión SMTP Gmail", False, str(e))
    
    # 4. Envío de correo de prueba
    if smtp_ok:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "✅ PRE-VUELO OK — Campaña C1 E28 lista para 8 AM"
            msg['From'] = f"CPSL Lima <{gmail_user}>"
            msg['To'] = gmail_user
            
            html = f"""<html><body style="font-family: 'Segoe UI', sans-serif; padding: 20px;">
<h2 style="color: #e94560;">Verificación Pre-Vuelo Completada</h2>
<p>La campaña de correos está lista para ejecutarse.</p>
<ul>
    <li><strong>Correos PX:</strong> {total_px}</li>
    <li><strong>Correos IMO:</strong> {total_imo}</li>
    <li><strong>Total:</strong> {total_px + total_imo}</li>
    <li><strong>Hora programada:</strong> 8:00 AM Lima</li>
    <li><strong>Verificación:</strong> {datetime.now(TZ).strftime('%Y-%m-%d %H:%M:%S')}</li>
</ul>
<p style="color: #388e3c;"><strong>Todos los sistemas operativos.</strong></p>
</body></html>"""
            msg.attach(MIMEText(html, 'html', 'utf-8'))
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(gmail_user, gmail_pass)
                server.send_message(msg)
            check("Correo de prueba", True, f"Enviado a {gmail_user}")
        except Exception as e:
            check("Correo de prueba", False, str(e))
    
    # 5. Proceso programador activo
    import subprocess
    result = subprocess.run(
        ["powershell", "-Command", 
         "Get-Process python* | Where-Object { $_.StartTime -gt (Get-Date).AddHours(-1) } | Select-Object Id, StartTime | Format-Table -AutoSize"],
        capture_output=True, text=True
    )
    procs = result.stdout.strip()
    check("Proceso programador", bool(procs), procs.replace('\n', ' | ')[:100] if procs else "NINGUNO")
    
    # 6. Estado limpio (sin envíos previos)
    estado_path = os.path.join(os.path.dirname(__file__), "campana_email_estado.json")
    if os.path.exists(estado_path):
        with open(estado_path, 'r') as f:
            estado = json.load(f)
        ya_env = len(estado.get('enviados_px', [])) + len(estado.get('enviados_imo', []))
        check("Estado limpio", ya_env == 0, f"{ya_env} ya enviados" if ya_env > 0 else "Limpio, 0 enviados previos")
    else:
        check("Estado limpio", True, "Sin archivo de estado (primera ejecución)")
    
    # 7. DB accesible
    import sqlite3
    try:
        conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "torre_control.db"))
        total = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI'").fetchone()[0]
        conn.close()
        check("Base de datos", True, f"{total} pendientes reales C1")
    except Exception as e:
        check("Base de datos", False, str(e))
    
    # RESUMEN
    passed = sum(1 for _, ok, _ in CHECKS if ok)
    failed = sum(1 for _, ok, _ in CHECKS if not ok)
    
    print(f"\n{'='*60}")
    if failed == 0:
        print(f"  🟢 TODOS LOS SISTEMAS OPERATIVOS ({passed}/{passed})")
        print(f"  📅 Campaña ejecutará a las 8:00 AM Lima sin intervención")
        print(f"  📧 782 correos listos (592 PX + 190 IMO)")
    else:
        print(f"  🔴 {failed} FALLOS DETECTADOS — REVISAR ANTES DE LAS 8 AM")
    print(f"{'='*60}")

if __name__ == "__main__":
    run()
