"""
MOTOR DE BIENVENIDA INSTITUCIONAL - ENTRENADORES CREAR
=======================================================
Genera un PDF premium institucional para dar la bienvenida
a entrenadores que viajan a Lima.

Fuentes:
  - entrenadores_data.json (datos del entrenador, vuelos, hotel)
  - CALENDARIO CREAR 2026.xlsx (programación)
  - Logo Crear fb.png (logo institucional)
  - FIRMA JOSE SANCHEZ.png (firma digital)
"""

import json, os, smtplib
from fpdf import FPDF
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# ── Rutas ──
BASE_DIR     = os.path.dirname(__file__)
DATA_PATH    = os.path.join(BASE_DIR, "entrenadores_data.json")
LOGO_PATH    = r"C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png"
FIRMA_PATH   = r"C:\Users\josem\Downloads\Imágenes\Firmas\FIRMA JOSE SANCHEZ.png"
OUTPUT_DIR   = os.path.join(BASE_DIR, "pdfs_entrenadores")
EMAIL_USER   = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS   = "bgsl xjus xsmn pzqd"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def cargar_datos():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class BienvenidaPDF(FPDF):
    """PDF premium institucional para entrenadores."""

    def header(self):
        # Logo centrado
        if os.path.exists(LOGO_PATH):
            self.image(LOGO_PATH, x=85, y=8, w=40)
            self.set_y(46)
        # Línea dorada
        self.set_draw_color(180, 150, 50)
        self.set_line_width(0.6)
        self.line(20, self.get_y(), 190, self.get_y())
        self.ln(6)


    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', '', 6)
        self.set_text_color(140, 140, 140)
        self.cell(0, 4, 'CREACION CUANTICA E.I.R.L. | RUC 20612592811 | Documento interno y confidencial', 0, 1, 'C')
        self.cell(0, 4, f'Pag. {self.page_no()} | Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}', 0, 0, 'C')

    def seccion(self, titulo, icono=""):
        self.ln(4)
        self.set_font('Helvetica', 'B', 11)
        self.set_text_color(25, 60, 120)
        self.cell(0, 8, f'{icono}  {titulo}', 0, 1)
        self.set_draw_color(180, 150, 50)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(30, 30, 30)

    def dato(self, label, valor):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(90, 90, 90)
        self.cell(58, 6, label, 0, 0)
        self.set_font('Helvetica', '', 9)
        self.set_text_color(20, 20, 20)
        self.cell(0, 6, str(valor), 0, 1)

    def parrafo(self, texto, size=9):
        self.set_font('Helvetica', '', size)
        self.set_text_color(40, 40, 40)
        self.multi_cell(0, 5, texto)
        self.ln(2)

    def nota(self, texto):
        self.set_fill_color(255, 248, 230)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(100, 80, 30)
        self.cell(0, 6, f'  NOTA: {texto}', 0, 1, fill=True)
        self.ln(3)
        self.set_text_color(30, 30, 30)


