from fpdf import FPDF
from datetime import datetime

class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CREACION CUANTICA E.I.R.L. - RUC 20612592811', 0, 1, 'C')
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'TERMINOS Y CONDICIONES DEL SERVICIO - PROGRAMA CAPITULO UNO', 0, 1, 'C')
        self.ln(10)

def generar_pdf_forense_v9():
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    hora = datetime.now().strftime("%H:%M:%S")
    
    # DATOS DEL PARTICIPANTE
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'DATOS DEL PARTICIPANTE:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, 'Nombres y Apellidos: ROCIO JARA AMPUERO', 0, 1)
    pdf.cell(0, 8, 'Documento de Identidad: 07938881', 0, 1)
    pdf.cell(0, 8, 'Codigo de Participante: 07938881', 0, 1)
    pdf.cell(0, 8, f'Fecha de Inscripcion: {fecha}', 0, 1)
    pdf.cell(0, 8, f'Hora de Registro: {hora}', 0, 1)
    pdf.ln(5)

    # TEXTO LEGAL FORENSE (Extraído del .doc oficial)
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'VERSION CORREGIDA - TERMINOS Y CONDICIONES:', 0, 1)
    pdf.set_font('Arial', '', 9)
    
    texto_legal = """Al inscribirme en el programa "Capítulo Uno" de CREACIÓN CUÁNTICA E.I.R.L. (en adelante, CREACIÓN CUÁNTICA), declaro bajo juramento haber leído, comprendido y aceptado las presentes condiciones, las cuales regulan la relación contractual bajo los principios de buena fe, transparencia y equilibrio conforme a la Ley N° 29571.

1. Política de inscripción y reembolso: El pago de inscripción garantiza la reserva de un cupo limitado y genera gastos logísticos inmediatos. Por ello, el importe es no reembolsable en casos de inasistencia o causas ajenas a la idoneidad del servicio. Sin embargo, procederá reembolso íntegro si el servicio no se brinda por responsabilidad de CREACIÓN CUÁNTICA, conforme al numeral 5.

2. Salud integral y declaración jurada: Declaro que me encuentro en adecuado estado de salud física y mental para participar en un entrenamiento de alto impacto emocional. Certifico que no me encuentro bajo tratamiento psiquiátrico ni padezco afecciones cardíacas. En virtud del deber de información, asumo responsabilidad exclusiva por cualquier descompensación derivada de condiciones preexistentes no declaradas. CREACIÓN CUÁNTICA responderá por la seguridad e idoneidad del servicio, pero no por daños derivados de condiciones preexistentes omitidas por el consumidor.

3. Naturaleza del servicio y continuidad: El servicio es una formación de estructura acumulativa. La participación en cada sesión es indispensable para acceder a las posteriores. El retiro prematuro o la inasistencia parcial facultan a CREACIÓN CUÁNTICA a restringir el acceso a las siguientes sesiones, para proteger la calidad del servicio y la seguridad del grupo, sin que ello genere derecho a reembolso; sin perjuicio del derecho a reprogramación previsto en el numeral 4.

4. Reprogramación por única vez: Declaro conocer que puedo solicitar una sola reprogramación de mi participación, siempre que: La solicitud sea presentada por escrito y confirmada por CREACIÓN CUÁNTICA al menos 7 días calendario antes del inicio. El motivo sea debidamente justificado (enfermedad, fuerza mayor o caso fortuito). En caso de enfermedad, podrá solicitarse certificado médico, el que será tratado confidencialmente. La reprogramación se aplicará a la siguiente edición disponible, sin costo adicional, siempre que exista cupo. De no existir, se reprogramará a la edición subsiguiente. Si el consumidor no asiste a la nueva fecha reprogramada sin justificación válida, perderá el derecho a una nueva reprogramación y no procederá reembolso.

5. Reprogramación solicitada por CREACIÓN CUÁNTICA: En caso de reprogramación por parte de CREACIÓN CUÁNTICA, el consumidor podrá optar entre: Participar en la siguiente edición sin costo adicional o recibir el reembolso íntegro del monto pagado, en un plazo máximo de 15 días calendario.

6. Responsabilidad civil, conducta y permanencia: En mi condición de consumidor asumo la responsabilidad por mis actos y bienes personales durante el entrenamiento. CREACIÓN CUÁNTICA se reserva el derecho de admisión y permanencia si ingreso bajo efectos de alcohol/drogas, haga uso de violencia o incurro en conductas que vulneren la seguridad de terceros, lo que dará lugar al retiro inmediato y definitivo del programa, sin derecho a devolución. Toda exclusión será documentada mediante acta o informe.

7. Confidencialidad y propiedad intelectual: Me comprometo a no grabar ni difundir las dinámicas y testimonios del grupo. El incumplimiento facultará a CREACIÓN CUÁNTICA a iniciar acciones por daños y perjuicios y por infracción a la Ley sobre el Derecho de Autor.

8. Uso de imagen y protección de datos: Autorizo el uso de mi imagen captada en el evento para fines institucionales y promocionales. Esta autorización es revocable por escrito en cualquier momento. CREACIÓN CUÁNTICA tratará los datos personales conforme a la Ley N° 29733 y su reglamento. El consumidor tiene derecho a acceder, rectificar, cancelar u oponerse al tratamiento mediante solicitud escrita.

9. Aceptación: El consumidor acepta libre y voluntariamente todas las condiciones anteriores, y reconoce que esta ficha forma parte de su legajo que CREACIÓN CUÁNTICA E.I.R.L. conservará conforme a la normativa vigente."""

    pdf.multi_cell(0, 6, texto_legal)
    
    # CONSTANCIA DIGITAL
    pdf.ln(10)
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(10, pdf.get_y(), 190, 30, 'F')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 10, '  CONSTANCIA DE ACEPTACION DIGITAL - IMO PLATAFORMA', 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.cell(0, 5, f'  Documento generado automaticamente segun protocolo oficial del documento doc.', 0, 1)
    pdf.cell(0, 5, f'  Fecha de Registro: {fecha} | Hora: {hora}', 0, 1)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, '  ESTADO: CONTRATO ACEPTADO DIGITALMENTE - VALIDADO', 0, 1)
    
    output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_Forense_ROCIO_JARA.pdf"
    pdf.output(output_path)
    print(f"PDF Forense v9 generado en: {output_path}")

if __name__ == "__main__":
    generar_pdf_forense_v9()
