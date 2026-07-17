"""
MOTOR DE BIENVENIDA OFICIAL v2 — CPSL E28
==========================================
Email HTML premium con tablas (compatible Gmail/Outlook/iPhone/Android).
Logo embebido como CID (no base64 inline).
Contrato PDF firmado como único adjunto.
"""

import smtplib, os, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from datetime import datetime
from pathlib import Path
from fpdf import FPDF
from database import SessionLocal, TrazabilidadPX, LogEnvio
from crear_email_core import EmailEngine

engine = EmailEngine()

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

engine.user = EMAIL_USER
engine.password = EMAIL_PASS

BASE_DIR = Path(__file__).parent
HTML_TEMPLATE = BASE_DIR / "templates" / "base_enterprise.html"
FIRMA_PATH    = Path(r"C:\Users\josem\Downloads\Imágenes\Firmas\FIRMA JOSE SANCHEZ.png")
LOGO_PATH     = BASE_DIR / "assets" / "logo_principal.png"


def generar_html_email(px: dict) -> str:
    template_path = os.path.join(os.path.dirname(__file__), "templates", "base_enterprise.html")
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    contenido_html = f"""
<p>Has tomado la decisión de no conformarte. Su admisión al <b>CAPÍTULO 1 — EQUIPO {px['equipo']} LIMA</b> representa el inicio de un proceso de transformación de alto rendimiento.</p>

<div class="info-box" style="background-color: #fcfcfc; border-left: 4px solid #b49632; padding: 25px; margin: 30px 0; border-radius: 0 8px 8px 0;">
    <h3 style="color: #1a1a2e; margin: 0; font-size: 14px; text-transform: uppercase; letter-spacing: 1px;">Registro de Inscripción</h3>
    <p style="margin: 8px 0; font-size: 15px;">Programa: <b>Capítulo 1 — Equipo {px['equipo']}</b></p>
    <p style="margin: 8px 0; font-size: 15px;">Estado: <span style="color: #27ae60;">VALIDADO ✅</span></p>
    <p style="margin: 8px 0; font-size: 15px;">ID Institucional: {px['codigo_px']}</p>
</div>

<p>Adjunto a esta comunicación oficial encontrará su <b>Contrato de Términos y Condiciones</b>, el cual ha sido validado mediante su aceptación digital. Este documento es fundamental para su expediente de participación.</p>

<table border="0" cellpadding="0" cellspacing="0" width="100%">
    <tr>
        <td align="center" style="padding: 20px 0;">
            <a href="https://crearglobal.com" style="background-color: #b49632; color: #ffffff; padding: 15px 35px; text-decoration: none; border-radius: 4px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Acceder a mi Portal</a>
        </td>
    </tr>
</table>
"""
    placeholders = {
        "GREETING": f"ADMISIÓN OFICIAL — {px['nombre'].upper()}",
        "CONTENT": contenido_html
    }
    
    try:
        return engine.load_template(template_path, placeholders)
    except:
        return contenido_html


class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 16)
        self.cell(0, 12, 'CREAR PODER SIN LIMITES', 0, 1, 'C')
        self.set_font('Helvetica', '', 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 5, 'P E R U  .  G L O B A L  2 0 2 6', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(3)
        self.set_draw_color(180, 150, 50)
        self.set_line_width(0.5)
        self.line(70, self.get_y(), 140, self.get_y())
        self.ln(5)
        self.set_font('Helvetica', 'B', 11)
        self.cell(0, 8, 'CONTRATO DE TERMINOS Y CONDICIONES DEL SERVICIO', 0, 1, 'C')
        self.set_font('Helvetica', 'B', 10)
        self.cell(0, 6, 'PROGRAMA CAPITULO UNO', 0, 1, 'C')
        self.ln(3)
        self.set_font('Helvetica', '', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 5, 'CREACION CUANTICA E.I.R.L. - RUC 20612592811', 0, 1, 'C')
        self.set_text_color(0, 0, 0)
        self.ln(8)
    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(150, 150, 150)
        self.cell(0, 5, f'CREACION CUANTICA E.I.R.L. | RUC 20612592811 | Pag. {self.page_no()}', 0, 0, 'C')
    def seccion_titulo(self, t):
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(40, 40, 40)
        self.cell(0, 8, t, 0, 1)
        self.set_draw_color(180, 150, 50)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)
    def dato_fila(self, label, valor):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(80, 80, 80)
        self.cell(55, 6, label, 0, 0)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(30, 30, 30)
        self.cell(0, 6, valor, 0, 1)


