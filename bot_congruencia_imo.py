import sqlite3
import pandas as pd
import re

def normalizar(val):
    if not val or pd.isna(val): return ""
    return str(val).strip().upper()

def bot_congruencia_imo():
    print("--- INICIANDO BOT DE CONGRUENCIA IMO (VERSION MEJORADA) ---")
    
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    excel_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Master_Aliados_Consolidado.xlsx'
    
    # 1. Cargar datos de la BD
    conn = sqlite3.connect(db_path)
    df_db = pd.read_sql_query("SELECT id, nombre, apellido, telefono, email, imo as imo_db FROM participantes", conn)
    conn.close()
    
    # Normalizar campos de cruce en BD
    df_db['key_nombre'] = (df_db['nombre'].fillna('') + " " + df_db['apellido'].fillna('')).apply(normalizar)
    df_db['key_tel'] = df_db['telefono'].astype(str).str.replace(r'\D', '', regex=True)
    
    # 2. Cargar datos de Aliados
    df_c1 = pd.read_excel(excel_path, sheet_name='C1_Raw')
    df_c2 = pd.read_excel(excel_path, sheet_name='C2_Raw')
    
    def procesar_aliados(df, cap):
        # Intentar normalizar columnas de nombre y apellidos
        # En C1_Raw son NOMBRE, APELLIDOS. En C2_Raw son NOMBRE, APELLIDOS.
        # Pero a veces son NOMBRES, APELLIDO. 
        df_clean = pd.DataFrame()
        
        # Buscar columna de nombre
        col_nom = [c for c in df.columns if str(c).upper() in ['NOMBRE', 'NOMBRES', 'NOMBRE Y APELLIDO ']]
        col_ape = [c for c in df.columns if str(c).upper() in ['APELLIDOS', 'APELLIDO']]
        col_tel = [c for c in df.columns if str(c).upper() in ['TEL.', 'TELEFONO']]
        col_imo = [c for c in df.columns if str(c).upper() == 'IMO']
        
        if col_nom:
            df_clean['nombre_excel'] = df[col_nom[0]].fillna('')
            if col_ape:
                df_clean['apellido_excel'] = df[col_ape[0]].fillna('')
                df_clean['full_name'] = (df_clean['nombre_excel'] + " " + df_clean['apellido_excel']).apply(normalizar)
            else:
                df_clean['full_name'] = df_clean['nombre_excel'].apply(normalizar)
        
        if col_tel:
            df_clean['tel_excel'] = df[col_tel[0]].astype(str).str.replace(r'\D', '', regex=True)
        else:
            df_clean['tel_excel'] = ""
            
        if col_imo:
            df_clean['imo_excel'] = df[col_imo[0]].apply(normalizar)
        else:
            df_clean['imo_excel'] = ""
            
        df_clean['capitulo'] = cap
        return df_clean

    df_aliados_c1 = procesar_aliados(df_c1, 'C1')
    df_aliados_c2 = procesar_aliados(df_c2, 'C2')
    df_aliados = pd.concat([df_aliados_c1, df_aliados_c2], ignore_index=True)
    
    print(f"Total registros en Aliados: {len(df_aliados)}")
    
    # 3. Cruce
    # Cruzamos por nombre completo primero
    merged = pd.merge(df_db, df_aliados, left_on='key_nombre', right_on='full_name', how='inner')
    
    # Reportar discrepancias de IMO
    discrepancias = []
    for _, row in merged.iterrows():
        imo_db = normalizar(row['imo_db'])
        imo_excel = row['imo_excel']
        
        if imo_db != imo_excel and (imo_db or imo_excel):
            discrepancias.append({
                "Participante": row['key_nombre'],
                "Telefono": row['telefono'],
                "IMO_en_BD": imo_db,
                "IMO_en_Excel": imo_excel,
                "Capitulo": row['capitulo']
            })
            
    df_discrepancias = pd.DataFrame(discrepancias)
    output_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Discrepancias_IMO.xlsx'
    df_discrepancias.to_excel(output_path, index=False)
    
    print(f"\nCruce finalizado.")
    print(f"Participantes coincidentes encontrados: {len(merged)}")
    print(f"Discrepancias de IMO detectadas: {len(df_discrepancias)}")
    print(f"Archivo de discrepancias guardado en: {output_path}")

if __name__ == "__main__":
    bot_congruencia_imo()
