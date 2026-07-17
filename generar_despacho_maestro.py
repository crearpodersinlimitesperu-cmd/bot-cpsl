import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("torre_control.db")
BLACK_LIST = Path("PATRONES_MAESTROS_2AÑOS.csv")

def generar_despacho_final():
    print("--- GENERANDO LISTA DE DESPACHO DESDE TORRE DE CONTROL ---")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. Cargar base de Diana/Joyce (Asignacion C1)
    query = """
        SELECT id, nombre, apellido, telefono, email, imo, tel_imo 
        FROM participantes 
        WHERE (cc_nombre LIKE '%DIANA%' OR cc_nombre LIKE '%JOYCE%')
          AND c1 = 'NO'
    """
    df = pd.read_sql_query(query, conn)
    
    # 2. Cargar Blacklist Forense
    df_bl = pd.read_csv(BLACK_LIST)
    rebotes_historicos = set(df_bl[df_bl['Tipo'] == 'REBOTE']['Email'].dropna().astype(str).str.lower().tolist())
    rechazos_historicos = set(df_bl[df_bl['Tipo'] == 'RECHAZO']['Email'].dropna().astype(str).str.lower().tolist())

    despacho = []
    
    for _, row in df.iterrows():
        email = str(row['email']).lower().strip()
        nombre = f"{row['nombre']} {row['apellido']}"
        
        if email in rechazos_historicos:
            continue
        elif email in rebotes_historicos or pd.isna(row['email']) or email == 'nan' or email == '':
            canal = "SMS_RESCATE"
        else:
            canal = "EMAIL_OFICIAL"

        despacho.append({
            "ID": row['id'],
            "Nombre": nombre,
            "Canal": canal,
            "Destino_PX": row['telefono'] if canal == "SMS_RESCATE" else email,
            "Telefono_PX": row['telefono'],
            "Destino_IMO": row['tel_imo'],
            "Nombre_IMO": row['imo'],
            "Motivo": "VALIDADO_FORENSE"
        })

    df_final = pd.DataFrame(despacho)
    df_final.to_csv("DESPACHO_MAESTRO_C1_EJECUCION.csv", index=False)
    conn.close()
    
    print(f"Total a contactar: {len(df_final)}")
    print(df_final['Canal'].value_counts().to_string())
    print(f"\nArchivo de ejecuci\u00f3n listo: DESPACHO_MAESTRO_C1_EJECUCION.csv")

if __name__ == "__main__":
    generar_despacho_final()

if __name__ == "__main__":
    generar_despacho_final()
