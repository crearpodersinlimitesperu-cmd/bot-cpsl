import os
import pandas as pd
import sqlite3
import re
from pathlib import Path

# Rutas
ETL_BASE = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\ETL - VENTAS CREAR LIMA - Documentos")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def deep_cell_purification():
    print(f"--- INICIANDO ESCANEO CELULAR PROFUNDO ETL ---")
    conn = sqlite3.connect(DB_PATH)
    df_maestro = pd.read_sql_query("SELECT id, nombre, apellido, email, identificacion FROM participantes", conn)
    
    # Crear diccionario de busqueda rapida: Nombre -> ID
    px_map = {}
    for _, row in df_maestro.iterrows():
        nombre_full = (str(row['nombre']) + " " + str(row['apellido'])).upper().strip()
        if len(nombre_full) > 8:
            px_map[nombre_full] = row['id']
    
    hallazgos = []
    
    # Expresiones regulares para extraccion
    re_email = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    re_dni = re.compile(r'\b\d{8,11}\b')

    for root, dirs, files in os.walk(ETL_BASE):
        for f in files:
            if f.lower().endswith(('.xlsx', '.xls', '.csv')):
                full_path = Path(root) / f
                try:
                    df = pd.read_excel(full_path, header=None) if not f.lower().endswith('.csv') else pd.read_csv(full_path, header=None)
                    print(f"Procesando: {f} ({len(df)} filas)")
                    
                    for i, row in df.iterrows():
                        row_str = " ".join(row.astype(str).tolist()).upper()
                        
                        # Buscar si algun participante esta en esta fila
                        for nombre, pid in px_map.items():
                            if nombre in row_str:
                                # ¡Encontrado! Extraer datos de la fila
                                current_row_vals = row.astype(str).tolist()
                                
                                found_email = None
                                found_dni = None
                                
                                for val in current_row_vals:
                                    # Buscar email
                                    email_match = re_email.search(val)
                                    if email_match:
                                        found_email = email_match.group(0).lower()
                                    
                                    # Buscar DNI (que no sea el nombre ni el telefono si es posible)
                                    dni_match = re_dni.search(val)
                                    if dni_match:
                                        found_dni = dni_match.group(0)

                                if found_email or found_dni:
                                    hallazgos.append({
                                        "id": pid,
                                        "nombre": nombre,
                                        "email": found_email,
                                        "dni": found_dni,
                                        "origen": f
                                    })
                except Exception as e:
                    continue

    print(f"\nSe han detectado {len(hallazgos)} coincidencias con datos potenciales.")
    if hallazgos:
        res_df = pd.DataFrame(hallazgos).drop_duplicates(subset=['id', 'email', 'dni'])
        res_df.to_csv("ACTUALIZACIONES_DEEP_SCAN.csv", index=False)
        print(f"Reporte generado: ACTUALIZACIONES_DEEP_SCAN.csv ({len(res_df)} registros únicos)")
    
    conn.close()

if __name__ == "__main__":
    deep_cell_purification()
