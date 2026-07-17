import pandas as pd
import sqlite3
import os
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
FALTANTES_CSV = BASE_DIR / "REPORTE_MJ_LIMA_FALTANTES.csv"
FUENTES = [
    Path(r"C:\Users\josem\Downloads\participantes_2026-05-11.csv"),
    BASE_DIR / "Google_Contacts_EQUIPO27.csv",
    BASE_DIR / "campana_imos_c1_e27.xlsx",
    BASE_DIR / "Asignacion_C1.xlsx"
]

def profundizar_busqueda_mj():
    print("--- INICIANDO BUSQUEDA PROFUNDA DE DATOS (337 PAX) ---")
    if not FALTANTES_CSV.exists():
        print("No se encontro el reporte de faltantes.")
        return

    df_missing = pd.read_csv(FALTANTES_CSV)
    df_missing['NOMBRE_BUSQUEDA'] = df_missing['NOMBRE_COMPLETO'].str.upper().str.strip()
    
    # Cargar todas las fuentes de contacto
    data_fuentes = []
    for f in FUENTES:
        if f.exists():
            try:
                if f.suffix == '.csv':
                    # Usamos latin1 y skip para el archivo grande de participantes
                    df_f = pd.read_csv(f, on_bad_lines='skip', encoding='latin1')
                else:
                    df_f = pd.read_excel(f)
                
                # Normalizar nombres en fuentes
                name_cols = [c for c in df_f.columns if any(k in c.lower() for k in ['nombre', 'pax', 'name'])]
                if name_cols:
                    df_f['NOMBRE_MATCH'] = df_f[name_cols[0]].astype(str).str.upper().str.strip()
                    data_fuentes.append(df_f)
            except: pass

    # Resultados
    recuperados = []
    for idx, row in df_missing.iterrows():
        encontrado = False
        for df_f in data_fuentes:
            match = df_f[df_f['NOMBRE_MATCH'] == row['NOMBRE_BUSQUEDA']]
            if not match.empty:
                # Extraer primer telefono y email disponible
                tel_col = [c for c in df_f.columns if any(k in c.lower() for k in ['tel', 'cel', 'imo', 'phone', 'whatsapp'])]
                mail_col = [c for c in df_f.columns if any(k in c.lower() for k in ['mail', 'correo'])]
                
                tel = str(match.iloc[0][tel_col[0]]) if tel_col else "-"
                mail = str(match.iloc[0][mail_col[0]]) if mail_col else "-"
                
                recuperados.append({
                    "NOMBRE": row['NOMBRE_COMPLETO'],
                    "EQUIPO": row['EQUIPO_MJ'],
                    "TELEFONO": tel,
                    "EMAIL": mail,
                    "FUENTE": row['ORIGEN'] + " -> " + str(match.iloc[0].get('fuente_origen', 'CSV/DB'))
                })
                encontrado = True
                break
        
        if not encontrado:
            recuperados.append({
                "NOMBRE": row['NOMBRE_COMPLETO'],
                "EQUIPO": row['EQUIPO_MJ'],
                "TELEFONO": "NO ENCONTRADO",
                "EMAIL": "NO ENCONTRADO",
                "FUENTE": row['ORIGEN']
            })

    df_final = pd.DataFrame(recuperados)
    output_path = BASE_DIR / "MJ_LIMA_INTEGRACION_TOTAL_CON_CONTACTOS.csv"
    df_final.to_csv(output_path, index=False)
    
    encontrados_count = len(df_final[df_final['TELEFONO'] != "NO ENCONTRADO"])
    print(f"Busqueda finalizada. Datos recuperados para {encontrados_count} de {len(df_missing)} participantes.")
    print(f"Archivo generado: {output_path.name}")

if __name__ == "__main__":
    profundizar_busqueda_mj()