def generar_pdf_entrenador(entrenador, datos_globales):
    """Genera el PDF de bienvenida para un entrenador."""
    pdf = BienvenidaPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    venues = datos_globales["venues"]
    contactos = datos_globales["contactos_crear_lima"]
    hotel_key = entrenador.get("hotel", "jose_antonio_deluxe")
    hotel = venues.get(hotel_key, venues["jose_antonio_deluxe"])
    horarios = entrenador.get("horarios", {})

    # ── TITULO PRINCIPAL ──
    pdf.set_font('Helvetica', 'B', 18)
    pdf.set_text_color(25, 60, 120)
    pdf.cell(0, 10, 'CREAR PODER SIN LIMITES', 0, 1, 'C')
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 5, 'P E R U  .  G L O B A L  2 0 2 6', 0, 1, 'C')
    pdf.ln(3)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(180, 150, 50)
    pdf.cell(0, 8, 'BIENVENIDA INSTITUCIONAL - ENTRENADOR', 0, 1, 'C')
    pdf.ln(6)

    # ── SALUDO PERSONALIZADO ──
    pdf.set_font('Helvetica', '', 10)
    pdf.set_text_color(40, 40, 40)
    nombre = entrenador["nombre"]
    programa = entrenador.get("programa", "CAPITULO UNO")
    equipo = entrenador.get("equipo", "")

    pdf.parrafo(
        f'Querido(a) {nombre},', size=11
    )
    pdf.parrafo(
        f'Bienvenido(a) a Lima! Estamos felices de recibirte en CREAR para '
        f'entrenar al Equipo {equipo} en su {programa}.'
    )
    if "MAESTRIA" in programa.upper() or "MJ" in programa.upper():
        pdf.parrafo(
            'Maestria del Juego es una fase intensiva de alto rendimiento donde los participantes '
            'rompen barreras y eligen una version extraordinaria de si mismos. Tu experiencia es '
            'fundamental para llevarlos a atravesar.'
        )
    elif "CAPITULO DOS" in programa.upper() or "C2" in programa.upper():
        pdf.parrafo(
            'Capitulo Dos es una fase intensiva donde los participantes rompen barreras y eligen '
            'el alto rendimiento. Tu experiencia es fundamental para llevarlos a atravesar.'
        )
    else:
        pdf.parrafo(
            'Capitulo Uno es la puerta de entrada a la experiencia CREAR. Tu presencia como entrenador '
            'es fundamental para que los participantes vivan una transformacion poderosa.'
        )

    # ── SECCION 1: LOGISTICA DE VUELO - LLEGADA ──
    vuelo_llegada = entrenador.get("vuelo_llegada", {})
    pdf.seccion("LOGISTICA DE VUELO - LLEGADA")
    pdf.dato("Llegada a Lima (LIM):", f'{vuelo_llegada.get("fecha", "Por confirmar")}, {vuelo_llegada.get("hora", "")}')
    pdf.dato("Aerolinea:", vuelo_llegada.get("aerolinea", "Por confirmar"))
    pdf.dato("Referencia de Vuelo:", vuelo_llegada.get("referencia", "Por confirmar"))
    pdf.ln(2)

    # ── SECCION 2: HOSPEDAJE ──
    pdf.seccion("HOSPEDAJE")
    pdf.dato("Hotel:", hotel["nombre"])
    pdf.dato("Direccion:", hotel.get("direccion", ""))
    pdf.dato("Telefono:", hotel.get("telefono", ""))
    pdf.nota("El hospedaje esta incluido. Mismo lugar del entrenamiento.")
    pdf.ln(2)

    # ── SECCION 3: ENTRENAMIENTO ──
    pdf.seccion("ENTRENAMIENTO")
    fds = entrenador.get("fds", "")
    pdf.dato("Programa:", f'{programa} ({fds})' if fds else programa)
    pdf.dato("Equipo:", f'Equipo {equipo}')
    pdf.dato("Lugar:", f'{hotel["nombre"]}, {hotel.get("salon", "")}')

    fechas = entrenador.get("fechas_entrenamiento", [])
    if fechas:
        pdf.dato("Fechas:", " / ".join(fechas))
    pdf.ln(2)

    # ── SECCION 4: HORARIOS CLAVE ──
    pdf.seccion("HORARIOS CLAVE")
    if horarios:
        if horarios.get("grounding"):
            pdf.dato("Grounding con Aliados:", horarios["grounding"])
        if horarios.get("registro"):
            pdf.dato("Mesa de Registro:", horarios["registro"])
        if horarios.get("inicio"):
            pdf.dato("Inicio del Entrenamiento:", horarios["inicio"])
        if horarios.get("cierre_diario"):
            pdf.dato("Cierre diario estimado:", horarios["cierre_diario"])
    else:
        pdf.dato("Grounding con Aliados:", "12:00 PM")
        pdf.dato("Mesa de Registro:", "1:00 PM")
        pdf.dato("Inicio del Entrenamiento:", "2:00 PM")
        pdf.dato("Cierre diario estimado:", "10:00 PM aprox.")
    pdf.ln(2)

    # ── SECCION 5: LOGISTICA DE VUELO - SALIDA ──
    vuelo_salida = entrenador.get("vuelo_salida", {})
    pdf.seccion("LOGISTICA DE VUELO - SALIDA")
    pdf.dato("Salida de Lima (LIM):", f'{vuelo_salida.get("fecha", "Por confirmar")}, {vuelo_salida.get("hora", "")}')
    pdf.dato("Aerolinea:", vuelo_salida.get("aerolinea", "Por confirmar"))
    pdf.dato("Referencia de Vuelo:", vuelo_salida.get("referencia", "Por confirmar"))
    pdf.ln(2)

    # ── SECCION 6: INDICACIONES DEL VENUE ──
    pdf.seccion("INDICACIONES DEL VENUE")
    pdf.parrafo(
        'Los espacios que usamos son rentados y es vital adaptarnos a sus reglas. '
        'Te pedimos tu total colaboracion para respetar los siguientes lineamientos:'
    )
    notas_venue = hotel.get("notas", "")
    if notas_venue:
        pdf.nota(notas_venue)
    pdf.parrafo(
        '- Respetar los limites de ruido (decibeles) establecidos por el hotel.\n'
        '- Horario de cierre maximo: 11:00 PM.\n'
        '- Mantener el orden y limpieza de los espacios utilizados.\n'
        '- Coordinar con el equipo local cualquier necesidad adicional.',
        size=8
    )
    pdf.ln(2)

    # ── SECCION 7: CONTACTOS CREAR LIMA ──
    pdf.seccion("CONTACTOS CREAR LIMA")
    sub = contactos.get("gerente", {"nombre": "José Sánchez", "telefono": "+51 919 563 284"})
    pdf.dato(f'{sub["nombre"]} (Gerente):', sub["telefono"])
    for coord in contactos.get("coordinadoras", []):
        pdf.dato(f'{coord["nombre"]} ({coord["rol"]}):', coord["telefono"])
    pdf.ln(4)

    # ── CIERRE EMOCIONAL ──
    pdf.set_draw_color(180, 150, 50)
    pdf.set_line_width(0.3)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(6)

    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(0, 6,
        'Agradecemos tu compromiso y dedicacion. Te deseamos un excelente viaje '
        f'y un {programa} impactante!'
    )
    pdf.ln(4)

    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 6, 'Con gratitud,', 0, 1)
    pdf.set_font('Helvetica', '', 10)
    pdf.cell(0, 6, 'El Equipo de CREAR LIMA', 0, 1)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(25, 60, 120)
    pdf.cell(0, 6, '#SOYCREADORCUANTICO', 0, 1)
    pdf.ln(6)

    # ── FIRMA JOSE SANCHEZ ──
    pdf.ln(8) # Espacio antes de la firma
    y_firma = pdf.get_y()
    
    if os.path.exists(FIRMA_PATH):
        pdf.image(FIRMA_PATH, x=25, y=y_firma, w=40)
        pdf.set_y(y_firma + 16)
    else:
        pdf.set_y(y_firma + 16)
        
    pdf.set_draw_color(180, 150, 50)
    pdf.set_line_width(0.3)
    pdf.line(15, pdf.get_y(), 85, pdf.get_y())
    pdf.ln(2)
    
    pdf.set_x(15)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(70, 4, 'José Sánchez - Gerente CREAR Lima', 0, 1, 'C')
    pdf.set_x(15)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(70, 4, 'CREACION CUANTICA E.I.R.L. | RUC 20612592811', 0, 1, 'C')

    # ── Guardar ──
    nombre_limpio = nombre.replace(" ", "_").upper()
    filename = f"Bienvenida_Entrenador_{nombre_limpio}_{equipo}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)
    pdf.output(filepath)
    size_kb = os.path.getsize(filepath) / 1024
    print(f"   [OK] PDF generado: {filename} ({size_kb:.0f} KB)")
    return filepath


