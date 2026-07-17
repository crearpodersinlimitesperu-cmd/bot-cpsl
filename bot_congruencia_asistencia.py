import sqlite3
import pandas as pd
import re

def limpiar_dni(val):
    val_str = str(val).strip().replace('.0', '')
    if val_str == 'nan' or not val_str:
        return None
    # Solo mantener digitos
    return re.sub(r'\D', '', val_str)

def congruencia_asistencia():
    print("--- INICIANDO BOT DE CONGRUENCIA DE ASISTENCIA ---")
    
    excel_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Master_Aliados_Consolidado.xlsx'
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    
    # 1. Leer Master_Aliados
    df_c1 = pd.read_excel(excel_path, sheet_name='C1_Raw')
    df_c2 = pd.read_excel(excel_path, sheet_name='C2_Raw')
    
    # Extraer DNIs únicos. La columna de DNI podría llamarse diferente o estar en varias columnas (es raw)
    # Por seguridad buscaremos en todas las columnas de texto algo que parezca un DNI (8 digitos)
    # O asumiremos que la columna 2 o 3 es la identificacion si el formato es el estándar.
    # Como el C2 tiene un formato mas limpio, intentemos buscar la columna que dice "Identificación" o "DNI"
    
    def extraer_dnis(df):
        dnis = set()
        for col in df.columns:
            if 'identi' in str(col).lower() or 'dni' in str(col).lower():
                for val in df[col].dropna():
                    limpio = limpiar_dni(val)
                    if limpio and len(limpio) >= 8:
                        dnis.add(limpio)
        # Si no encontró por nombre de columna, barrer todo
        if len(dnis) < 50:
            for col in df.columns:
                for val in df[col].dropna():
                    limpio = limpiar_dni(val)
                    if limpio and len(limpio) >= 8 and len(limpio) <= 12:
                        dnis.add(limpio)
        return list(dnis)

    dnis_c1 = extraer_dnis(df_c1)
    dnis_c2 = extraer_dnis(df_c2)
    
    print(f"DNI extraidos de C1_Raw: {len(dnis_c1)}")
    print(f"DNI extraidos de C2_Raw: {len(dnis_c2)}")
    
    # 2. Actualizar BD
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    actualizados_c1 = 0
    actualizados_c2 = 0
    
    # Actualizar C1
    for dni in dnis_c1:
        cursor.execute("UPDATE participantes SET c1 = 'SI' WHERE identificacion = ? AND c1 != 'SI'", (dni,))
        actualizados_c1 += cursor.rowcount
        
    # Actualizar C2
    for dni in dnis_c2:
        cursor.execute("UPDATE participantes SET c2 = 'SI', es_pendiente_real = 'NO' WHERE identificacion = ? AND c2 != 'SI'", (dni,))
        actualizados_c2 += cursor.rowcount
        
    conn.commit()
    print(f"Registros en BD actualizados a C1='SI': {actualizados_c1}")
    print(f"Registros en BD actualizados a C2='SI': {actualizados_c2}")
    
    # 3. Auditoria de Vacios (Asistieron pero no tienen email o no tienen IMO)
    # Todos los C1='SI' o C2='SI' que no tengan email o imo
    query_alertas = """
    SELECT identificacion, nombre, apellido, telefono, c1, c2, email, imo 
    FROM participantes 
    WHERE (c1 = 'SI' OR c2 = 'SI') 
      AND (email IS NULL OR email = '' OR email = 'None' OR email = 'nan' 
           OR imo IS NULL OR imo = '' OR imo = 'None' OR imo = 'nan')
    """
    df_alertas = pd.read_sql_query(query_alertas, conn)
    alertas_path = r'C:\Users\josem\Downloads\bot-cpsl-review\alertas_inconsistencias.csv'
    df_alertas.to_csv(alertas_path, index=False, encoding='utf-8')
    
    print(f"Generadas {len(df_alertas)} alertas de inconsistencia en {alertas_path}")
    
    conn.close()
    print("--- CONGRUENCIA APLICADA EXITOSAMENTE ---")

if __name__ == "__main__":
    congruencia_asistencia()
