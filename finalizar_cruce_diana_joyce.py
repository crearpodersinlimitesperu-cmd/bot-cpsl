import pandas as pd
from pathlib import Path

# Rutas
ASIG_PATH = Path(r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\Asignacion_C1.xlsx")
IMO_PATH = Path(r"C:\Users\josem\Downloads\Hojas de Cálculo\participantes_2026-05-11.csv")

def cruce_final():
    print("--- INICIANDO CRUCE FINAL DIANA/JOYCE VS IMO ---")
    
    # 1. Cargar Asignaciones y filtrar
    df_asig = pd.read_excel(ASIG_PATH)
    # Filtro Diana (dmoscoso) y Joyce (jmarin)
    df_asig_filt = df_asig[df_asig['Usuario Registro'].isin(['dmoscoso', 'jmarin'])]
    print(f"Registros encontrados para Diana/Joyce: {len(df_asig_filt)}")

    # 2. Cargar IMO
    df_imo = pd.read_csv(IMO_PATH, on_bad_lines='skip', engine='python')
    # Normalizar columna DNI para el cruce
    df_asig_filt['dni_clean'] = df_asig_filt['Identificaci\u00f3n'].astype(str).str.replace('\.0', '', regex=True).str.strip()
    df_imo['dni_clean'] = df_imo['Identificaci\u00f3n'].astype(str).str.replace('\.0', '', regex=True).str.strip()

    # 3. Cruzar por DNI
    merged = pd.merge(df_asig_filt, df_imo, on='dni_clean', how='inner', suffixes=('_asig', '_imo'))
    print(f"Participantes validados con IMO: {len(merged)}")

    # 4. Detectar No-Enrolados (Estan en Asignacion pero NO en IMO)
    no_enrolados = df_asig_filt[~df_asig_filt['dni_clean'].isin(df_imo['dni_clean'])]
    print(f"Participantes en Asignacion pero NO en IMO: {len(no_enrolados)}")

    # 5. Generar Reportes
    if not merged.empty:
        merged.to_csv("VALIDADOS_DIANA_JOYCE_IMO.csv", index=False)
        print("Reporte generado: VALIDADOS_DIANA_JOYCE_IMO.csv")
    
    if not no_enrolados.empty:
        no_enrolados.to_csv("FALTANTES_IMO_DIANA_JOYCE.csv", index=False)
        print("Reporte generado: FALTANTES_IMO_DIANA_JOYCE.csv")

    # Muestra de resultados
    print("\nRESUMEN DE ASIGNACIONES:")
    print(f"Total Asignados: {len(df_asig_filt)}")
    print(f"Total Validados en IMO: {len(merged)}")
    print(f"Pendientes de Enrolamiento: {len(no_enrolados)}")

if __name__ == "__main__":
    cruce_final()
