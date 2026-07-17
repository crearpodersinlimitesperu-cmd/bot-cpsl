import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

def registrar_log(categoria, evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB, timeout=30.0)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def clean_name(name):
    return str(name).strip().upper()

def cruzar_imo_enrolados():
    print("--- INICIANDO CRUCE MAESTRO IMO <-> ENROLADOS (RESCATE DE TELEFONOS) ---")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    
    # 1. Obtener lista de todos los IMOs mencionados
    df_px = pd.read_sql("SELECT id, nombre, apellido, telefono, imo, tel_imo FROM participantes", conn)
    df_px['FULL_NAME'] = (df_px['nombre'].fillna('') + ' ' + df_px['apellido'].fillna('')).apply(clean_name)
    
    imos_mencionados = df_px[df_px['imo'].notna() & (df_px['imo'] != '')]['imo'].unique()
    print(f"Analizando {len(imos_mencionados)} IMOs únicos mencionados...")
    
    encontrados = 0
    actualizados = 0
    
    cursor = conn.cursor()
    # Pre-build a lightweight list of tuples for fast iteration
    px_records = [(row.FULL_NAME, str(row.telefono), len(row.FULL_NAME)) for row in df_px.itertuples(index=False)]
    
    for imo_name in imos_mencionados:
        imo_clean = clean_name(imo_name)
        
        # Buscar al IMO en la lista pre-construida
        matches = [(full_name, tel, flen) for full_name, tel, flen in px_records if imo_clean in full_name or full_name in imo_clean]
        
        if matches:
            encontrados += 1
            # Ordenar por longitud de FULL_NAME descendente (equivalente a sort_values original)
            matches.sort(key=lambda x: x[2], reverse=True)
            imo_real_tel = matches[0][1]
            
            if imo_real_tel and imo_real_tel not in ('nan', 'None', ''):
                cursor.execute("""
                    UPDATE participantes 
                    SET tel_imo = ? 
                    WHERE imo = ? AND (tel_imo IS NULL OR tel_imo = '' OR tel_imo = 'nan')
                """, (imo_real_tel, imo_name))
                if cursor.rowcount > 0:
                    actualizados += cursor.rowcount

    conn.commit()
    conn.close()
    
    msg = f"Cruce finalizado. IMOs localizados en DB: {encontrados}. Registros sanados con teléfono: {actualizados}."
    print(msg)
    registrar_log('AUDITORIA', 'CRUCE_IMO_ENROLADOS', msg, "EXITO")

if __name__ == "__main__":
    cruzar_imo_enrolados()
