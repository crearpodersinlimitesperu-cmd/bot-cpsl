import sqlite3
import os
import pandas as pd
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
SEARCH_DIR = Path(r"C:\Users\josem\Downloads")
ONEDRIVE_DIR = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA")

def buscar_en_db():
    print("--- BUSCANDO EN BASE DE DATOS ---")
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT * FROM participantes 
        WHERE (nombre LIKE '%CESAR%' OR apellido LIKE '%CESAR%')
          AND (nombre LIKE '%MIRKO%' OR apellido LIKE '%MIRKO%')
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    if not df.empty:
        print(df.to_string())
    else:
        print("No se encontró a 'Cesar Mirko' en la base de datos central.")

def buscar_en_archivos():
    print("\n--- ESCANEANDO ARCHIVOS DE EXCEL Y CSV ---")
    keywords = ["CESAR", "MIRKO"]
    rutas_a_escanear = [SEARCH_DIR, ONEDRIVE_DIR]
    
    encontrados = []
    
    for base_path in rutas_a_escanear:
        if not base_path.exists(): continue
        print(f"Escaneando: {base_path}")
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(('.xlsx', '.csv', '.xls')):
                    full_path = Path(root) / file
                    try:
                        if file.endswith('.csv'):
                            df = pd.read_csv(full_path, low_memory=False)
                        else:
                            df = pd.read_excel(full_path, engine='openpyxl')
                        
                        # Convertir todo a string para búsqueda rápida
                        mask = df.apply(lambda row: row.astype(str).str.contains('CESAR', case=False).any() and 
                                                    row.astype(str).str.contains('MIRKO', case=False).any(), axis=1)
                        matches = df[mask]
                        if not matches.empty:
                            print(f"!!! COINCIDENCIA EN: {full_path.name}")
                            print(matches.to_string())
                            encontrados.append(full_path)
                    except:
                        continue
    
    if not encontrados:
        print("No se detectaron archivos con la mención 'Cesar Mirko'.")

if __name__ == "__main__":
    buscar_en_db()
    buscar_en_archivos()
