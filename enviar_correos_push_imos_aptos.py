import pandas as pd
import sqlite3
import smtplib
import time
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = os.environ.get('GMAIL_APP_PASS', '').replace('"', '').replace(' ', '')

COORDINADORAS = {
    'jmarin': {'nombre': 'Joyce Marin', 'telefono': '933 599 903'},
    'dmoscoso': {'nombre': 'Diana Moscoso', 'telefono': '912 379 744'},
}

def cargar_imos_con_correo():
    """Carga los 4 reportes de equipos, cruza con asignados aptos y devuelve IMOs con email."""
    files = [
        r'C:\Users\josem\Downloads\reporte_equipos.xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (1).xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (2).xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (3).xlsx',
    ]
    dfs = []
    for f in files:
        dfs.append(pd.read_excel(f))
    df_reportes = pd.concat(dfs, ignore_index=True)
    df_reportes['id_clean'] = df_reportes['Identificación'].astype(str).str.strip().str.replace('.0', '', regex=False)

    csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
    df_aptos = pd.read_csv(csv_path)
    df_aptos['equipo_num'] = df_aptos['NombreEquipo'].str.extract(r'(\d+)').astype(float)
    df_aptos = df_aptos[df_aptos['equipo_num'].isin([25, 26, 27])].copy()
    df_aptos['imo_id_clean'] = df_aptos['IdentificacionIMO'].astype(str).str.strip().str.replace('.0', '', regex=False)

    imo_ids = df_aptos['imo_id_clean'].unique()

    # Buscar IMOs como participantes en reportes
    imo_info = {}
    imo_como_px = df_reportes[df_reportes['id_clean'].isin(imo_ids)]
    for _, row in imo_como_px.iterrows():
        imo_id = row['id_clean']
        if imo_id not in imo_info:
            correo = row.get('Correo', None)
            tel = row.get('TelefonoMovil', None)
            nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip().title()
            if correo and pd.notna(correo) and '@' in str(correo):
                imo_info[imo_id] = {'nombre': nombre, 'correo': str(correo).strip(), 'telefono': str(tel).strip() if pd.notna(tel) else ''}

    # Para los que faltan, buscar por participante en reportes
    for _, apto in df_aptos.iterrows():
        imo_id = apto['imo_id_clean']
        if imo_id in imo_info:
            continue
        px_id = str(apto.get('Identificación', '')).strip().replace('.0', '')
        if not px_id:
            continue
        match = df_reportes[df_reportes['id_clean'] == px_id]
        if len(match) > 0:
            row = match.iloc[0]
            nombre_imo = str(row.get('NombreIMO', '')).strip().title()
            tel_imo = str(row.get('TelefonoIMO', '')).strip()
            if nombre_imo and nombre_imo != 'Nan':
                imo_info[imo_id] = {'nombre': nombre_imo, 'correo': '', 'telefono': tel_imo if tel_imo != 'nan' else ''}
    
    # Intentar encontrar correo para los que solo tienen teléfono
    for imo_id, info in imo_info.items():
        if info['correo']:
            continue
        match = df_reportes[df_reportes['id_clean'] == imo_id]
        if len(match) > 0:
            for _, row in match.iterrows():
                correo = row.get('Correo', None)
                if correo and pd.notna(correo) and '@' in str(correo):
                    info['correo'] = str(correo).strip()
                    nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip().title()
                    if nombre:
                        info['nombre'] = nombre
                    break

    return imo_info, df_aptos

