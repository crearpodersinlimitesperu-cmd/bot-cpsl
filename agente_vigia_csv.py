import os
import sys
import time
import json
import sqlite3
import pandas as pd
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
WATCH_DIR = r"G:\Mi unidad\SUBDIRECCIÓN LIMA - Documentos\_PENDIENTE REVISAR"
STATE_FILE = os.path.join(BASE_DIR, ".agente_vigia_state.json")
LOG_FILE = os.path.join(BASE_DIR, "agente_vigia.log")

def log(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def get_processed_files():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_processed_files(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)

def fusionar_cupo(conn, id_antiguo, id_nuevo):
    """
    Transfiere C1, C2, maestria y relaciones del id_antiguo al id_nuevo, y luego borra el antiguo.
    Similar a la lógica de fusionar_perfiles.
    """
    c = conn.cursor()
    c.execute("SELECT * FROM participantes WHERE id = ?", (id_antiguo,))
    antiguo = c.fetchone()
    c.execute("SELECT * FROM participantes WHERE id = ?", (id_nuevo,))
    nuevo = c.fetchone()
    
    if not antiguo or not nuevo:
        return False
        
    p_dict = dict(nuevo) # principal
    d_dict = dict(antiguo) # duplicado/antiguo
    
    update_fields = {}
    # Transferir C1, C2, maestria si el nuevo no lo tiene y el antiguo sí
    for key in ['c1', 'c2', 'maestria', 'tiene_cambio_cupo']:
        if p_dict.get(key) in [None, 'NO', '', 'PENDIENTE'] and d_dict.get(key) in ['SI', 'ACTIVO']:
            update_fields[key] = 'SI'
            
    # Transferir notas/observaciones si el nuevo está vacío
    if not p_dict.get('observaciones') and d_dict.get('observaciones'):
        update_fields['observaciones'] = d_dict.get('observaciones')
        
    if update_fields:
        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
        params = list(update_fields.values()) + [id_nuevo]
        c.execute(f"UPDATE participantes SET {set_clause}, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?", params)
        
    # Re-enrutar relaciones
    nombre_ant = f"{d_dict.get('nombre', '')} {d_dict.get('apellido', '')}".strip()
    nombre_nue = f"{p_dict.get('nombre', '')} {p_dict.get('apellido', '')}".strip()
    
    if nombre_ant and nombre_nue:
        c.execute("UPDATE participantes SET imo = ? WHERE imo = ?", (nombre_nue, nombre_ant))
        
    c.execute("UPDATE relaciones SET px_id = ? WHERE px_id = ?", (id_nuevo, id_antiguo))
    c.execute("UPDATE relaciones SET relacionado_id = ?, nombre_relacionado = ? WHERE relacionado_id = ?", 
              (id_nuevo, nombre_nue, id_antiguo))
              
    # Borrar el antiguo
    c.execute("DELETE FROM participantes WHERE id = ?", (id_antiguo,))
    return True

def procesar_csv(filepath):
    log(f"Procesando archivo: {os.path.basename(filepath)}")
    try:
        # Intentar utf-8, si falla intentar latin-1
        try:
            df = pd.read_csv(filepath, sep=';', encoding="utf-8")
        except UnicodeDecodeError:
            df = pd.read_csv(filepath, sep=';', encoding="latin-1")
            
        df = df.fillna('')
        
        # Buscar las columnas sin importar mayúsculas o tildes
        cols = {c.strip().lower(): c for c in df.columns}
        
        col_dni = next((c for k, c in cols.items() if 'identificaci' in k or 'dni' in k), None)
        col_cupo = next((c for k, c in cols.items() if 'cambio cupo' in k), None)
        col_nom = next((c for k, c in cols.items() if 'nombre' in k and 'equipo' not in k), None)
        col_ape = next((c for k, c in cols.items() if 'apellido' in k), None)
        
        if not col_dni or not col_nom or not col_ape:
            log("Error: No se encontraron las columnas necesarias en el CSV (Identificación, Nombre, Apellido).")
            return False
            
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        actualizados = 0
        cambios_cupo = 0
        
        for _, row in df.iterrows():
            dni_nuevo = str(row.get(col_dni, '')).strip()
            nombre = str(row.get(col_nom, '')).strip()
            apellido = str(row.get(col_ape, '')).strip()
            
            if not dni_nuevo:
                continue
                
            dni_antiguo = str(row.get(col_cupo, '')).strip() if col_cupo else ""
            es_cambio_cupo = dni_antiguo and dni_antiguo != "-" and dni_antiguo.lower() != "no" and dni_antiguo != dni_nuevo
            
            # Buscar si el DNI nuevo existe
            c.execute("SELECT id FROM participantes WHERE identificacion = ?", (dni_nuevo,))
            res_nuevo = c.fetchone()
            
            if es_cambio_cupo:
                # Buscar a la persona original
                c.execute("SELECT id FROM participantes WHERE identificacion = ?", (dni_antiguo,))
                res_antiguo = c.fetchone()
                
                if res_antiguo:
                    id_antiguo = res_antiguo['id']
                    if res_nuevo:
                        # Ambos existen -> Fusionar antiguo en nuevo
                        id_nuevo = res_nuevo['id']
                        if fusionar_cupo(conn, id_antiguo, id_nuevo):
                            # Actualizar nombre del nuevo por si acasi
                            c.execute("UPDATE participantes SET nombre = ?, apellido = ? WHERE id = ?", (nombre, apellido, id_nuevo))
                            cambios_cupo += 1
                    else:
                        # Solo existe el antiguo -> Actualizar el DNI y Nombre del antiguo al nuevo (Transferencia directa)
                        c.execute("""
                            UPDATE participantes 
                            SET identificacion = ?, nombre = ?, apellido = ?, tiene_cambio_cupo = 'SI', fecha_actualizacion = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (dni_nuevo, nombre, apellido, id_antiguo))
                        cambios_cupo += 1
            else:
                # Actualización de nombres normal
                if res_nuevo:
                    c.execute("""
                        UPDATE participantes 
                        SET nombre = ?, apellido = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                        WHERE identificacion = ?
                    """, (nombre, apellido, dni_nuevo))
                    actualizados += 1
                    
        conn.commit()
        conn.close()
        log(f"Completado. Nombres actualizados: {actualizados}. Cambios de cupo procesados: {cambios_cupo}.")
        return True
    except Exception as e:
        log(f"Error procesando {os.path.basename(filepath)}: {e}")
        return False

def main_loop():
    log("Iniciando Agente Vigía de CSVs...")
    log(f"Monitoreando: {WATCH_DIR}")
    
    if not os.path.exists(WATCH_DIR):
        log(f"Advertencia: La ruta {WATCH_DIR} no existe. Se reintentará más tarde.")
        
    # Process once immediately
    try:
        if os.path.exists(WATCH_DIR):
            state = get_processed_files()
            archivos = [f for f in os.listdir(WATCH_DIR) if f.lower().startswith('participantes_') and f.lower().endswith('.csv')]
            
            for f in archivos:
                filepath = os.path.join(WATCH_DIR, f)
                mtime = os.path.getmtime(filepath)
                
                if f not in state or state[f] < mtime:
                    if procesar_csv(filepath):
                        state[f] = mtime
                        save_processed_files(state)
    except Exception as e:
        log(f"Error en paso inicial: {e}")

    # Enter background loop
    while True:
        try:
            time.sleep(30)
            if os.path.exists(WATCH_DIR):
                state = get_processed_files()
                archivos = [f for f in os.listdir(WATCH_DIR) if f.lower().startswith('participantes_') and f.lower().endswith('.csv')]
                
                for f in archivos:
                    filepath = os.path.join(WATCH_DIR, f)
                    mtime = os.path.getmtime(filepath)
                    
                    if f not in state or state[f] < mtime:
                        if procesar_csv(filepath):
                            state[f] = mtime
                            save_processed_files(state)
                            
        except KeyboardInterrupt:
            log("Agente Vigía detenido manualmente.")
            break
        except Exception as e:
            log(f"Error en el ciclo principal: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
