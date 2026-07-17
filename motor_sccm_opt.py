import sqlite3
import pandas as pd
from fuzzywuzzy import fuzz
from datetime import datetime
from pathlib import Path
import re

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"

def normalizar_texto(texto):
    if not texto: return ""
    texto = str(texto).upper().strip()
    texto = re.sub(r'[ÁÀÄÂ]', 'A', texto)
    texto = re.sub(r'[ÉÈËÊ]', 'E', texto)
    texto = re.sub(r'[ÍÌÏÎ]', 'I', texto)
    texto = re.sub(r'[ÓÒÖÔ]', 'O', texto)
    texto = re.sub(r'[ÚÙÜÛ]', 'U', texto)
    texto = re.sub(r'[^A-Z0-9 ]', '', texto)
    return texto

def calcular_similitud(n1, n2):
    return fuzz.token_set_ratio(n1, n2)

def iniciar_cruce_maestro_optimizado():
    print("--- INICIANDO SCCM OPTIMIZADO (Búsqueda por Prefijos) ---")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT id, nombre, apellido, telefono, equipo FROM participantes", conn)
    df['nombre_completo'] = df['nombre'].fillna('') + " " + df['apellido'].fillna('')
    df['nombre_norm'] = df['nombre_completo'].apply(normalizar_texto)
    df['prefix'] = df['nombre_norm'].str[:3] # Indexar por las primeras 3 letras
    
    posibles_fusiones = []
    
    # Agrupar por prefijo para reducir comparaciones
    grupos = df.groupby('prefix')
    
    print(f"Analizando {len(df)} registros en {len(grupos)} bloques de prefijos...")

    for prefix, grupo in grupos:
        if len(prefix) < 2: continue # Ignorar prefijos muy cortos
        
        records = grupo.to_dict('records')
        for i in range(len(records)):
            for j in range(i + 1, len(records)):
                row = records[i]
                target = records[j]
                
                similitud_nombre = calcular_similitud(row['nombre_norm'], target['nombre_norm'])
                mismo_tel = (str(row['telefono']) == str(target['telefono']) and str(row['telefono']) != '')
                
                if mismo_tel or similitud_nombre > 88:
                    posibles_fusiones.append({
                        "id_a": row['id'], "nombre_a": row['nombre_completo'], "equipo_a": row['equipo'],
                        "id_b": target['id'], "nombre_b": target['nombre_completo'], "equipo_b": target['equipo'],
                        "score": similitud_nombre if not mismo_tel else 100,
                        "motivo": "Mismo Telefono" if mismo_tel else f"Similitud {similitud_nombre}%"
                    })

    conn.close()
    
    print(f"Se han detectado {len(posibles_fusiones)} fusiones potenciales.")
    if posibles_fusiones:
        reporte_df = pd.DataFrame(posibles_fusiones)
        reporte_df.to_csv(BASE_DIR / "REPORTE_FUSIONES_SCCM.csv", index=False)
        print(f"Reporte generado: {len(posibles_fusiones)} casos encontrados.")
        # Mostrar top 5 para validacion rapida
        print("\nEjemplos de Fusiones Detectadas:")
        print(reporte_df[['nombre_a', 'nombre_b', 'motivo']].head(5).to_string())
    
    return posibles_fusiones

if __name__ == "__main__":
    iniciar_cruce_maestro_optimizado()
