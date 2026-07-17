import sqlite3
import pandas as pd
from pathlib import Path
import os

# Estandarización de rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"

def identify_missing_imos_vectorized():
    print("--- INICIANDO BUSQUEDA Y RESCATE VECTORIZADO ---")
    if not DB_PATH.exists():
        print(f"DB no encontrada en {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    
    # 1. Cargar PAX sin tel_imo
    df_missing = pd.read_sql("SELECT id, nombre, apellido, equipo, tel_imo FROM participantes WHERE (tel_imo IS NULL OR tel_imo IN ('', 'nan', '0'))", conn)
    if df_missing.empty:
        print("No hay participantes con tel_imo faltante.")
        conn.close()
        return
    
    df_missing['nombre_busqueda'] = (df_missing['nombre'] + ' ' + df_missing['apellido']).str.lower().str.strip()
    print(f"PAX a rescatar: {len(df_missing)}")

    # 2. Cargar fuentes alternativas
    fuentes_paths = [
        BASE_DIR / "Google_Contacts_EQUIPO27.csv",
        BASE_DIR / "campana_imos_c1_e27.xlsx",
        BASE_DIR / "Asignacion_C1.xlsx"
    ]
    
    data_fuentes = []
    for fp in fuentes_paths:
        if fp.exists():
            try:
                df_f = pd.read_csv(fp) if fp.suffix == '.csv' else pd.read_excel(fp)
                df_f['fuente_origen'] = fp.name
                data_fuentes.append(df_f)
            except Exception as e:
                print(f"Error cargando {fp.name}: {e}")

    if not data_fuentes:
        print("No hay fuentes alternativas disponibles.")
        conn.close()
        return

    # 3. Consolidar fuentes y vectorizar búsqueda
    df_all_fuentes = pd.concat(data_fuentes, ignore_index=True)
    
    # Identificar columnas de contacto dinámicamente
    cols_cont = [c for c in df_all_fuentes.columns if any(k in c.lower() for k in ['imo', 'tel', 'cel', 'whatsapp'])]
    if not cols_cont:
        print("No se encontraron columnas de contacto en las fuentes.")
        conn.close()
        return

    # Crear columna unificada de nombre en fuentes para el merge
    cols_name = [c for c in df_all_fuentes.columns if any(k in c.lower() for k in ['nombre', 'pax', 'participante', 'name'])]
    if not cols_name:
        print("No se encontraron columnas de nombre en las fuentes.")
        conn.close()
        return
    
    df_all_fuentes['nombre_busqueda'] = df_all_fuentes[cols_name[0]].str.lower().str.strip()
    
    # Extraer el primer número válido
    def extract_digits(val):
        d = "".join(filter(str.isdigit, str(val)))
        if len(d) >= 9:
            if len(d) == 9 and not d.startswith('51'): return '51' + d
            return d
        return None

    df_all_fuentes['IMO_FINAL'] = df_all_fuentes[cols_cont].bfill(axis=1).iloc[:, 0].apply(extract_digits)
    df_all_fuentes = df_all_fuentes.dropna(subset=['IMO_FINAL', 'nombre_busqueda']).drop_duplicates('nombre_busqueda')

    # 4. Merge Vectorizado
    df_merged = df_missing.merge(df_all_fuentes[['nombre_busqueda', 'IMO_FINAL', 'fuente_origen']], on='nombre_busqueda', how='inner')
    
    # 5. Actualización Masiva
    if not df_merged.empty:
        cursor = conn.cursor()
        updates = [(row['IMO_FINAL'], int(row['id'])) for _, row in df_merged.iterrows()]
        cursor.executemany("UPDATE participantes SET tel_imo = ? WHERE id = ?", updates)
        conn.commit()
        
        # Generar Reporte
        report_path = BASE_DIR / "RESCATE_IMOS_RESULTADOS_V2.csv"
        df_merged.to_csv(report_path, index=False)
        print(f"RESCATE EXITOSO: {len(df_merged)} IMOs recuperados.")
    else:
        print("No se encontraron coincidencias en el cruce masivo.")

    conn.close()

if __name__ == "__main__":
    identify_missing_imos_vectorized()