def generar_contrato_pdf(px, path):
    pdf = ContratoPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    fecha = datetime.now().strftime("%d/%m/%Y")
    hora  = datetime.now().strftime("%H:%M:%S")
    pdf.set_font('Helvetica', 'B', 13)
    pdf.cell(0, 10, f'EQUIPO  {px["equipo"]}', 0, 1, 'C')
    pdf.ln(6)
    pdf.seccion_titulo('I. DATOS DEL PARTICIPANTE')
    for l, v in [
        ('Nombres y Apellidos:', px["nombre"]),
        ('Documento de Identidad:', px["documento"]),
        ('Codigo de Participante:', px["codigo_px"]),
        ('Correo Electronico:', px.get("correo", "")),
        ('Telefono:', px.get("telefono", "")),
        ('Fecha de Inscripcion:', px.get("fecha_inscripcion", fecha)),
        ('Hora de Registro:', px.get("hora_inscripcion", hora)),
        ('Programa:', f'CAPITULO UNO - EQUIPO {px["equipo"]}'),
        ('Horario Referencial:', 'Viernes, sabado y domingo de 9:00 AM a 10:00 PM aprox.'),
        ('Modalidad de Aceptacion:', 'ACEPTACION DIGITAL MEDIANTE FORMULARIO ELECTRONICO'),
        ('Estado:', 'ACEPTADO'),
    ]:
        pdf.dato_fila(l, v)
    pdf.ln(6)
    pdf.seccion_titulo('II. DECLARACION DE ACEPTACION DIGITAL')
    pdf.set_font('Helvetica', '', 9)
    pdf.multi_cell(0, 5, 'El participante declara haber leido integramente, comprendido y aceptado libre y voluntariamente los presentes Terminos y Condiciones del Servicio al momento de completar su inscripcion en el sistema oficial de CREACION CUANTICA E.I.R.L.')
    pdf.ln(2)
    pdf.multi_cell(0, 5, 'La aceptacion electronica realizada mediante el formulario oficial de inscripcion constituye manifestacion valida de voluntad conforme a la legislacion peruana aplicable, en particular al Codigo Civil (D.Leg. N 295) y la Ley N 27291 sobre contratos por medios electronicos.')
    pdf.ln(6)
    pdf.seccion_titulo('III. TERMINOS Y CONDICIONES DEL SERVICIO')
    for t, tx in [
        ('1. NATURALEZA DEL SERVICIO', 'CREACION CUANTICA E.I.R.L. (en adelante "la Empresa") presta un servicio de formacion, desarrollo personal y liderazgo a traves del programa denominado "Capitulo Uno", de caracter presencial e intensivo, durante tres jornadas consecutivas (viernes, sabado y domingo). La metodologia es progresiva, acumulativa y de participacion total.'),
        ('2. OBLIGACIONES DEL PARTICIPANTE', 'El participante se compromete a asistir puntualmente a la totalidad de las jornadas del entrenamiento, en los horarios establecidos. No se permitira el retiro anticipado antes del cierre diario, la inasistencia parcial a dinamicas criticas, el ingreso tardio reiterado ni cualquier conducta que interrumpa el proceso colectivo. El incumplimiento de estas condiciones podra derivar en la restriccion de la permanencia en el programa sin derecho a reembolso.'),
        ('3. POLITICA DE CANCELACION Y REEMBOLSOS', 'El importe abonado por concepto de inscripcion al programa es de caracter no reembolsable una vez iniciado el entrenamiento. Ante cancelaciones previas al inicio, la Empresa evaluara cada caso de forma individual conforme a sus politicas internas vigentes, pudiendo ofrecer la reprogramacion de la participacion para un ciclo posterior.'),
        ('4. CONFIDENCIALIDAD DEL CONTENIDO', 'El participante se compromete a mantener la confidencialidad del contenido metodologico, dinamicas, materiales y experiencias compartidas dentro del entrenamiento. Esta expresamente prohibida la reproduccion, difusion, grabacion o comercializacion, parcial o total, del contenido del programa sin autorizacion escrita de la Empresa.'),
        ('5. PROPIEDAD INTELECTUAL', 'Todos los materiales, metodologias, denominaciones, marcas y contenidos del programa Capitulo Uno son propiedad exclusiva de CREAR GLOBAL y/o CREACION CUANTICA E.I.R.L. El acceso al programa no otorga al participante ningun derecho de uso, reproduccion o explotacion de dichos activos intelectuales.'),
        ('6. RESPONSABILIDAD Y PARTICIPACION VOLUNTARIA', 'La participacion en el programa es estrictamente voluntaria. El participante asume plena responsabilidad sobre las decisiones, compromisos y acciones que adopte como resultado de su experiencia en el entrenamiento. La Empresa no asume responsabilidad por resultados individuales, dado que el impacto del programa depende de la disposicion, compromiso y aplicacion personal de cada participante.'),
        ('7. CONDUCTA Y COMUNIDAD', 'El participante se obliga a mantener en todo momento un trato respetuoso hacia los demas participantes, el equipo de coordinacion, los entrenadores y el personal de la Empresa. Conductas que atenten contra el contexto del entrenamiento, la integridad de los participantes o la reputacion de la Empresa constituiran causa justificada de retiro inmediato del programa.'),
        ('8. PROTECCION DE DATOS PERSONALES', 'Los datos personales del participante seran tratados con estricta confidencialidad, utilizados unicamente para la gestion del programa y comunicaciones relacionadas con el servicio contratado, de conformidad con la Ley N 29733 - Ley de Proteccion de Datos Personales y su reglamento.'),
        ('9. JURISDICCION Y LEGISLACION APLICABLE', 'El presente contrato se rige por la legislacion peruana. Ante cualquier controversia derivada de su interpretacion o ejecucion, las partes se someten a la competencia de los jueces y tribunales de la ciudad de Lima, Peru, renunciando expresamente a cualquier otro fuero que pudiera corresponderles.'),
    ]:
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(0, 5, t, 0, 1)
        pdf.set_font('Helvetica', '', 8)
        pdf.multi_cell(0, 4.5, tx)
        pdf.ln(2)
    pdf.ln(4)
    pdf.seccion_titulo('IV. CONSTANCIA DE ACEPTACION DIGITAL')
    pdf.set_font('Helvetica', '', 8)
    for c in [
        'Documento generado automaticamente por el sistema interno de inscripcion de CREACION CUANTICA E.I.R.L.',
        'Aceptacion registrada digitalmente por el participante mediante el formulario oficial.',
        'Documento asociado al expediente interno del participante con fuerza contractual valida.',
        'Emitido al momento de completar el proceso de inscripcion en la plataforma oficial.',
    ]:
        pdf.cell(0, 5, f'*  {c}', 0, 1)
    pdf.ln(6)
    pdf.set_font('Helvetica', '', 8)
    pdf.multi_cell(0, 5, 'El participante declara haber leido integramente el presente documento y haber aceptado electronicamente los terminos y condiciones durante el proceso oficial de inscripcion del programa. Este documento forma parte del registro digital interno de CREACION CUANTICA E.I.R.L.')
    pdf.ln(6)
    pdf.set_draw_color(180, 150, 50)
    pdf.set_line_width(0.3)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(0, 6, 'ACEPTACION DIGITAL REGISTRADA', 0, 1, 'C')
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 5, px["nombre"], 0, 1, 'C')
    pdf.cell(0, 5, f'DNI: {px["documento"]}', 0, 1, 'C')
    pdf.cell(0, 5, f'Fecha: {px.get("fecha_inscripcion", fecha)}', 0, 1, 'C')
    pdf.cell(0, 5, f'Hora: {px.get("hora_inscripcion", hora)}', 0, 1, 'C')
    pdf.ln(4)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(8)
    pdf.seccion_titulo('V. FIRMAS')
    pdf.ln(3)
    pdf.set_font('Helvetica', '', 8)
    pdf.cell(95, 5, 'Por el participante:', 0, 0)
    pdf.cell(95, 5, 'Por la Empresa:', 0, 1)
    pdf.ln(3)
    y_firma = pdf.get_y()
    pdf.set_font('Helvetica', 'I', 8)
    pdf.cell(95, 5, '[Aceptacion digital registrada]', 0, 1)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(95, 4, px["nombre"], 0, 1)
    pdf.cell(95, 4, f'DNI: {px["documento"]}', 0, 1)
    if os.path.exists(FIRMA_PATH):
        pdf.image(FIRMA_PATH, x=115, y=y_firma - 5, w=55)
    pdf.set_xy(105, y_firma + 20)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(95, 4, 'Jose Sanchez', 0, 1)
    pdf.set_x(105)
    pdf.cell(95, 4, 'Representante Legal', 0, 1)
    pdf.set_x(105)
    pdf.cell(95, 4, 'CREACION CUANTICA E.I.R.L.', 0, 1)
    pdf.ln(10)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 4, 'CREACION CUANTICA E.I.R.L.  |  RUC 20612592811', 0, 1, 'C')
    pdf.cell(0, 4, 'crearpodersinlimitesperu@gmail.com  |  Lima, Peru', 0, 1, 'C')
    pdf.cell(0, 4, '(c) 2026 CREAR Global - Documento confidencial. Todos los derechos reservados.', 0, 1, 'C')
    pdf.output(path)
    print(f"   [OK] PDF generado: ({os.path.getsize(path)//1024} KB)")


