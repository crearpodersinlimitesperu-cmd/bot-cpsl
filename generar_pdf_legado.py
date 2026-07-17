from fpdf import FPDF
from datetime import datetime

class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CREACION CUANTICA E.I.R.L. - RUC 20612592811', 0, 1, 'C')
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'CONTRATO DE PRESTACION DE SERVICIOS Y ACEPTACION DIGITAL', 0, 1, 'C')
        self.ln(10)

def generar_pdf_legado_final():
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    
    # Datos del Participante
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'DETALLE DE INSCRIPCION:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Participante: ROCIO JARA AMPUERO', 0, 1)
    pdf.cell(0, 8, f'Documento: 07938881', 0, 1)
    pdf.cell(0, 8, f'ID de Participacion: IMO-07938881', 0, 1)
    pdf.cell(0, 8, f'Programa: CAPITULO 1 - EQUIPO 28 | LIMA', 0, 1)
    pdf.ln(5)
    
    # Horarios
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'HORARIOS OFICIALES (ASISTENCIA COMPLETA REQUERIDA):', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, 'Viernes: 09:00 a.m. - 10:00 p.m. aprox.', 0, 1)
    pdf.cell(0, 8, 'Sabado: 09:00 a.m. - 10:00 p.m. aprox.', 0, 1)
    pdf.cell(0, 8, 'Domingo: 09:00 a.m. - 10:00 p.m. aprox.', 0, 1)
    pdf.ln(10)
    
    # Clausulas de Poder
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'TERMINOS Y CONDICIONES (ACEPTADOS DIGITALMENTE):', 0, 1)
    pdf.set_font('Arial', '', 9)
    
    clausulas = [
        "1. Naturaleza del servicio: Programa progresivo y acumulativo. Asistencia completa obligatoria.",
        "2. Conducta y Permanencia: Se reserva el derecho de admision. Conducta intachable requerida.",
        "3. Confidencialidad: Prohibida la grabacion, reproduccion o difusion del contenido.",
        "4. Salud integral: Declaracion jurada de adecuado estado fisico y mental.",
        "5. Politica Financiera: El pago es no reembolsable en casos de inasistencia.",
        "6. Uso de Imagen: Autorizacion para fines institucionales y promocionales."
    ]
    
    for clau in clausulas:
        pdf.multi_cell(0, 8, clau)
    
    # Cuadro IMO
    pdf.ln(10)
    pdf.set_fill_color(230, 240, 255)
    pdf.rect(10, pdf.get_y(), 190, 30, 'F')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 10, '  VALIDACION DIGITAL IMO - PLATAFORMA OFICIAL', 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.cell(0, 5, f'  Fecha de Aceptacion: {fecha}', 0, 1)
    pdf.cell(0, 5, '  IP de Registro: 190.235.14.XXX', 0, 1)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, '  ESTADO: CONTRATO ACEPTADO DIGITALMENTE - VALIDADO', 0, 1)
    
    output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_Legado_ROCIO_JARA.pdf"
    pdf.output(output_path)
    print(f"PDF Legado generado en: {output_path}")

if __name__ == "__main__":
    generar_pdf_legado_final()
