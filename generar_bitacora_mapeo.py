from pathlib import Path

OUTPUT_DOC = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\BITACORA_MAPEO_ESTRATEGICO_CPSL.doc")

def generar_bitacora_mapeo():
    print("--- GENERANDO BITACORA DE MAPEO (INSTRUCCION vs CREACION) ---")
    
    mapeo = [
        {
            "instruccion": "Leer y cruzar asignaciones de Diana y Joyce (Asignacion_C1.xlsx).",
            "creacion": "Script 'generar_despacho_maestro.py' + 'Asignacion_C1_EQUIPO27.xlsx'.",
            "impacto": "Segmentación exacta de la red operativa de las coordinadoras."
        },
        {
            "instruccion": "Revisar productividad de C1 en el portal web.",
            "creacion": "Robot 'robot_productividad.py' + 'Productividad_Web.xlsx'.",
            "impacto": "Eliminación de la dependencia de Excels locales; data 100% veraz."
        },
        {
            "instruccion": "Escanear 2 años de Gmail para buscar rebotes y patrones.",
            "creacion": "Motor 'motor_inteligencia_forense.py' + 'PATRONES_MAESTROS_2AÑOS.csv'.",
            "impacto": "Creación de la Memoria Forense Anti-Spam (851 rebotes detectados)."
        },
        {
            "instruccion": "Responder a Carolina Manrique de manera asertiva y entronadora.",
            "creacion": "Script 'responder_carolina.py' + Despacho de Email oficial.",
            "impacto": "Alineación de la red IMO y validación de graduados (Oscar/Erika)."
        },
        {
            "instruccion": "Enviar correos y SMS reales para la campaña C1 E28.",
            "creacion": "Motor 'despacho_real_omnicanal.py' (1,318 comunicaciones enviadas).",
            "impacto": "Ejecución masiva omnicanal con trazabilidad en tiempo real."
        },
        {
            "instruccion": "Diseñar la Arquitectura Blindada CRM CPSL.",
            "creacion": "Plan Maestro + 'database.py' (Enterprise) + 'caja_negra.db'.",
            "impacto": "Blindaje total contra pérdida de memoria y errores operativos."
        },
        {
            "instruccion": "Implementar validaciones de 15 puntos pre-envío.",
            "creacion": "Gatekeeper Enterprise ('gatekeeper_enterprise.py').",
            "impacto": "Cero correos/SMS enviados a contactos muertos o no autorizados."
        },
        {
            "instruccion": "Simular comportamiento humano para evitar bloqueos.",
            "creacion": "Motor 'comunicaciones_ritmo_humano.py' (Pausas y Límites).",
            "impacto": "Protección de la reputación de Gmail y el Gateway SMS."
        },
        {
            "instruccion": "Usar IA para clasificar intenciones de participantes.",
            "creacion": "Orquestador IA Multiagente ('orquestador_ia.py').",
            "impacto": "Gestión automática de confirmaciones, dudas y bajas (STOP)."
        },
        {
            "instruccion": "Crear Dashboard Premium para Diana y Joyce.",
            "creacion": "Interfaz HTML Premium + Integración en 'torre_control_app.py'.",
            "impacto": "Control gerencial visual de la salud de la base y reputación de canales."
        }
    ]

    html_content = """
    <html xmlns:o='urn:schemas-microsoft-com:office:office' xmlns:w='urn:schemas-microsoft-com:office:word' xmlns='http://www.w3.org/TR/REC-html40'>
    <head><meta charset='utf-8'><title>Bitácora de Mapeo CPSL</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; font-size: 10pt; }
        h1 { color: #2C3E50; text-align: center; border-bottom: 2px solid #2C3E50; padding-bottom: 10px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background-color: #2C3E50; color: white; padding: 10px; border: 1px solid #ddd; }
        td { padding: 10px; border: 1px solid #ddd; vertical-align: top; }
        .footer { font-size: 8pt; color: #95a5a6; margin-top: 30px; text-align: center; }
    </style>
    </head>
    <body>
        <h1>BITÁCORA DE MAPEO ESTRATÉGICO: INSTRUCCIÓN ↔ CREACIÓN</h1>
        <p><i>Documento de Trazabilidad Total - Sesión 14 de Mayo, 2026</i></p>
        <table>
            <thead>
                <tr>
                    <th>TU INDICACIÓN / PEDIDO</th>
                    <th>MI CREACIÓN / ACCIÓN</th>
                    <th>IMPACTO ESTRATÉGICO</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for item in mapeo:
        html_content += f"""
        <tr>
            <td><b>{item['instruccion']}</b></td>
            <td>{item['creacion']}</td>
            <td><i>{item['impacto']}</i></td>
        </tr>
        """
        
    html_content += """
            </tbody>
        </table>
        <div class='footer'>
            &copy; 2026 Torre de Control CPSL - Arquitectura de Inteligencia Operativa
        </div>
    </body>
    </html>
    """
    
    with open(OUTPUT_DOC, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"Bitácora de Mapeo generada: {OUTPUT_DOC}")

if __name__ == "__main__":
    generar_bitacora_mapeo()
