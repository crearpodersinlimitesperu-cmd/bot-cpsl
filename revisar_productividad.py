import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'

print(f"Abriendo archivo: {file_path}")

try:
    xl = pd.ExcelFile(file_path)
    sheet_names = xl.sheet_names
    print(f"Pestañas encontradas ({len(sheet_names)}): {sheet_names}")
    
    total_vacios_general = 0
    
    for sheet in sheet_names:
        print(f"\n{'='*80}")
        print(f"PESTAÑA: {sheet}")
        print(f"{'='*80}")
        
        df = pd.read_excel(file_path, sheet_name=sheet)
        
        # Verificar que existen las columnas D y J
        if len(df.columns) >= 10: # Al menos hasta la J (índice 9)
            col_d = df.columns[3] # Índice 3 es D
            col_j = df.columns[9] # Índice 9 es J
            
            print(f"Columna D identificada como: '{col_d}'")
            print(f"Columna J identificada como: '{col_j}'")
            
            # Contar estados en Columna D
            estados_d = df.iloc[:, 3].fillna('VACIO').value_counts()
            print("\nDistribución en Columna D (Asistencia):")
            print(estados_d.to_string())
            
            # Filtrar donde Columna D está vacía
            df_vacio = df[df.iloc[:, 3].isna()]
            total_vacios = len(df_vacio)
            total_vacios_general += total_vacios
            print(f"\nTotal de registros con Asistencia VACÍA: {total_vacios}")
            
            if total_vacios > 0:
                # Resultados de Gestión (Columna J) para esos vacíos
                res_gestion = df_vacio.iloc[:, 9].fillna('SIN GESTIÓN (VACÍO)').value_counts()
                print("\nResultados de Gestión (Columna J) para los que están VACÍOS en Asistencia:")
                print(res_gestion.to_string())
        else:
            print("La pestaña no tiene suficientes columnas (menos de 10).")

    print(f"\n{'='*80}")
    print(f"TOTAL GENERAL DE REGISTROS VACÍOS EN ASISTENCIA: {total_vacios_general}")
    print(f"{'='*80}")

except Exception as e:
    print(f"Error procesando el archivo: {e}")
