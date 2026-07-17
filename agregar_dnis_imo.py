import sqlite3
import pandas as pd

def normalizar(val):
    if not val or pd.isna(val): return ""
    return str(val).strip().upper()

def agregar_dnis_reporte():
    print("--- AGREGANDO DNIs AL REPORTE DE DISCREPANCIAS ---")
    
    excel_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Discrepancias_IMO.xlsx'
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    
    df = pd.read_excel(excel_path)
    
    conn = sqlite3.connect(db_path)
    
    # Crear un mapa de Nombre Completo -> DNI desde la BD
    # Concatenamos nombre y apellido para buscar
    df_names = pd.read_sql_query("SELECT identificacion, nombre, apellido FROM participantes", conn)
    df_names['full_name'] = (df_names['nombre'].fillna('') + " " + df_names['apellido'].fillna('')).apply(normalizar)
    
    name_to_dni = dict(zip(df_names['full_name'], df_names['identificacion']))
    
    dnis_bd = []
    dnis_excel = []
    
    for _, row in df.iterrows():
        name_bd = normalizar(row['IMO_en_BD'])
        name_excel = normalizar(row['IMO_en_Excel'])
        
        dni_bd = name_to_dni.get(name_bd, "No encontrado")
        dni_excel = name_to_dni.get(name_excel, "No encontrado")
        
        dnis_bd.append(dni_bd)
        dnis_excel.append(dni_excel)
        
    df['DNI_IMO_BD'] = dnis_bd
    df['DNI_IMO_Excel'] = dnis_excel
    
    # Reordenar columnas para que los DNIs estén junto a los nombres
    cols = ['Participante', 'Telefono', 'Capitulo', 'IMO_en_BD', 'DNI_IMO_BD', 'IMO_en_Excel', 'DNI_IMO_Excel']
    df = df[cols]
    
    df.to_excel(excel_path, index=False)
    conn.close()
    print(f"Reporte actualizado con DNIs en: {excel_path}")

if __name__ == "__main__":
    agregar_dnis_reporte()
