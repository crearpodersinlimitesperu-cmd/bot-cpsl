import os
import pandas as pd
import sqlite3
from pathlib import Path

# Rutas
ETL_BASE = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\ETL - VENTAS CREAR LIMA - Documentos")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def purificacion_masiva():
    print(f"--- INICIANDO PURIFICACION MASIVA ETL: {ETL_BASE} ---")
    conn = sqlite3.connect(DB_PATH)
    df_maestro = pd.read_sql_query("SELECT id, nombre, apellido, telefono, email, identificacion FROM participantes", conn)
    
    # Normalizar para busqueda
    df_maestro['nombre_completo'] = (df_maestro['nombre'].fillna('') + " " + df_maestro['apellido'].fillna('')).str.upper().str.strip()
    
    hallazgos = []
    
    for root, dirs, files in os.walk(ETL_BASE):
        for f in files:
            if f.lower().endswith(('.xlsx', '.xls', '.csv')):
                full_path = Path(root) / f
                try:
                    if f.lower().endswith('.csv'):
                        df = pd.read_csv(full_path, low_memory=False)
                    else:
                        df = pd.read_excel(full_path)
                    
                    # Normalizar columnas del excel actual
                    df.columns = [str(c).upper().strip() for c in df.columns]
                    
                    # Buscar por nombre en este archivo
                    # Asumimos que hay una columna que contiene el nombre del participante
                    nombre_col = None
                    for col in df.columns:
                        if 'NOMBRE' in col or 'PARTICIPANTE' in col or 'CLIENTE' in col:
                            nombre_col = col
                            break
                    
                    if nombre_col:
                        df[nombre_col] = df[nombre_col].astype(str).str.upper().strip()
                        # Cruce
                        merged = pd.merge(df_maestro, df, left_on='nombre_completo', right_on=nombre_col, how='inner')
                        
                        if not merged.empty:
                            print(f"!!! Hallazgo en {f}: {len(merged)} registros cruzados.")
                            for _, row in merged.iterrows():
                                # Intentar rescatar email o DNI si el maestro no lo tiene
                                if pd.isna(row['EMAIL']) or row['EMAIL'] == '':
                                    # Buscar columna candidata a email en el df actual
                                    for col in df.columns:
                                        if 'MAIL' in col or 'CORREO' in col:
                                            email_val = row[col]
                                            if pd.notna(email_val) and '@' in str(email_val):
                                                hallazgos.append({"id": row['ID'], "campo": "email", "valor": email_val, "origen": f})
                                
                                if pd.isna(row['IDENTIFICACION']) or row['IDENTIFICACION'] == '':
                                    for col in df.columns:
                                        if 'DNI' in col or 'IDENTI' in col or 'DOC' in col:
                                            dni_val = row[col]
                                            if pd.notna(dni_val) and len(str(dni_val)) >= 8:
                                                hallazgos.append({"id": row['ID'], "campo": "identificacion", "valor": dni_val, "origen": f})
                except:
                    continue

    print(f"\nSe han detectado {len(hallazgos)} actualizaciones potenciales.")
    if hallazgos:
        pd.DataFrame(hallazgos).to_csv("ACTUALIZACIONES_MASIVAS_ETL.csv", index=False)
        print("Reporte generado: ACTUALIZACIONES_MASIVAS_ETL.csv")
    
    conn.close()

if __name__ == "__main__":
    purificacion_masiva()
