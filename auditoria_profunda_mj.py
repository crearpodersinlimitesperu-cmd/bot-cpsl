import pandas as pd
import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\MAESTRIA DEL JUEGO GLOBAL\Equipos\Lima")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def audit_mj_lima():
    print("--- INICIANDO AUDITORIA PROFUNDA MJ LIMA ---")
    all_participants = []

    # 1. Escanear todos los archivos de seguimiento en carpetas de equipos
    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if "SEGUIMIENTO" in file.upper() and file.endswith(".xlsx"):
                file_path = Path(root) / file
                print(f"Procesando: {file}")
                try:
                    df = pd.read_excel(file_path)
                    # Normalizar columnas (buscamos 'NOMBRE' o similar)
                    df.columns = [str(c).strip().upper() for c in df.columns]
                    
                    name_col = next((c for c in df.columns if "NOMBRE" in c or "PARTICIPANTE" in c), None)
                    team_col = next((c for c in df.columns if "EQUIPO" in c), None)
                    
                    if name_col:
                        # Extraer datos básicos
                        temp_df = df[[name_col]].copy()
                        temp_df['ORIGEN'] = file
                        if team_col:
                            temp_df['EQUIPO_MJ'] = df[team_col]
                        else:
                            temp_df['EQUIPO_MJ'] = file_path.parent.name
                        
                        all_participants.append(temp_df.rename(columns={name_col: 'NOMBRE_COMPLETO'}))
                except Exception as e:
                    print(f"Error en {file}: {e}")

    if not all_participants:
        print("No se encontraron datos de participantes.")
        return

    df_mj = pd.concat(all_participants, ignore_index=True).dropna(subset=['NOMBRE_COMPLETO'])
    df_mj['NOMBRE_COMPLETO'] = df_mj['NOMBRE_COMPLETO'].astype(str).str.strip().str.upper()
    print(f"Total registros MJ encontrados: {len(df_mj)}")

    # 2. Comparar con la DB principal
    conn = sqlite3.connect(DB_PATH)
    df_db = pd.read_sql("SELECT id, nombre, apellido, maestria FROM participantes", conn)
    df_db['NOMBRE_COMPLETO_DB'] = (df_db['nombre'] + ' ' + df_db['apellido']).str.strip().str.upper()

    # Cruce para ver quiénes faltan o están desactualizados
    # Usamos merge por nombre
    merged = df_mj.merge(df_db, left_on='NOMBRE_COMPLETO', right_on='NOMBRE_COMPLETO_DB', how='left')
    
    no_en_db = merged[merged['id'].isna()]
    en_db_no_mj = merged[(merged['id'].notna()) & (merged['maestria'] != 'SI')]

    print(f"Participantes MJ que NO están en la DB principal: {len(no_en_db)}")
    print(f"Participantes MJ en DB pero marcados como NO graduados MJ: {len(en_db_no_mj)}")

    # 3. Acciones correctivas
    cursor = conn.cursor()
    
    # Marcar como SI a los que están en DB pero no marcados como MJ
    if not en_db_no_mj.empty:
        ids_to_update = en_db_no_mj['id'].astype(int).tolist()
        cursor.execute(f"UPDATE participantes SET maestria='SI', c1='SI', c2='SI' WHERE id IN ({','.join(map(str, ids_to_update))})")
        print(f"Sincronizados {len(ids_to_update)} participantes como Graduados MJ.")

    # Para los que NO están en la DB, generamos un reporte para revisión
    if not no_en_db.empty:
        no_en_db[['NOMBRE_COMPLETO', 'EQUIPO_MJ', 'ORIGEN']].to_csv(Path(r"C:\Users\josem\Downloads\bot-cpsl-review\PAX_MJ_FALTANTES_EN_DB.csv"), index=False)
        print("Reporte de PAX faltantes generado: PAX_MJ_FALTANTES_EN_DB.csv")

    conn.commit()
    conn.close()
    print("--- AUDITORIA MJ FINALIZADA ---")

if __name__ == "__main__":
    audit_mj_lima()
