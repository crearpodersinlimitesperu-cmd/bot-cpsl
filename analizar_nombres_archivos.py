import pandas as pd
import sqlite3
from pathlib import Path

# Rutas
INVENTARIO_CSV = "INVENTARIO_EVIDENCIA_VISUAL.csv"
DB_PATH = "torre_control.db"

def analizar():
    print("--- ANALIZANDO NOMBRES DE ARCHIVOS VS PARTICIPANTES ---")
    df_archivos = pd.read_csv(INVENTARIO_CSV)
    
    conn = sqlite3.connect(DB_PATH)
    df_px = pd.read_sql_query("SELECT id, nombre, apellido, telefono FROM participantes", conn)
    conn.close()
    
    df_px['nombre_completo'] = df_px['nombre'].fillna('') + " " + df_px['apellido'].fillna('')
    participantes = df_px.to_dict('records')
    
    hallazgos = []
    
    for _, archivo in df_archivos.iterrows():
        nombre_f = str(archivo['Name']).upper()
        for px in participantes:
            nombre_px = str(px['nombre_completo']).upper()
            if len(nombre_px) > 8 and nombre_px in nombre_f:
                hallazgos.append({
                    "px_id": px['id'],
                    "nombre_px": px['nombre_completo'],
                    "archivo": archivo['Name'],
                    "ruta_completa": archivo['FullName']
                })
                break # Evitar duplicados por archivo
    
    print(f"Total de evidencias vinculadas por nombre: {len(hallazgos)}")
    if hallazgos:
        resumen = pd.DataFrame(hallazgos)
        resumen.to_csv("EVIDENCIAS_VINCULADAS_POR_NOMBRE.csv", index=False)
        print("Reporte generado: EVIDENCIAS_VINCULADAS_POR_NOMBRE.csv")
        print("\nPrimeros 5 hallazgos:")
        print(resumen[['nombre_px', 'archivo']].head(5).to_string())

if __name__ == "__main__":
    analizar()