def generar_html_correo(nombre_imo, lista_participantes_html):
    return f"""
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; color: #222; max-width: 650px; margin: 0 auto; line-height: 1.6;">
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 25px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: #f0c040; margin: 0; font-size: 22px;">CREAR PODER SIN LÍMITES</h1>
        <p style="color: #ccc; margin: 5px 0 0 0; font-size: 13px;">Tu gente está lista. Solo falta tu llamado.</p>
    </div>
    
    <div style="padding: 25px 30px; background: #fafafa; border: 1px solid #e0e0e0;">
        <p>Estimado/a <strong>{nombre_imo}</strong>:</p>
        
        <p>En CREAR Poder Sin Límites no creemos en la suerte. Creemos en el contexto sostenido por la presencia del líder.</p>
        
        <p>Has hecho tu trabajo de forma impecable: <strong>tu gente está inscrita, su entrenamiento en C1 está 100% pagado.</strong> Les abriste la puerta. Ese es el primer acto de liderazgo.</p>
        
        <p>Pero el acto final, el que verdaderamente crea poder, ocurre cuando ellos cruzan la puerta, toman su asiento y eligen no levantarse hasta terminar.</p>
        
        <p style="font-size: 18px; text-align: center; color: #c0392b; font-weight: bold;">Hoy, ese acto final depende de ti.</p>
        
        <p>Tu equipo tiene el asiento reservado. El contexto está creado. Nuestro equipo de facilitadores y logística está listo para recibirlos. Solo falta una variable: <strong>tu influencia ejecutiva</strong> para que nadie se quede en el intento.</p>
        
        <div style="background: #fff3cd; border-left: 4px solid #f0c040; padding: 15px; margin: 20px 0; border-radius: 0 6px 6px 0;">
            <h3 style="margin: 0 0 10px 0; color: #856404;">🎯 Tu misión en las próximas 48 horas:</h3>
            <p style="margin: 5px 0;">Conecta con tu gente hoy mismo. No asumas. No delegues. <strong>Tú eres el puente.</strong></p>
            <p style="margin: 5px 0;">Diles que están listos y <strong>pídeles que escriban INMEDIATAMENTE a su coordinadora asignada</strong> para confirmar su asistencia final.</p>
        </div>
        
        <div style="background: #e8f4fd; border: 1px solid #b8daff; padding: 15px; border-radius: 6px; margin: 20px 0;">
            <h3 style="margin: 0 0 10px 0; color: #004085;">📋 Tu lista de personas aptas y su coordinadora:</h3>
            <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
                <tr style="background: #004085; color: white;">
                    <th style="padding: 8px; text-align: left; border-radius: 4px 0 0 0;">Participante</th>
                    <th style="padding: 8px; text-align: left;">Equipo</th>
                    <th style="padding: 8px; text-align: left; border-radius: 0 4px 0 0;">Debe escribir a</th>
                </tr>
                {lista_participantes_html}
            </table>
        </div>
        
        <p>Hazle a tu gente esta única pregunta: <em>"¿A qué hora te recojo o nos encontramos este viernes 29? Tu asiento te está esperando. ¡Escríbele a tu coordinadora para confirmarlo!"</em></p>
        
        <p>Consigue su compromiso explícito y responde a este mismo correo con un simple <strong>"Listo"</strong> cuando todos hayan contactado a coordinación.</p>
        
        <p><strong>¿Por qué es crucial que lo hagas TÚ?</strong></p>
        <p>Porque recuerdas nuestro manifiesto: <em>"Sostenemos el contexto con nuestra presencia y entregamos resultados, no excusas. Somos parte de algo más grande que nosotros."</em></p>
        
        <p>Un mensaje masivo nuestro no tiene el peso de <strong>TU llamado personal</strong>. Tu llamado es el que transforma una inscripción en una experiencia. Es el que convierte una posibilidad en un resultado.</p>
        
        <div style="background: #1a1a2e; color: white; padding: 20px; border-radius: 6px; margin: 20px 0; text-align: center;">
            <h3 style="color: #f0c040; margin: 0 0 10px 0;">📅 Detalles del Entrenamiento</h3>
            <p style="margin: 5px 0;">📅 Fecha: <strong>Viernes 29 al Domingo 31 de Mayo 2026</strong></p>
            <p style="margin: 5px 0;">📍 Sede: <strong>Hotel BTH Boutique Concept</strong></p>
            <p style="margin: 5px 0;">📍 Av. Guardia Civil 727, San Borja</p>
            <p style="margin: 5px 0;">🎯 Check-in / Registro: <strong>9:00 AM (Viernes)</strong></p>
        </div>
        
        <p style="text-align: center; font-style: italic; color: #555;">Tu próximo paso es ahora. Contacta a tu gente. Sienta a tu equipo.</p>
        <p style="text-align: center; font-weight: bold; color: #c0392b;">Con la certeza de quien sabe que el líder no espera que ocurra, sino que hace que ocurra.</p>
    </div>
    
    <div style="background: #1a1a2e; padding: 15px; text-align: center; border-radius: 0 0 8px 8px;">
        <p style="color: #f0c040; font-weight: bold; margin: 0;">CREAR Poder Sin Límites Perú</p>
        <p style="color: #888; font-size: 12px; margin: 5px 0 0 0;">#SoyCreadorCuántico</p>
    </div>
</body>
</html>
"""

