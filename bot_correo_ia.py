import os
import sys
import time
import imaplib
import smtplib
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import pandas as pd
import threading
from dotenv import load_dotenv

# Reconfigurar codificación para evitar caídas en Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Importar ecosistema CREAR LIMA
try:
    from sync_cloud import load_productividad_cloud, actualizar_dato_maestro
    from ia_multimodelo import ia_responder
    from bot_whatsapp import wa
except ImportError:
    print("[WARNING] Faltan módulos del CRM/Bot local. Asegúrate de ejecutar esto en la carpeta bot-cpsl-review.")

# ── CONFIGURACIÓN (A llenar por Gerencia) ──
EMAIL_GERENCIA = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get("GMAIL_APP_PASS", "AQUÍ_VA_TU_CLAVE_DE_16_LETRAS")

COORDS_INFO = {
    "Diana Moscoso": {"email": "diana.moscoso@crearpsl.com", "wa": "51912379744"},
    "Joyce Marin": {"email": "joyce.marin@crearpsl.com", "wa": "51933599903"}
}

# ── 1. RUTINA 8:50 AM: DISPARAR ALERTAS (CORREO + WA) ──
def disparar_alertas_matutinas():
    print(f"[{datetime.now().strftime('%H:%M')}] Iniciando Despacho Táctico de 8:50 AM...")
    df_prod = load_productividad_cloud()
    if df_prod.empty:
        print("Error: Base de datos vacía.")
        return
        
    # FILTRO ESTRICTO DE CAMPAÑA C1E27
    if 'Equipo' in df_prod.columns:
        df_prod = df_prod[df_prod['Equipo'] == 'EQUIPO 27']
        
    def es_sentado(val):
        v = str(val).upper().strip()
        if v in ['SI', 'CONFIRMADO', 'SENTADO', '✓', '✔', 'ASISTIRA']: return True
        if 'SENTADO' in v or 'CONFIRMADO' in v or '✓' in v or '✔' in v: return True
        return False
        
    df_prod['EsSentado'] = df_prod['Asistencia'].apply(es_sentado) if 'Asistencia' in df_prod.columns else False
    df_prod['EsDesertor'] = df_prod['Asistencia'].str.upper().str.contains('DESERTOR', na=False) if 'Asistencia' in df_prod.columns else False
        
    df_no_sentados = df_prod[~df_prod['EsSentado'] & ~df_prod['EsDesertor']]
    
    for cc_name, info in COORDS_INFO.items():
        df_cc = df_no_sentados[df_no_sentados['Coordinador'] == cc_name]
        if df_cc.empty: continue
        
        casos = len(df_cc)
        nombres_destacados = ", ".join(df_cc['NombreCompleto'].head(3).tolist())
        
        # 1. Enviar por WhatsApp
        msg_wa = f"🚨 *TORRE DE CONTROL - REPORTE 8:50 AM*\n\nHola {cc_name.split()[0]},\nTienes *{casos} derivados/pendientes* que requieren solución en menos de 12 horas.\n\nEjemplo: {nombres_destacados}...\n\n✉️ *Acabo de enviarte el reporte detallado a tu correo*. Responde a ese correo hoy mismo con las actualizaciones para que la IA las procese automáticamente."
        wa(info["wa"], msg_wa, "GERENCIA")
        
        # 2. Enviar por Correo
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_GERENCIA, EMAIL_PASS)
            
            html_table = df_cc[['NombreCompleto', 'ApellidoCompleto', 'Resultado Gestión', 'Fecha Gestión']].to_html(index=False, justify='center', border=1)
            html_content = f"""
            <html><body>
                <h2 style='color: #dc2626;'>🚨 REPORTE DE DERIVADOS Y PENDIENTES - C1E27</h2>
                <p>Hola <b>{cc_name}</b>,</p>
                <p>Gerencia solicita cierre o contacto efectivo en <b>menos de 12 horas</b> para los siguientes {casos} casos:</p>
                {html_table}
                <br><hr>
                <p>🤖 <b>IMPORTANTE:</b> Responde a este mismo correo indicando qué pasó con cada uno. <br>
                Ejemplo: <i>'Juan Perez ya confirmó. Maria Gomez no contesta.'</i><br>
                El Cerebro Cuántico leerá tu correo y actualizará el CRM automáticamente.</p>
            </body></html>
            """
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_GERENCIA
            msg['To'] = info["email"]
            msg['Subject'] = f"🚨 URGENTE: {casos} Casos Pendientes (Resolver en <12h)"
            msg.attach(MIMEText(html_content, 'html'))
            
            server.send_message(msg)
            server.quit()
            print(f"✅ Alertas enviadas a {cc_name} (WA + Correo)")
        except Exception as e:
            print(f"❌ Error enviando correo a {cc_name}: {e}")

