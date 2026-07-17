import sqlite3
import pandas as pd
import re

def normalizar(val):
    if not val or pd.isna(val): return ""
    return str(val).strip().upper()

def find_imos_to_update():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    excel_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Master_Aliados_Consolidado.xlsx'
    
    conn = sqlite3.connect(db_path)
    # Solo los que no tienen IMO
    df_missing = pd.read_sql_query("SELECT identificacion, nombre, apellido FROM participantes WHERE (imo IS NULL OR imo = '' OR imo = '-' OR imo = 'None') AND es_pendiente_real = 'SI'", conn)
    conn.close()
    
    df_missing['full_name'] = (df_missing['nombre'].fillna('') + " " + df_missing['apellido'].fillna('')).apply(normalizar)
    
    # Cargar Aliados
    df_c1 = pd.read_excel(excel_path, sheet_name='C1_Raw')
    df_c2 = pd.read_excel(excel_path, sheet_name='C2_Raw')
    
    def extract_names_imos(df):
        cols_nom = [c for c in df.columns if str(c).upper() in ['NOMBRE', 'NOMBRES', 'NOMBRE Y APELLIDO ']]
        cols_ape = [c for c in df.columns if str(c).upper() in ['APELLIDOS', 'APELLIDO']]
        cols_imo = [c for c in df.columns if str(c).upper() == 'IMO']
        
        data = []
        for _, row in df.iterrows():
            nom = ""
            if cols_nom: nom = str(row[cols_nom[0]])
            if cols_ape: nom += " " + str(row[cols_ape[0]])
            
            imo = ""
            if cols_imo: imo = str(row[cols_imo[0]])
            
            data.append({"name": normalizar(nom), "imo": normalizar(imo)})
        return pd.DataFrame(data)

    df_a1 = extract_names_imos(df_c1)
    df_a2 = extract_names_imos(df_c2)
    df_aliados = pd.concat([df_a1, df_a2], ignore_index=True)
    
    results = []
    for _, row_px in df_missing.iterrows():
        # Buscar en aliados
        match = df_aliados[df_aliados['name'] == row_px['full_name']]
        if not match.empty:
            imo_name = match.iloc[0]['imo']
            if imo_name and imo_name != '-':
                results.append({
                    "DNI_PX": row_px['identificacion'],
                    "Nombre_PX": row_px['full_name'],
                    "IMO_Name": imo_name
                })
    
    df_results = pd.DataFrame(results)
    print(f"Encontrados {len(df_results)} participantes con IMO en Excel para actualizar.")
    print(df_results)
    
    # Ahora necesito el DNI de esos IMOs
    if not df_results.empty:
        conn = sqlite3.connect(db_path)
        df_all_names = pd.read_sql_query("SELECT identificacion, nombre, apellido FROM participantes", conn)
        df_all_names['full_name'] = (df_all_names['nombre'].fillna('') + " " + df_all_names['apellido'].fillna('')).apply(normalizar)
        name_to_dni = dict(zip(df_all_names['full_name'], df_all_names['identificacion']))
        
        df_results['DNI_IMO'] = df_results['IMO_Name'].apply(lambda x: name_to_dni.get(x, "No encontrado"))
        conn.close()
        
    df_results.to_csv(r'C:\Users\josem\Downloads\bot-cpsl-review\update_web_imos.csv', index=False)
    print("Lista guardada en update_web_imos.csv")

if __name__ == "__main__":
    find_imos_to_update()