def ejecutar():
    print("="*70)
    print("  ENVÍO DE CORREOS A IMOS - PARTICIPANTES APTOS E25/E26/E27")
    print("="*70)

    imo_info, df_aptos = cargar_imos_con_correo()

    # Filtrar solo IMOs con correo
    imos_con_correo = {k: v for k, v in imo_info.items() if v['correo']}
    print(f"IMOs con correo a enviar: {len(imos_con_correo)}")

    # Conectar SMTP
    print("Conectando a Gmail SMTP...")
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(EMAIL_USER, EMAIL_PASS)
    print("Conectado.\n")

    enviados = 0
    errores = 0
    log = open(r'C:\Users\josem\Downloads\bot-cpsl-review\reporte_correos_imos_aptos.txt', 'w', encoding='utf-8')
    log.write("REPORTE DE CORREOS A IMOS - APTOS E25/E26/E27\n")
    log.write("="*70 + "\n\n")

    for imo_id, info in sorted(imos_con_correo.items()):
        nombre_imo = info['nombre']
        correo_imo = info['correo']

        # Participantes de este IMO
        pxs = df_aptos[df_aptos['imo_id_clean'] == imo_id]
        if len(pxs) == 0:
            continue

        # Generar filas de la tabla HTML
        filas_html = ""
        for i, (_, px) in enumerate(pxs.iterrows()):
            nombre_px = f"{px['NombreCompleto']} {px['ApellidoCompleto']}".strip().title()
            equipo = px['NombreEquipo']
            coord_key = str(px['Usuario Registro']).strip().lower()
            coord = COORDINADORAS.get(coord_key, {'nombre': coord_key, 'telefono': '?'})
            bg = '#f8f9fa' if i % 2 == 0 else '#ffffff'
            filas_html += f'<tr style="background:{bg};"><td style="padding:8px;border-bottom:1px solid #dee2e6;">{nombre_px}</td><td style="padding:8px;border-bottom:1px solid #dee2e6;">{equipo}</td><td style="padding:8px;border-bottom:1px solid #dee2e6;"><strong>{coord["nombre"]}</strong> ({coord["telefono"]})</td></tr>\n'

        html = generar_html_correo(nombre_imo, filas_html)

        msg = MIMEMultipart()
        msg['From'] = f"Crear Poder Sin Limites <{EMAIL_USER}>"
        msg['To'] = correo_imo
        msg['Subject'] = "Tu gente esta lista y 100% pagada. Asegura su asiento hoy."
        msg.attach(MIMEText(html, 'html'))

        print(f"Enviando a {nombre_imo} ({correo_imo}) [{len(pxs)} PXs]... ", end="", flush=True)
        try:
            server.send_message(msg)
            print("[OK]", flush=True)
            log.write(f"[EXITO] {correo_imo} - {nombre_imo} ({len(pxs)} participantes)\n")
            enviados += 1
        except Exception as e:
            print(f"[ERROR: {e}]", flush=True)
            log.write(f"[ERROR] {correo_imo} - {nombre_imo}: {e}\n")
            errores += 1
        
        time.sleep(2)

    server.quit()
    log.write(f"\n{'='*70}\nRESUMEN: Enviados={enviados} | Errores={errores}\n")
    log.close()

    print(f"\n{'='*70}")
    print(f"  RESUMEN: Enviados={enviados} | Errores={errores}")
    print(f"{'='*70}")
    print("Reporte: reporte_correos_imos_aptos.txt")

if __name__ == "__main__":
    ejecutar()
