import pandas as pd
from datetime import datetime

# Cargar data de despacho
df = pd.read_csv("DESPACHO_MAESTRO_C1_EJECUCION.csv")

def generar_reporte_ejecutivo():
    print("--- GENERANDO REPORTE DE CIERRE EJECUTIVO ---")
    
    resumen = {
        "Fecha_Ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Total_Impactados": len(df),
        "Emails_Exitosos": len(df[df['Canal'] == 'EMAIL_OFICIAL']),
        "SMS_Rescate": len(df[df['Canal'] == 'SMS_RESCATE']),
        "Ahorro_Redundancia": len(df[df['Canal'] == 'SMS_RESCATE']), # Evitamos enviar 272 correos fallidos
        "Eficiencia_Dato": f"{(len(df[df['Canal'] == 'EMAIL_OFICIAL']) / len(df)) * 100:.1f}%"
    }
    
    # Top 10 IMOs con mas rescatados (data invalida)
    top_imos = df[df['Canal'] == 'SMS_RESCATE']['Nombre_IMO'].value_counts().head(10)
    
    with open("REPORTE_CIERRE_EJECUCION_C1.txt", "w", encoding='utf-8') as f:
        f.write("====================================================\n")
        f.write("      REPORTE DE CIERRE - OPERACION PURIFICACION C1\n")
        f.write(f"      FECHA: {resumen['Fecha_Ejecucion']}\n")
        f.write("====================================================\n\n")
        
        f.write("1. METRICAS DE IMPACTO:\n")
        f.write(f"- Total Participantes Gestionados: {resumen['Total_Impactados']}\n")
        f.write(f"- Emails Oficiales Despachados:   {resumen['Emails_Exitosos']}\n")
        f.write(f"- SMS de Rescate (PX + IMO):      {resumen['SMS_Rescate']}\n")
        f.write(f"- Ahorro de Envíos Fallidos:      {resumen['Ahorro_Redundancia']} (Gracias a Auditoría Forense)\n")
        f.write(f"- Calidad de la Base Original:    {resumen['Eficiencia_Dato']}\n\n")
        
        f.write("2. TOP 10 IMOs CON DATOS POR ACTUALIZAR (ALTA PRIORIDAD):\n")
        for imo, count in top_imos.items():
            f.write(f"- {imo}: {count} participantes con rebote\n")
        
        f.write("\n3. CONCLUSION OPERATIVA:\n")
        f.write("La base de datos ha sido purificada contra el historial de 2 años.\n")
        f.write("Se recomienda a Diana y Joyce enfocar el seguimiento en los 272\n")
        f.write("casos de SMS_RESCATE para obtener los nuevos correos veraces.\n")
        f.write("\n--- FIN DEL REPORTE ---\n")

    print(f"Reporte generado: REPORTE_CIERRE_EJECUCION_C1.txt")
    
    # Exportar una version Excel para analisis profundo
    df.to_excel("CIERRE_EJECUCION_MAESTRO_DETALLE.xlsx", index=False)
    print("Detalle en Excel generado: CIERRE_EJECUCION_MAESTRO_DETALLE.xlsx")

if __name__ == "__main__":
    generar_reporte_ejecutivo()
