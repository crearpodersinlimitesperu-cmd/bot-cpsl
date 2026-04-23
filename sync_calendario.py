import os, json, logging
import pandas as pd
from datetime import datetime

log = logging.getLogger("Calendario")
logging.basicConfig(level=logging.INFO)

EXCEL_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PROGRAMACION 2026 CREAR LIMA.xlsx"
DATA_DIR = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
CALENDARIO_PATH = os.path.join(DATA_DIR, "calendario_entrenamientos.json")

def sincronizar_calendario():
    if not os.path.exists(EXCEL_PATH):
        log.error(f"Archivo Excel no encontrado: {EXCEL_PATH}")
        return False
        
    try:
        df = pd.read_excel(EXCEL_PATH)
        # Limpiar espacios en columnas
        df.columns = [str(c).strip().upper() for c in df.columns]
        
        if 'SEDE' not in df.columns:
            log.error("Columna SEDE no encontrada en el Excel")
            return False
            
        # Filtrar solo LIMA
        lima_df = df[df['SEDE'].astype(str).str.strip().str.upper() == 'LIMA']
        
        eventos = []
        for _, row in lima_df.iterrows():
            try:
                # Intentar parsear las fechas (pueden ser strings o datetime)
                inicio = pd.to_datetime(row['INICIO']).strftime("%Y-%m-%d")
                fin = pd.to_datetime(row['FIN']).strftime("%Y-%m-%d") if 'FIN' in df.columns else None
                if not fin and 'FIN ENTRENAMIENTO' in df.columns:
                    fin = pd.to_datetime(row['FIN ENTRENAMIENTO']).strftime("%Y-%m-%d")
                
                entrenamiento = str(row.get('ENTRENAMIENTO', 'Entrenamiento')).strip()
                
                if inicio and fin:
                    eventos.append({
                        "inicio": inicio,
                        "fin": fin,
                        "nombre": entrenamiento
                    })
            except Exception as e:
                log.warning(f"Error parseando fila: {e}")
                continue
                
        # Guardar en JSON
        with open(CALENDARIO_PATH, 'w', encoding='utf-8') as f:
            json.dump(eventos, f, ensure_ascii=False, indent=2)
            
        log.info(f"Se sincronizaron {len(eventos)} eventos para LIMA.")
        return True
        
    except Exception as e:
        log.error(f"Error procesando el Excel: {e}")
        return False

if __name__ == "__main__":
    sincronizar_calendario()
