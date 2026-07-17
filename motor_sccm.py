import sqlite3
import pandas as pd
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from datetime import datetime
from pathlib import Path
import re

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    # Eliminar tildes y caracteres especiales simples
    texto = re.sub(r'[ÁÀÄÂ]', 'A', texto)
    texto = re.sub(r'[ÉÈËÊ]', 'E', texto)
    texto = re.sub(r'[ÍÌÏÎ]', 'I', texto)
    texto = re.sub(r'[ÓÒÖÔ]', 'O', texto)
    texto = re.sub(r'[ÚÙÜÛ]', 'U', texto)
    texto = re.sub(r'[^A-Z0-9 ]', '', texto)
    return texto

def calcular_similitud(n1, n2):
    # Usamos Token Set Ratio para manejar nombres en diferente orden
    return fuzz.token_set_ratio(normalizar_texto(n1), normalizar_texto(n2))

def iniciar_cruce_maestro():
    print("--- INICIANDO SISTEMA CONGRUENTE DE CRUCE MAESTRO (SCCM) ---")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Cargar todos los participantes
    df = pd.read_sql_query("SELECT id, nombre, apellido, telefono, email, equipo FROM participantes", conn)
    df['nombre_completo'] = df['nombre'].fillna('') + " " + df['apellido'].fillna('')
    df['nombre_norm'] = df['nombre_completo'].apply(normalizar_texto)
    
    posibles_fusiones = []
    procesados = set()

    print(f"Analizando {len(df)} registros buscando duplicados y similitudes...")

    for i, row in df.iterrows():
        if row['id'] in procesados: continue
        
        # Buscar parecidos en el resto del dataframe
        # Filtramos por telefono igual O nombre muy parecido (>85%)
        # Solo comparamos con los que no hemos procesado
        for j, target in df.iloc[i+1:].iterrows():
            if target['id'] in procesados: continue
            
            similitud_nombre = calcular_similitud(row['nombre_norm'], target['nombre_norm'])
            mismo_tel = (str(row['telefono']) == str(target['telefono']) and str(row['telefono']) != '')
            
            if mismo_tel or similitud_nombre > 88:
                posibles_fusiones.append({
                    "id_a": row['id'],
                    "nombre_a": row['nombre_completo'],
                    "equipo_a": row['equipo'],
                    "id_b": target['id'],
                    "nombre_b": target['nombre_completo'],
                    "equipo_b": target['equipo'],
                    "score": similitud_nombre if not mismo_tel else 100,
                    "motivo": "Mismo Teléfono" if mismo_tel else f"Similitud {similitud_nombre}%"
                })
                # No marcamos como procesado aun para permitir multiples hallazgos, 
                # pero en un sistema real podriamos agrupar.

    conn.close()
    
    print(f"Se han detectado {len(posibles_fusiones)} posibles duplicados/fusiones.")
    
    # Guardar reporte de fusiones para revision humana
    if posibles_fusiones:
        reporte_df = pd.DataFrame(posibles_fusiones)
        reporte_df.to_csv(BASE_DIR / "REPORTE_FUSIONES_SCCM.csv", index=False)
        print("REPORTE_FUSIONES_SCCM.csv generado con éxito.")
    
    return posibles_fusiones

if __name__ == "__main__":
    iniciar_cruce_maestro()
