import os
from fpdf import FPDF
from datetime import datetime
from pathlib import Path

# Brand Assets
BASE_DIR = Path(__file__).parent
FIRMA_PATH = Path(r"C:\Users\josem\Downloads\Imágenes\Firmas\FIRMA JOSE SANCHEZ.png")
LOGO_PATH  = Path(r"C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png")

class BoardingPassPDF(FPDF):
    def header(self):
        # Premium Spacing Header
        self.set_fill_color(26, 26, 46) # Navy
        self.rect(0, 0, 210, 40, 'F')
        
        if LOGO_PATH.exists():
            self.image(str(LOGO_PATH), 10, 10, 25)
        
        self.set_xy(40, 12)
        self.set_font('Helvetica', 'B', 15)
        self.set_text_color(255, 255, 255)
        self.cell(100, 10, 'CREAR GLOBAL', 0, 0, 'L')
        
        self.set_xy(150, 10)
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(180, 150, 50) # Gold
        self.cell(50, 5, 'OFFICIAL RECORD', 0, 1, 'R')
        self.set_x(150)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(200, 200, 200)
        self.cell(50, 5, 'PERU - GLOBAL 2026', 0, 1, 'R')
        
        self.ln(20)

    def footer(self):
        self.set_y(-25)
        self.set_font('Helvetica', '', 7)
        self.set_text_color(180, 180, 180)
        self.cell(0, 5, '-' * 120, 0, 1, 'C')
        self.cell(0, 5, f'CREACION CUANTICA E.I.R.L. | RUC 20612592811 | Pagina {self.page_no()}', 0, 1, 'C')
        self.cell(0, 5, 'Institutional Transactional Record - Confidential', 0, 0, 'C')

    def section_header(self, title, token=""):
        self.ln(10)
        self.set_font('Helvetica', 'B', 10)
        self.set_text_color(26, 26, 46)
        self.cell(100, 8, title.upper(), 0, 0)
        if token:
            self.set_font('Helvetica', 'B', 8)
            self.set_text_color(180, 150, 50)
            self.cell(0, 8, f'ID: {token}', 0, 1, 'R')
        else:
            self.ln(8)
        
        self.set_draw_color(180, 150, 50)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), 200, self.get_y())
        self.ln(4)

    def data_box(self, label, value):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(120, 120, 120)
        self.cell(60, 6, label, 0, 0)
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(26, 26, 46)
        self.cell(0, 6, str(value), 0, 1)

def generate_boarding_pass_contract(px_data, token, output_path):
    """
    Generates a world-class Boarding Pass style contract.
    """
    pdf = BoardingPassPDF()
    pdf.set_auto_page_break(auto=True, margin=30)
    pdf.add_page()
    
    fecha_hoy = datetime.now().strftime("%d/%m/%Y")

    # Boarding Pass Header Info
    pdf.set_xy(10, 45)
    pdf.set_font('Helvetica', 'B', 20)
    pdf.set_text_color(26, 26, 46)
    pdf.cell(0, 10, 'ADMISSION CONFIRMED', 0, 1, 'L')
    
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 5, 'Su participacion en el programa de transformacion ha sido validada institucionalmente.', 0, 1, 'L')
    
    # Section 1: Institutional Admission
    pdf.section_header('Informacion de Admision', token)
    pdf.data_box('PARTICIPANTE:', px_data.get('nombre'))
    pdf.data_box('DOCUMENTO:', px_data.get('documento'))
    pdf.data_box('PROGRAMA:', f"CAPITULO UNO - EQUIPO {px_data.get('equipo', 'E28')}")
    pdf.data_box('SEDE:', 'LIMA, PERU')
    pdf.data_box('FECHA DE EMISION:', fecha_hoy)
    
    # Section 2: Legal Acceptance
    pdf.section_header('Manifestacion de Voluntad')
    pdf.set_font('Helvetica', '', 8.5)
    pdf.set_text_color(60, 60, 60)
    statement = (
        "El participante declara haber leido y aceptado integramente los Terminos y Condiciones "
        "del Servicio durante el proceso de inscripcion digital. Esta manifestacion tiene "
        "validez legal plena bajo la Ley N 27291 del Estado Peruano."
    )
    pdf.multi_cell(0, 5, statement)
    
    # Section 3: Professional Commitment
    pdf.section_header('Compromisos Institucionales')
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(26, 26, 46)
    commitments = [
        "1. Asistencia total y puntual a las tres jornadas del entrenamiento.",
        "2. Respeto absoluto a la confidencialidad de la metodologia y participantes.",
        "3. El pago realizado es personal, intransferible y no reembolsable."
    ]
    for c in commitments:
        pdf.cell(5, 6, '>', 0, 0)
        pdf.cell(0, 6, c, 0, 1)
    
    # Digital Seal
    pdf.ln(15)
    curr_y = pdf.get_y()
    
    # Drawing a box for the digital seal
    pdf.set_draw_color(230, 230, 230)
    pdf.rect(10, curr_y, 190, 45)
    
    pdf.set_xy(15, curr_y + 5)
    pdf.set_font('Helvetica', 'B', 7)
    pdf.set_text_color(180, 150, 50)
    pdf.cell(0, 5, 'ACEPTACION DIGITAL REGISTRADA', 0, 1, 'L')
    
    pdf.set_x(15)
    pdf.set_font('Helvetica', '', 7)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(90, 4, f"Hash ID: {token}", 0, 1)
    pdf.set_x(15)
    pdf.cell(90, 4, f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    pdf.set_x(15)
    pdf.cell(90, 4, f"Digital Fingerprint: CC-EIRL-SECURE-ID-{px_data.get('documento')}", 0, 1)
    
    # Institutional Signature
    if FIRMA_PATH.exists():
        pdf.image(str(FIRMA_PATH), 85, curr_y + 15, 40)
    
    pdf.set_xy(80, curr_y + 35)
    pdf.set_font('Helvetica', 'B', 8)
    pdf.set_text_color(26, 26, 46)
    pdf.cell(50, 5, 'JOSE SANCHEZ', 0, 1, 'C')
    pdf.set_x(80)
    pdf.set_font('Helvetica', '', 7)
    pdf.cell(50, 4, 'Representante Legal', 0, 1, 'C')

    pdf.output(output_path)
    return output_path

if __name__ == "__main__":
    test_data = {"nombre": "TEST USER", "documento": "12345678", "equipo": "E28"}
    generate_boarding_pass_contract(test_data, "PX-2026-LIM-C1-E28-000001", "test_boarding_pass.pdf")
    print("Boarding Pass generated.")