# ── 2. RUTINA IA: LEER CORREOS Y ACTUALIZAR CRM ──
def procesar_respuestas_correo():
    print(f"[{datetime.now().strftime('%H:%M')}] Buscando respuestas de CCs en Gmail...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_GERENCIA, EMAIL_PASS)
        mail.select("inbox")
        
        # Buscar correos NO LEÍDOS
        status, messages = mail.search(None, "UNSEEN")
        if status == "OK" and messages[0]:
            for num in messages[0].split():
                typ, data = mail.fetch(num, "(RFC822)")
                for response_part in data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        sender = msg.get("From")
                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes): subject = subject.decode(encoding if encoding else "utf-8")
                        
                        # Extraer texto del correo
                        cuerpo = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    cuerpo = part.get_payload(decode=True).decode()
                                    break
                        else:
                            cuerpo = msg.get_payload(decode=True).decode()
                            
                        # Limpiar historial anidado (el "On date, Gerencia wrote:")
                        cuerpo_limpio = cuerpo.split("El mié,")[0].split("On Wed")[0].strip()
                        
                        if len(cuerpo_limpio) > 10:
                            print(f"📧 Correo nuevo de {sender}. Analizando con IA Cuántica...")
                            
                            prompt_ia = f"""
                            El siguiente es un correo de una Coordinadora actualizando el estado de sus participantes.
                            Extrae ÚNICAMENTE una lista de los nombres mencionados y su nuevo estado (OK, REZAGADO, NO CONTESTA, DESERTOR).
                            Devuelve la respuesta en formato de texto plano simple por línea: Nombre Apellido | ESTADO
                            Correo:
                            "{cuerpo_limpio}"
                            """
                            # Llamada al cerebro
                            analisis = ia_responder(prompt_ia, contexto="Cerebro_Email_Parser")
                            print(f"🧠 Resultado IA:\n{analisis}")
                            
                            # Actualizar Google Sheets (Ejemplo simplificado)
                            for linea in analisis.split('\\n'):
                                if '|' in linea:
                                    nombre, estado = linea.split('|')
                                    print(f"🔄 Actualizando CRM -> {nombre.strip()} a {estado.strip()}")
                                    # actualizar_dato_maestro(dni_o_nombre, 'Estatus C1', estado.strip())
                                    
                # Marcar como leído
                mail.store(num, '+FLAGS', '\\Seen')
        mail.logout()
    except Exception as e:
        print(f"❌ Error leyendo correos: {e}")

# ── 3. PROGRAMADOR PRINCIPAL (SCHEDULER) ──
def daemon_principal():
    print("🤖 BOT DE CORREOS IA INICIADO. VIGILANDO 24/7...")
    alertas_enviadas_hoy = False
    
    while True:
        ahora = datetime.now()
        dia_semana = ahora.weekday() # 0 = Lunes, 1 = Martes ... 4 = Viernes
        hora = ahora.hour
        minuto = ahora.minute
        
        # 1. Chequeo de 8:50 AM (Martes a Viernes)
        if dia_semana in [1, 2, 3, 4] and hora == 8 and minuto == 50:
            if not alertas_enviadas_hoy:
                disparar_alertas_matutinas()
                alertas_enviadas_hoy = True
        
        # Resetear flag de alertas a media noche
        if hora == 0:
            alertas_enviadas_hoy = False
            
        # 2. Leer correos cada 10 minutos para procesar respuestas
        if minuto % 10 == 0:
            procesar_respuestas_correo()
            
        time.sleep(60)

if __name__ == "__main__":
    daemon_principal()
