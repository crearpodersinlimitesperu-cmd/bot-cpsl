import os
import pandas as pd
import easyocr
import dateparser
from thefuzz import process, fuzz
import re
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm

print("Inicializando Motor de Inteligencia Artificial (EasyOCR)...")
reader = easyocr.Reader(['es', 'en'], gpu=False)
print("Motor OCR Listo.")

def build_pdf(pdf_path, data_dict):
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(name='TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, spaceAfter=12, textColor=colors.HexColor("#003366"))
    subtitle_style = ParagraphStyle(name='SubtitleStyle', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, spaceAfter=10, textColor=colors.HexColor("#004080"))
    normal_style = ParagraphStyle(name='NormalStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, spaceAfter=6, leading=14)
    terms_style = ParagraphStyle(name='TermsStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, spaceAfter=8, leading=12, alignment=4)
    
    elements = []
    
    logo_path = "C:/Users/josem/Downloads/logo.png"
    if os.path.exists(logo_path):
        img = Image(logo_path, width=4*cm, height=2.5*cm)
        img.hAlign = 'LEFT'
        elements.append(img)
        elements.append(Spacer(1, 0.5*cm))
        
    elements.append(Paragraph("FICHA DE INSCRIPCIÓN DEL PARTICIPANTE", title_style))
    elements.append(Spacer(1, 0.3*cm))
    
    elements.append(Paragraph("DATOS PERSONALES", subtitle_style))
    nombre = str(data_dict.get('Nombre', ''))
    if nombre == 'nan': nombre = ''
    apellido = str(data_dict.get('Apellido', ''))
    if apellido == 'nan': apellido = ''
    nombre_completo = f"{nombre} {apellido}".strip()
    
    data = [
        [Paragraph("<b>Nombre Completo:</b>", normal_style), Paragraph(nombre_completo, normal_style)],
        [Paragraph("<b>Nombre de preferencia:</b>", normal_style), Paragraph(nombre, normal_style)],
        [Paragraph("<b>Teléfono Móvil:</b>", normal_style), Paragraph(str(data_dict.get('Teléfono', '')), normal_style)],
        [Paragraph("<b>CI. No / Identificación:</b>", normal_style), Paragraph(str(data_dict.get('Identificación', '')), normal_style)],
    ]
    t = Table(data, colWidths=[5.5*cm, 10.5*cm])
    t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elements.append(t)
    elements.append(Spacer(1, 0.5*cm))
    
    elements.append(Paragraph("INFORMACIÓN DE ENTRENAMIENTO", subtitle_style))
    equipo_str = str(data_dict.get('Equipo', ''))
    if equipo_str == 'nan': equipo_str = 'NO ASIGNADO'
    fecha_entrenamiento = data_dict.get('FechaEntrenamiento', 'FECHA POR CONFIRMAR')
    imo = str(data_dict.get('IMO', ''))
    if imo == 'nan': imo = 'NINGUNO'
    
    data2 = [
        [Paragraph("<b>Invitado por (IMO):</b>", normal_style), Paragraph(imo, normal_style)],
        [Paragraph("<b>Equipo:</b>", normal_style), Paragraph(equipo_str, normal_style)],
        [Paragraph("<b>Fecha de Entrenamiento:</b>", normal_style), Paragraph(fecha_entrenamiento, normal_style)],
    ]
    t2 = Table(data2, colWidths=[5.5*cm, 10.5*cm])
    t2.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 4)]))
    elements.append(t2)
    elements.append(Spacer(1, 0.5*cm))

    elements.append(Paragraph("TÉRMINOS Y CONDICIONES DEL SERVICIO — CAPÍTULO UNO", subtitle_style))
    elements.append(Paragraph("CREACIÓN CUÁNTICA E.I.R.L. — RUC 20612592811", terms_style))
    elements.append(Spacer(1, 0.2*cm))
    
    terms_intro = """Al inscribirme en el programa "Capítulo Uno" de CREACIÓN CUÁNTICA E.I.R.L., declaro haber leído, entendido y aceptado los siguientes términos con carácter de declaración jurada:"""
    elements.append(Paragraph(terms_intro, terms_style))
    
    terms_list = [
        "<b>1. Política de no reembolso y asistencia (cláusula esencial)</b><br/>El pago de inscripción es no reembolsable y no transferible bajo ninguna circunstancia.",
        "<b>2. Naturaleza del entrenamiento y salud integral</b><br/>Entiendo que el entrenamiento es una experiencia vivencial de alto impacto emocional y físico. Declaro, bajo juramento, encontrarme en perfecto estado de salud física y mental.",
        "<b>3. Responsabilidad civil y conducta</b><br/>Asumo total responsabilidad por mis actos dentro del evento y me comprometo a mantener una conducta respetuosa.",
        "<b>4. Confidencialidad y propiedad intelectual</b><br/>Me comprometo a no grabar, reproducir ni divulgar las dinámicas, materiales o testimonios compartidos durante el entrenamiento.",
        "<b>5. Uso de imagen y datos personales</b><br/>Autorizo a CREACIÓN CUÁNTICA E.I.R.L. a utilizar fotografías y videos captados durante el evento."
    ]
    for term in terms_list:
        elements.append(Paragraph(term, terms_style))
        elements.append(Spacer(1, 0.2*cm))
        
    elements.append(Spacer(1, 1*cm))
    
    elements.append(Paragraph("ACEPTACIÓN DE TÉRMINOS Y CONDICIONES", subtitle_style))
    acceptance_text = "✓ <b>Aceptación digital registrada</b>. El participante aceptó formalmente todos los términos y condiciones de manera electrónica mediante el formulario de registro (modalidad de compra en línea)."
    elements.append(Paragraph(acceptance_text, normal_style))
    elements.append(Spacer(1, 0.3*cm))
    
    fecha_registro = data_dict.get('FechaRegistro', 'Aceptación Electrónica Confirmada')
    signature_data = [
        [Paragraph("<b>NOMBRE DEL PARTICIPANTE:</b>", normal_style), Paragraph(nombre_completo, normal_style)],
        [Paragraph("<b>FECHA DE REGISTRO / PAGO:</b>", normal_style), Paragraph(fecha_registro, normal_style)]
    ]
    t5 = Table(signature_data, colWidths=[6*cm, 10*cm])
    t5.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'LEFT'), ('VALIGN', (0,0), (-1,-1), 'TOP'), ('BOTTOMPADDING', (0,0), (-1,-1), 8)]))
    elements.append(t5)

    doc.build(elements)