def generar_html_email_entrenador(entrenador):
    html_path = r"C:\Users\josem\Downloads\files\CREAR_email_premium_entrenadores.html"
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    
    html = html.replace("{{NOMBRE_COMPLETO}}", entrenador["nombre"])
    html = html.replace("{{PROGRAMA}}", entrenador.get("programa", "CAPITULO UNO"))
    html = html.replace("{{EQUIPO}}", entrenador.get("equipo", ""))
    return html

def enviar_bienvenida_entrenador(entrenador, pdf_path, cc=None):
    """Envía el PDF por email al entrenador usando HTML premium."""
    destino = entrenador.get("email", "")
    if not destino or destino == "POR DEFINIR":
        print(f"   [SKIP] Sin email real para este entrenador ({destino}). Solo se generó el PDF.")
        return

    nombre = entrenador["nombre"]
    programa = entrenador.get("programa", "")
    equipo = entrenador.get("equipo", "")

    msg = MIMEMultipart("related")
    msg['From'] = f"Creación Cuántica E.I.R.L. <{EMAIL_USER}>"
    msg['To'] = destino
    if cc:
        msg['Cc'] = cc
    msg['Subject'] = f"Bienvenida Oficial — {programa} | Equipo {equipo} | CREAR Lima"

    # Cuerpo HTML
    html = generar_html_email_entrenador(entrenador)
    msg_alt = MIMEMultipart("alternative")
    msg.attach(msg_alt)
    msg_alt.attach(MIMEText(html, 'html'))

    # Logo CID
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as f:
            from email.mime.image import MIMEImage
            logo = MIMEImage(f.read())
            logo.add_header("Content-ID", "<logo_crear>")
            logo.add_header("Content-Disposition", "inline", filename="logo.png")
            msg.attach(logo)


    # Adjuntar PDF
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                f'attachment; filename="Bienvenida Institucional - {nombre} - {equipo}.pdf"')
            msg.attach(part)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
        print(f"   [OK] Email enviado a {destino}" + (f" CC:{cc}" if cc else ""))
    except Exception as e:
        print(f"   [ERR] {e}")


def ejecutar_todos():
    """Genera PDFs y envía emails para todos los entrenadores."""
    datos = cargar_datos()
    entrenadores = datos.get("entrenadores", [])

    print(f"\n{'='*60}")
    print(f"  MOTOR DE BIENVENIDA - ENTRENADORES CREAR")
    print(f"  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"  Entrenadores: {len(entrenadores)}")
    print(f"{'='*60}\n")

    for i, ent in enumerate(entrenadores, 1):
        print(f"\n--- [{i}/{len(entrenadores)}] {ent['nombre']} ---")
        pdf_path = generar_pdf_entrenador(ent, datos)
        # Enviar con copia a Jose
        enviar_bienvenida_entrenador(ent, pdf_path, cc="jose.sanchez@crearpsl.com")

    print(f"\n{'='*60}")
    print(f"  DESPACHO COMPLETADO - {len(entrenadores)} entrenadores")
    print(f"  PDFs en: {OUTPUT_DIR}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    ejecutar_todos()
