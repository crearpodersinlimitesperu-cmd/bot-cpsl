import pandas as pd
import sqlite3
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
REBOTES_CSV = r'C:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv'

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('IDENTIDAD', evento, detalle, estado))
        conn_cn.commit()
    except Exception as e:
        print(f"Error blackbox: {e}")

def corregir_rebotes():
    if not os.path.exists(REBOTES_CSV):
        print("No se encontró el CSV de rebotes.")
        return
        
    df_rebotes = pd.read_csv(REBOTES_CSV)
    emails_rebotados = df_rebotes['email'].dropna().unique()
    
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    correcciones = 0
    
    for email in emails_rebotados:
        email_lower = str(email).lower().strip()
        
        # Marcarlos como REBOTE en la base de datos
        cursor.execute("UPDATE participantes SET email = 'REBOTE' WHERE LOWER(email) = ?", (email_lower,))
        if cursor.rowcount > 0:
            correcciones += cursor.rowcount
            log_blackbox(conn_cn, 'CORRECCION_REBOTE', f'Email marcado como REBOTE: {email_lower}', 'COMPLETADO')
            
    conn.commit()
    print(f"--- CORRECCIÓN DE REBOTES ---")
    print(f"Rebotes únicos procesados: {len(emails_rebotados)}")
    print(f"Registros corregidos en BD: {correcciones}")
    
    log_blackbox(conn_cn, 'CORRECCION_MASIVA_REBOTES', f'Corregidos {correcciones} registros en BD', 'COMPLETADO')
    
    conn.close()
    conn_cn.close()

if __name__ == "__main__":
    corregir_rebotes()
