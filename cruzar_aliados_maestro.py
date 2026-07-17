import pandas as pd
import sqlite3
import os
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"
ONEDRIVE_PATH = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA")

def registrar_log(categoria, evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def cruzar_data_aliados():
    print("--- INICIANDO CRUCE MAESTRO DE ALIADOS ---")
    
    # 1. Localizar archivos de los equipos más recientes
    equipos_objetivo = ["26", "27"]
    archivos_encontrados = []
    
    c1_folder = ONEDRIVE_PATH / "PORCENTAJE ALIADOS C1"
    for eq in equipos_objetivo:
        path = c1_folder / f"ALIADOS CAPÍTULO UNO EQUIPO {eq}.xlsx"
        if path.exists(): archivos_encontrados.append(path)

    if not archivos_encontrados:
        print("No se localizaron los archivos de Aliados en la ruta de OneDrive.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    rescatados = 0
    actualizados = 0
    
    for path in archivos_encontrados:
        print(f"Procesando: {path.name}...")
        try:
            # Leer específicamente la pestaña 'PX'
            df = pd.read_excel(path, engine='openpyxl', sheet_name='PX')
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            # Mapeo de columnas específicas detectadas en la auditoría
            col_nom = 'NOMBRES'
            col_ape = 'APELLIDOS'
            col_tel = 'TEL.'
            col_status = 'STATUS'
            
            if col_nom not in df.columns or col_tel not in df.columns:
                print(f"Saltando {path.name}: Estructura de columnas no reconocida.")
                continue

            for _, row in df.iterrows():
                nombre = str(row[col_nom]).strip().upper()
                apellido = str(row[col_ape]).strip().upper()
                telefono = str(row[col_tel]).replace('.0', '').strip()
                status = str(row.get(col_status, '')).upper()
                
                if len(telefono) < 9: continue

                # Lógica de actualización avanzada
                cursor.execute("""
                    UPDATE participantes 
                    SET telefono = COALESCE(NULLIF(telefono, ''), ?),
                        c2 = CASE WHEN ? = 'C2' THEN 'SI' ELSE c2 END,
                        es_pendiente_real = CASE WHEN ? IN ('DESERTOR', 'C2') THEN 'NO' ELSE es_pendiente_real END,
                        resultado_gestion = 'SYNC_PX_SHEET_OK'
                    WHERE (LOWER(nombre) LIKE ?) AND (LOWER(apellido) LIKE ?)
                """, (telefono, status, status, f"%{nombre.lower()}%", f"%{apellido.lower()}%"))
                
                if cursor.rowcount > 0:
                    actualizados += cursor.rowcount
                    rescatados += 1

        except Exception as e:
            print(f"Error procesando {path.name}: {e}")

    conn.commit()
    conn.close()
    
    res = f"Cruce finalizado. Registros enriquecidos: {rescatados}. Filas afectadas en CRM: {actualizados}."
    print(res)
    registrar_log("AUDITORIA_CRUCE", "CRUCE_ALIADOS", res)

if __name__ == "__main__":
    cruzar_data_aliados()
