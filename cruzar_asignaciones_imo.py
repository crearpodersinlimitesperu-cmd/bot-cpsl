import pandas as pd
import sqlite3
from fuzzywuzzy import fuzz
from pathlib import Path

# Rutas
ASIG_PATH = Path(r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\Asignacion_C1.xlsx")
IMO_PATH = Path(r"C:\Users\josem\Downloads\Hojas de Cálculo\participantes_2026-05-11.csv")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def normalizar_nombre(n):
    return str(n).upper().strip()

def cruce_tactico():
    print("--- INICIANDO CRUCE TACTICO: ASIGNACION VS IMO ---")
    
    # 1. Cargar Asignaciones (Filtrar por Diana y Joyce)
    try:
        df_asig = pd.read_excel(ASIG_PATH)
        # Buscar columna de coordinadora
        coordinadora_col = None
        for col in df_asig.columns:
            if 'COORDINADORA' in col.upper() or 'ASIG' in col.upper() or 'CC' in col.upper():
                coordinadora_col = col
                break
        
        if coordinadora_col:
            df_asig = df_asig[df_asig[coordinadora_col].astype(str).str.contains('DIANA|JOYCE', case=False, na=False)]
            print(f"Participantes en Asignacion (Diana/Joyce): {len(df_asig)}")
        else:
            print("No se encontro columna de Coordinadora en Asignacion. Procesando base completa.")
    except Exception as e:
        print(f"Error al leer Asignaciones: {e}")
        return

    # 2. Cargar IMO (Robusto a lineas malas)
    try:
        df_imo = pd.read_csv(IMO_PATH, on_bad_lines='skip', engine='python')
        print(f"Participantes en IMO: {len(df_imo)}")
    except Exception as e:
        print(f"Error al leer IMO: {e}")
        return

    # 3. Cruce por Nombre
    # Buscamos columnas de nombres
    asig_nombre_col = next((c for c in df_asig.columns if 'NOMBRE' in c.upper()), df_asig.columns[0])
    imo_nombre_col = next((c for c in df_imo.columns if 'NOMBRE' in c.upper()), df_imo.columns[0])

    df_asig['nombre_norm'] = df_asig[asig_nombre_col].apply(normalizar_nombre)
    df_imo['nombre_norm'] = df_imo[imo_nombre_col].apply(normalizar_nombre)

    # Cruce
    print("Realizando cruce de datos...")
    merged = pd.merge(df_asig, df_imo, on='nombre_norm', how='inner', suffixes=('_asig', '_imo'))
    print(f"Cruces exitosos encontrados: {len(merged)}")

    # 4. Reporte de Hallazgos
    if not merged.empty:
        merged.to_csv("CRUCE_ASIGNACION_IMO_DIANA_JOYCE.csv", index=False)
        print("Reporte generado: CRUCE_ASIGNACION_IMO_DIANA_JOYCE.csv")
        
        # Mostrar muestra
        print("\nMuestra de Cruce:")
        cols_to_show = [asig_nombre_col] + ([coordinadora_col] if coordinadora_col else [])
        print(merged[cols_to_show].head(10).to_string())
    else:
        print("No se encontraron coincidencias exactas entre Asignacion e IMO.")

if __name__ == "__main__":
    cruce_tactico()
