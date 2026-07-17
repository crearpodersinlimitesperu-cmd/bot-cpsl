import pandas as pd
import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\MAESTRIA DEL JUEGO GLOBAL\Equipos\Lima")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def find_names_in_df(df):
    """Busca nombres de participantes en cualquier columna del dataframe."""
    names = []
    # Ignorar las primeras filas si son puras NaN o ruido de encabezado
    df = df.dropna(how='all').reset_index(drop=True)
    
    for col in df.columns:
        col_data = df[col].dropna().astype(str)
        # Filtro: debe tener al menos 2 palabras (Nombre Apellido) y no ser un encabezado comun
        potential_names = col_data[col_data.str.contains(' ') & 
                                   ~col_data.str.upper().isin(['NOMBRE', 'PARTICIPANTE', 'PX', 'EQUIPO', 'SENTADOS'])]
        for name in potential_names:
            if len(name) > 5 and name.isupper(): # Los nombres en estos excels suelen estar en MAYUSCULAS
                names.append(name.strip().upper())
    return list(set(names))

def audit_mj_lima_pro():
    print("--- INICIANDO AUDITORIA MAESTRA MJ LIMA (MODO GREEDY) ---")
    all_pax_data = []

    for root, dirs, files in os.walk(BASE_DIR):
        for file in files:
            if "SEGUIMIENTO" in file.upper() and file.endswith(".xlsx"):
                file_path = Path(root) / file
                print(f"Escaneando: {file}")
                try:
                    df = pd.read_excel(file_path, header=None) # Sin header para no perder la primera fila
                    found_names = find_names_in_df(df)
                    
                    team_name = file_path.parent.name if "EQUIPO" in file_path.parent.name else "LIMA_GENERAL"
                    
                    for name in found_names:
                        all_pax_data.append({
                            'NOMBRE_COMPLETO': name,
                            'EQUIPO_MJ': team_name,
                            'ORIGEN': file
                        })
                except Exception as e:
                    print(f"Error en {file}: {e}")

    if not all_pax_data:
        print("No se encontraron datos.")
        return

    df_mj = pd.DataFrame(all_pax_data).drop_duplicates(subset=['NOMBRE_COMPLETO'])
    print(f"Total PAX MJ detectados (Greedy): {len(df_mj)}")

    # Comparar con DB
    conn = sqlite3.connect(DB_PATH)
    df_db = pd.read_sql("SELECT id, nombre, apellido, maestria FROM participantes", conn)
    df_db['NOMBRE_COMPLETO_DB'] = (df_db['nombre'] + ' ' + df_db['apellido']).str.strip().str.upper()

    merged = df_mj.merge(df_db, left_on='NOMBRE_COMPLETO', right_on='NOMBRE_COMPLETO_DB', how='left')
    
    no_en_db = merged[merged['id'].isna()]
    en_db_no_mj = merged[(merged['id'].notna()) & (merged['maestria'] != 'SI')]

    print(f"PAX MJ faltantes en DB: {len(no_en_db)}")
    print(f"PAX MJ a sincronizar en DB: {len(en_db_no_mj)}")

    cursor = conn.cursor()
    if not en_db_no_mj.empty:
        ids = en_db_no_mj['id'].astype(int).tolist()
        cursor.execute(f"UPDATE participantes SET maestria='SI', c1='SI', c2='SI' WHERE id IN ({','.join(map(str, ids))})")
        print(f"Sincronizados {len(ids)} graduados MJ.")

    if not no_en_db.empty:
        no_en_db[['NOMBRE_COMPLETO', 'EQUIPO_MJ', 'ORIGEN']].to_csv(Path(r"C:\Users\josem\Downloads\bot-cpsl-review\REPORTE_MJ_LIMA_FALTANTES.csv"), index=False)
        print("Reporte generado: REPORTE_MJ_LIMA_FALTANTES.csv")

    conn.commit()
    conn.close()
    print("--- AUDITORIA PRO FINALIZADA ---")

if __name__ == "__main__":
    audit_mj_lima_pro()