import cv2
import numpy as np

def extraer_fecha_ocr(image_path):
    try:
        # Fix: leer la imagen a memoria primero para evitar problemas de OpenCV con tildes en la ruta (ej. CAPÍTULO)
        with open(image_path, 'rb') as f:
            img_array = np.asarray(bytearray(f.read()), dtype=np.uint8)
            img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            
        results = reader.readtext(img, detail=0)
        full_text = " ".join(results).lower()
        
        # Buscar patrones de fecha usando regex
        # format: dd/mm/yyyy or dd-mm-yyyy or dd.mm.yyyy
        match = re.search(r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b', full_text)
        if match:
            # usar dateparser para parsear el match
            parsed = dateparser.parse(match.group(1), settings={'DATE_ORDER': 'DMY'})
            if parsed: return parsed.strftime('%Y-%m-%d')
            
        # Si no funciona la regex, buscar en todo el texto con dateparser
        # dateparser search es potente pero puede dar falsos positivos, mejor regex primero.
        import dateparser.search
        dates = dateparser.search.search_dates(full_text, settings={'STRICT_PARSING': False, 'DATE_ORDER': 'DMY'})
        if dates:
            # Tomamos la primera fecha razonable que encuentre
            for text, dt in dates:
                if 2020 <= dt.year <= 2030:
                    return dt.strftime('%Y-%m-%d')
                    
    except Exception as e:
        print(f"Error OCR en {image_path}: {e}")
    return None

def process_all():
    csv_path = "C:/Users/josem/Downloads/participantes_2026-05-22.csv"
    excel_path = "C:/Users/josem/OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA/CREAR LIMA/PROGRAMACION 2026 CREAR LIMA.xlsx"
    comprobantes_dir = "C:/Users/josem/OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA/CREAR LIMA - 02. Comprobantes"
    out_dir = os.path.join(comprobantes_dir, "FICHAS_CON_FECHAS_REVISION")
    
    os.makedirs(out_dir, exist_ok=True)
    
    print("Catalogando imágenes de comprobantes...")
    image_catalog = {} # nombre archivo sin extension -> path completo
    for root, dirs, files in os.walk(comprobantes_dir):
        # Evitar buscar en la carpeta de salida
        if "FICHAS" in root: continue
        for file in files:
            if file.lower().endswith(('.jpeg', '.jpg', '.png', '.pdf')):
                name_without_ext = os.path.splitext(file)[0].lower()
                image_catalog[name_without_ext] = os.path.join(root, file)
                
    nombres_archivos = list(image_catalog.keys())
    print(f"Se encontraron {len(nombres_archivos)} archivos de comprobantes.")
    
    print("Leyendo Excel...")
    df_excel = pd.read_excel(excel_path, sheet_name='LIM')
    team_dates = {}
    for idx, row in df_excel.iterrows():
        try:
            if pd.notna(row['ENTRENAMIENTO']) and 'UNO' in str(row['ENTRENAMIENTO']).upper():
                equipo_num = str(row['EQUIPO']).replace('.0','').strip()
                if pd.notna(row['INICIO']) and pd.notna(row['FINAL']):
                    inicio = pd.to_datetime(row['INICIO']).strftime('%Y-%m-%d')
                    final = pd.to_datetime(row['FINAL']).strftime('%Y-%m-%d')
                    team_dates[equipo_num] = f"LIMA, {inicio} AL {final}"
        except Exception:
            continue
            
    print("Leyendo CSV...")
    df_csv = pd.read_csv(csv_path, on_bad_lines='skip', engine='python')
    
    count = 0
    total_to_process = len(df_csv)
    print(f"Procesando {total_to_process} registros a fondo con Inteligencia Artificial OCR...")
    
    for idx, row in df_csv.iterrows():
        data_dict = row.to_dict()
        
        equipo_str = str(data_dict.get('Equipo', ''))
        equipo_num = equipo_str.replace('EQUIPO', '').strip()
        data_dict['FechaEntrenamiento'] = team_dates.get(equipo_num, 'FECHA POR CONFIRMAR')
        
        nombre = str(data_dict.get('Nombre', '')).strip()
        apellido = str(data_dict.get('Apellido', '')).strip()
        nombre_completo = f"{nombre} {apellido}".strip().lower()
        
        fecha_encontrada = "No se encontró comprobante"
        
        # 1. Fuzzy Match con el nombre de archivo
        if nombres_archivos:
            match, score = process.extractOne(nombre_completo, nombres_archivos, scorer=fuzz.token_set_ratio)
            if score > 75:
                matched_path = image_catalog[match]
                print(f" -> Comprobante de {nombre_completo.upper()} encontrado: {match} (Score: {score})")
                if matched_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    print("    Leyendo texto con OCR...")
                    extracted_date = extraer_fecha_ocr(matched_path)
                    if extracted_date:
                        fecha_encontrada = extracted_date
                        print(f"    Fecha extraída por IA: {fecha_encontrada}")
                    else:
                        fecha_encontrada = "Fecha no legible en imagen"
                        print("    La IA no pudo encontrar una fecha legible en la imagen.")
                else:
                    fecha_encontrada = "El comprobante es PDF (requiere lectura manual)"
            else:
                print(f" -> Comprobante de {nombre_completo.upper()} no encontrado (Mejor coincidencia: {match} con Score: {score})")
                
        data_dict['FechaRegistro'] = fecha_encontrada
        identificacion = str(data_dict.get('Identificación', '000')).strip()
        
        filename = f"Ficha_{equipo_str.replace(' ', '')}_{identificacion}_{nombre[:8]}.pdf".replace('/', '-')
        pdf_path = os.path.join(out_dir, filename)
        try:
            build_pdf(pdf_path, data_dict)
            count += 1
        except Exception as e:
            print(f"Error generando {filename}: {e}")
            
    print(f"Prueba finalizada. {count} PDFs generados.")

if __name__ == "__main__":
    process_all()
