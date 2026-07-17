from fpdf import FPDF
from datetime import datetime

class ContratoPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'CREACION CUANTICA E.I.R.L. - RUC 20612592811', 0, 1, 'C')
        self.set_font('Arial', 'B', 10)
        self.cell(0, 10, 'CONTRATO DE TERMINOS Y CONDICIONES DEL SERVICIO - CAPITULO UNO', 0, 1, 'C')
        self.ln(10)

def generar_pdf_executive_final():
    pdf = ContratoPDF()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    fecha = datetime.now().strftime("%d/%m/%Y")
    hora = datetime.now().strftime("%H:%M:%S")
    
    # Datos del Participante
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'DATOS DEL PARTICIPANTE:', 0, 1)
    pdf.set_font('Arial', '', 10)
    pdf.cell(0, 8, f'Nombre Completo: ROCIO JARA AMPUERO', 0, 1)
    pdf.cell(0, 8, f'DNI / Pasaporte: 07938881', 0, 1)
    pdf.cell(0, 8, f'ID Participante: IMO-07938881', 0, 1)
    pdf.cell(0, 8, f'Programa: CAPITULO UNO - EQUIPO 28', 0, 1)
    pdf.ln(5)
    
    # Clausulas Executive
    pdf.set_font('Arial', 'B', 11)
    pdf.cell(0, 10, 'TERMINOS Y CONDICIONES DEL SERVICIO:', 0, 1)
    pdf.set_font('Arial', '', 9)
    
    clausulas = [
        "1. Politica de inscripcion y reembolso: El pago garantiza la reserva de un cupo limitado y genera gastos logisticos inmediatos. No reembolsable en casos de inasistencia.",
        "2. Salud integral: El participante declara encontrarse en adecuado estado fisico y mental. No bajo tratamiento psiquiatrico ni afecciones cardiacas.",
        "3. Naturaleza del servicio: Estructura acumulativa. La participacion en cada sesion es indispensable para acceder a las posteriores.",
        "4. Reprogramacion por unica vez: Solicitud por escrito con 7 dias de anticipacion. Motivo justificado. Sujeto a disponibilidad.",
        "5. Reprogramacion por CREACION CUANTICA: El consumidor podra optar por la siguiente edicion o reembolso integro en 15 dias.",
        "6. Responsabilidad civil y conducta: CREACION CUANTICA se reserva el derecho de admision y permanencia. Conductas violentas generan retiro inmediato.",
        "7. Confidencialidad: Prohibida la grabacion o difusion de dinamicas y testimonios. Proteccion de propiedad intelectual.",
        "8. Uso de imagen y proteccion de datos: Autorizacion revocable para fines institucionales. Tratamiento conforme a la Ley N 29733.",
        "9. Aceptacion: El consumidor acepta libre y voluntariamente todas las condiciones anteriores."
    ]
    
    for clau in clausulas:
        pdf.multi_cell(0, 8, clau)
        pdf.ln(1)
    
    # Constancia Digital
    pdf.ln(10)
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(10, pdf.get_y(), 190, 35, 'F')
    pdf.set_font('Arial', 'B', 9)
    pdf.cell(0, 10, '  CONSTANCIA DE ACEPTACION DIGITAL', 0, 1)
    pdf.set_font('Arial', '', 8)
    pdf.cell(0, 5, f'  Fecha de Aceptacion: {fecha}', 0, 1)
    pdf.cell(0, 5, f'  Hora de Aceptacion: {hora}', 0, 1)
    pdf.cell(0, 5, '  Metodo: Aceptacion electronica voluntaria mediante plataforma IMO', 0, 1)
    pdf.set_font('Arial', 'B', 8)
    pdf.cell(0, 5, '  ESTADO: CONTRATO ACEPTADO DIGITALMENTE - VALIDADO', 0, 1)
    
    output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Contrato_Executive_ROCIO_JARA.pdf"
    pdf.output(output_path)
    print(f"PDF Executive generado en: {output_path}")

if __name__ == "__main__":
    generar_pdf_executive_final()