def enviar_bienvenida(px, destino, cc=None, es_prueba=False):
    label = "PRUEBA" if es_prueba else "PRODUCCION"
    print(f"--- DESPACHO OFICIAL v2 ({label}) ---")

    html = generar_html_email(px)
    print("   [OK] HTML premium estandarizado generado.")

    nombre_limpio = px["nombre"].replace(" ", "_").replace("Í", "I").replace("Ó", "O")
    pdf_path = os.path.join(os.path.dirname(__file__), f"Contrato_{nombre_limpio}.pdf")
    generar_contrato_pdf(px, pdf_path)

    subject = f"Confirmación Oficial — Capítulo 1 | Equipo {px['equipo']} Lima"
    
    success, msg = engine.send_enterprise_email(
        to=destino,
        subject=subject,
        body_html=html,
        attachments=[pdf_path],
        px_id=px.get("id", 0),
        metadata={"event": "BIENVENIDA_V2_ENTERPRISE"}
    )
    
    if success:
        print(f"   [OK] Correo enviado a {destino}")
    else:
        print(f"   [ERR] {msg}")


if __name__ == "__main__":
    rocio = {
        "nombre": "ROCIO JARA AMPUERO",
        "documento": "07938881",
        "codigo_px": "07938881",
        "equipo": "E28",
        "correo": "rjampuero@gmail.com",
        "telefono": "",
        "fecha_inscripcion": datetime.now().strftime("%d/%m/%Y"),
        "hora_inscripcion": datetime.now().strftime("%H:%M:%S"),
    }
    # Prueba solo a Jose
    enviar_bienvenida(rocio, "jose.sanchez@crearpsl.com", es_prueba=True)
