import fitz

def main():
    pdf_path = "C:/Users/josem/Downloads/Ficha del Participante.pdf"
    output_path = "C:/Users/josem/Downloads/Ficha del Participante - Actualizada.pdf"
    
    doc = fitz.open(pdf_path)
    
    # Add a red note on the first page
    page1 = doc[0]
    note = "NOTA: LOS TÉRMINOS Y CONDICIONES REALES ACEPTADOS\nY LOS DETALLES DE PAGO SE ENCUENTRAN EN LA PÁGINA 2."
    page1.insert_text((50, 380), note, fontsize=12, color=(1, 0, 0), fontname="helv")
    
    # Add a new page
    new_page = doc.new_page()
    
    title = "Términos y condiciones del servicio — Capítulo Uno\nCREACIÓN CUÁNTICA E.I.R.L. — RUC 20612592811\n\n"
    
    terms = """Al inscribirme en el programa "Capítulo Uno" de CREACIÓN CUÁNTICA E.I.R.L., declaro haber leído, entendido y aceptado los siguientes términos con carácter de declaración jurada:

1. Política de no reembolso y asistencia (cláusula esencial)
El pago de inscripción es no reembolsable y no transferible bajo ninguna circunstancia (incluyendo inasistencias, motivos de salud, cruce de horarios o razones personales). La reserva del cupo genera gastos administrativos y logísticos inmediatos. Si no asisto a la fecha programada, perderé el 100% del pago realizado, considerándose el servicio como ejecutado.

2. Naturaleza del entrenamiento y salud integral
Entiendo que el entrenamiento es una experiencia vivencial de alto impacto emocional y físico. Declaro, bajo juramento, encontrarme en perfecto estado de salud física y mental. Certifico no estar bajo tratamiento psiquiátrico actual ni padecer condiciones cardíacas o emocionales que impidan mi participación. Exonero a CREACIÓN CUÁNTICA E.I.R.L. de cualquier responsabilidad por descompensaciones derivadas de condiciones preexistentes que omita declarar.

3. Responsabilidad civil y conducta
Asumo total responsabilidad por mis actos dentro del evento y me comprometo a mantener una conducta respetuosa. La empresa se reserva el derecho de admisión y permanencia. Si asisto bajo efectos de alcohol o drogas, o presento conductas violentas, seré retirado del programa sin derecho a reclamo ni devolución.

4. Confidencialidad y propiedad intelectual
Me comprometo a no grabar, reproducir ni divulgar las dinámicas, materiales o testimonios compartidos durante el entrenamiento, protegiendo la privacidad del grupo y la propiedad intelectual de la empresa.

5. Uso de imagen y datos personales
Autorizo a CREACIÓN CUÁNTICA E.I.R.L. a utilizar fotografías y videos en los que aparezca mi imagen captada durante el evento para fines institucionales y promocionales en sus redes sociales y sitio web. Asimismo, autorizo el tratamiento de mis datos personales conforme a la Ley N° 29733 para la gestión del servicio.
"""

    payment_info = """
---------------------------------------------------------------------------------------------------------
INFORMACIÓN ADICIONAL DEL PARTICIPANTE Y PAGO
---------------------------------------------------------------------------------------------------------
Participante: HERLE CHRISTIAM RODRIGUEZ ARENAS
Equipo: C1E25 (Capítulo 1, Equipo 25)
Fecha de Entrenamiento: LIMA, 2026-05-29 AL 2026-05-31
Pago Registrado: 8 de febrero de 2026, 17:22 horas
Monto Pagado: S/ 900.00
N° de Comprobante: 214162
Forma de Pago: VISA BANCO INTERBANK (Culqi)
"""

    rect = fitz.Rect(50, 50, 550, 800)
    new_page.insert_textbox(rect, title + terms + payment_info, fontsize=11, fontname="helv")
    
    doc.save(output_path)
    print(f"PDF saved to {output_path}")

if __name__ == "__main__":
    main()
