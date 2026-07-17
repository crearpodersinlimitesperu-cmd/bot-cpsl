"""
AGENTE VIGILANTE DE RELACIONES DE ALIADOS C1 - CREAR PODER SIN LÍMITES
=====================================================================
Monitorea cada hora los archivos Excel de aliados C1 de los Equipos 10 al 28 en OneDrive,
extrae las relaciones de Aliados C1 e IMOs, resuelve sus IDs en la base de datos central (torre_control.db)
utilizando algoritmos fuzzy de coincidencia de nombres y actualiza el CRM de forma atómica.
Registra el log detallado de la operación en caja_negra.db.
"""
import os
import sys
import re
import glob
import shutil
import sqlite3
import unicodedata
import pandas as pd
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURACIÓN DE RUTA ---
BASE_DIR = r"C:\Users\josem\Downloads\bot-cpsl-review"
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
CAJA_NEGRA_PATH = os.path.join(BASE_DIR, "caja_negra.db")
TEMP_DIR = os.path.join(BASE_DIR, "scratch")
ONEDRIVE_DIR = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"

def norm(text):
    if not text or pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', '', text) # Eliminar caracteres raros
    text = re.sub(r'\s+', ' ', text)
    return text

def log_blackbox(action, details, status="SUCCESS"):
    """Registra la auditoría en caja_negra.db."""
    try:
        conn = sqlite3.connect(CAJA_NEGRA_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (datetime('now', 'localtime'), 'VIGILANTE_ALIADOS_C1', ?, ?, ?)
        """, (action, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error escribiendo en caja negra: {e}", file=sys.stderr)

def split_names(name_str):
    """Separa aliados complejos en nombres individuales."""
    if not name_str or pd.isna(name_str):
        return []
    s = str(name_str).strip()
    s = s.replace('//', '|').replace('/', '|').replace(' AND ', '|').replace(' and ', '|')
    s = re.sub(r'\s+[ye]\s+', '|', s, flags=re.IGNORECASE)
    parts = [p.strip() for p in s.split('|') if p.strip()]
    return parts

def resolve_name_in_db(name_str, db_participants, min_score=85):
    """
    Resuelve el ID de un participante en la base de datos de forma robusta.
    1. Intenta coincidencia exacta de palabras.
    2. Si falla, intenta coincidencia Fuzzy (token_set_ratio) >= min_score.
    """
    name_norm = norm(name_str)
    if not name_norm or len(name_norm) < 4:
        return None, ""
        
    # Ignorar noise típico
    if name_norm in ['staff', 'apoyos', 'sombras', 'responsable', 'creador cuantico', 'sin aliado', 'ninguno', 'no tiene', '-', 'sin asignar']:
        return None, ""
        
    words = name_norm.split()
    
    # Heurística 1: Coincidencia exacta de palabras
    matches = []
    for pid, db_name, db_norm in db_participants:
        if all(w in db_norm for w in words):
            matches.append((pid, db_name))
            
    if len(matches) == 1:
        return matches[0][0], matches[0][1]
    elif len(matches) > 1:
        # Resolver homónimos eligiendo coincidencia de palabras exacta sin importar orden
        for pid, db_name in matches:
            db_norm = norm(db_name)
            if sorted(db_norm.split()) == sorted(words):
                return pid, db_name
        return matches[0][0], matches[0][1]
        
    # Heurística 2: Coincidencia Fuzzy (rapidfuzz token_set_ratio)
    best_cand = None
    max_score = 0
    for pid, db_name, db_norm in db_participants:
        score = fuzz.token_set_ratio(name_norm, db_norm)
        if score > max_score:
            max_score = score
            best_cand = (pid, db_name)
            
    if max_score >= min_score and best_cand:
        return best_cand[0], best_cand[1]
        
    return None, name_str.strip()

def process_team_file(team_num, file_path, db_participants, conn):
    c = conn.cursor()
    filename = os.path.basename(file_path)
    eq_name = f"EQUIPO {team_num}"
    
    # Generar ruta temporal local
    temp_excel = os.path.join(TEMP_DIR, f"temp_aliados_e{team_num}.xlsx")
    
    # 1. Copia temporal
    try:
        shutil.copy2(file_path, temp_excel)
    except Exception as e:
        print(f"Error copiando {filename} a temporal: {e}")
        return False, f"Error copia temporal: {e}"
        
    # 2. Leer Excel
    try:
        xl = pd.ExcelFile(temp_excel)
        sheet_name = 'PX' if 'PX' in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet_name)
        xl.close()
    except Exception as e:
        print(f"Error leyendo {filename}: {e}")
        if os.path.exists(temp_excel):
            try:
                os.remove(temp_excel)
            except:
                pass
        return False, f"Error lectura excel: {e}"
        
    # 3. Limpiar columnas
    df.columns = [str(col).strip().upper() for col in df.columns]
    
    # Identificar columnas
    col_nombres = next((c for c in df.columns if any(k in c for k in ['NOMBRE', 'NOMBRES']) and 'PREFIERE' not in c and 'APELLIDO' not in c), None)
    col_apellidos = next((c for c in df.columns if any(k in c for k in ['APELLIDO', 'APELLIDOS'])), None)
    col_nombres_apellidos = next((c for c in df.columns if 'NOMBRES APELLIDOS' in c or 'NOMBRE COMPLETO' in c), None)
    col_aliado = next((c for c in df.columns if 'ALIADO' in c), None)
    col_imo = next((c for c in df.columns if 'IMO' in c and 'TEL' not in c and 'NUM' not in c), None)
    
    # Validar que al menos tengamos forma de armar el nombre del PX
    if not col_nombres_apellidos and (not col_nombres or not col_apellidos):
        print(f"  [WARN] Columnas de participante no detectadas en {filename}")
        if os.path.exists(temp_excel):
            os.remove(temp_excel)
        return False, "Columnas de participante no detectadas"
        
    # 4. Limpiar relaciones existentes de este equipo/contexto en la DB
    # Esto elimina relaciones viejas y mantiene la coherencia con el Excel de OneDrive
    c.execute("DELETE FROM relaciones WHERE tipo IN ('ALIADO_C1', 'IMO') AND contexto = ?", (eq_name,))
    
    inserted_aliados = 0
    inserted_imos = 0
    skipped_rows = 0
    
    for idx, row in df.iterrows():
        # Obtener nombre del PX
        if col_nombres_apellidos and not pd.isna(row.get(col_nombres_apellidos)):
            px_fullname = str(row.get(col_nombres_apellidos)).strip()
        else:
            n = str(row.get(col_nombres, '')).strip() if col_nombres else ''
            a = str(row.get(col_apellidos, '')).strip() if col_apellidos else ''
            px_fullname = f"{n} {a}".strip()
            
        if not px_fullname or px_fullname.lower() in ['nan', '']:
            continue
            
        # Resolver PX en DB
        px_id, db_px_name = resolve_name_in_db(px_fullname, db_participants, min_score=85)
        if not px_id:
            skipped_rows += 1
            continue
            
        # A. Procesar Aliados
        if col_aliado:
            aliado_raw = str(row.get(col_aliado, '')).strip()
            if aliado_raw and aliado_raw.lower() not in ['nan', '', '-', 'sin aliado', 'ninguno', 'no tiene']:
                aliados = split_names(aliado_raw)
                for al in aliados:
                    rel_id, rel_name = resolve_name_in_db(al, db_participants, min_score=85)
                    c.execute("""
                        INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                        VALUES (?, ?, ?, 'ALIADO_C1', ?)
                    """, (px_id, rel_id, rel_name or al.strip(), eq_name))
                    inserted_aliados += 1
                    
        # B. Procesar IMOs
        if col_imo:
            imo_raw = str(row.get(col_imo, '')).strip()
            if imo_raw and imo_raw.lower() not in ['nan', '', '-', 'sin asignar', 'ninguno']:
                rel_id, rel_name = resolve_name_in_db(imo_raw, db_participants, min_score=85)
                c.execute("""
                    INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                    VALUES (?, ?, ?, 'IMO', ?)
                """, (px_id, rel_id, rel_name or imo_raw.strip(), eq_name))
                inserted_imos += 1
                
                # Actualizar el campo imo en la tabla participantes si no es nulo
                c.execute("UPDATE participantes SET imo = ? WHERE id = ?", (rel_name or imo_raw.strip(), px_id))
                
    conn.commit()
    
    # Limpiar archivo temporal
    if os.path.exists(temp_excel):
        os.remove(temp_excel)
        
    print(f"  [OK] Procesado: {filename} | Aliados C1: {inserted_aliados} | IMOs: {inserted_imos} | Omitidos: {skipped_rows}")
    return True, f"Procesado OK. Aliados: {inserted_aliados}, IMOs: {inserted_imos}, PX Omitidos: {skipped_rows}"

def run_agent():
    print("=================================================================")
    print("   INICIANDO SUPER AGENTE: VIGILANTE DE ALIADOS C1")
    print("=================================================================")
    
    if not os.path.exists(ONEDRIVE_DIR):
        print(f"ERROR: No se encontró la ruta de OneDrive: {ONEDRIVE_DIR}")
        log_blackbox("ERROR_ONEDRIVE_NO_ENCONTRADO", f"Ruta no existe: {ONEDRIVE_DIR}", "ERROR")
        return False
        
    # 1. Cargar participantes de la DB para mapeo en memoria
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, nombre, apellido FROM participantes")
        db_data = c.fetchall()
        
        db_participants = []
        for pid, nombre, apellido in db_data:
            fullname = f"{nombre or ''} {apellido or ''}".strip()
            db_participants.append((pid, fullname, norm(fullname)))
            
        print(f"Cargados {len(db_participants)} participantes del CRM para mapeo.")
    except Exception as e:
        print(f"Error cargando participantes de la DB: {e}")
        log_blackbox("ERROR_CARGA_DB_PARTICIPANTES", str(e), "ERROR")
        return False
        
    # 2. Recorrer Equipos del 10 al 28 y procesar sus archivos
    success_count = 0
    total_files = 0
    errors = []
    
    for team in range(10, 29):
        # Buscar el archivo correspondiente al equipo
        # Soporta nombres como "ALIADOS CAPÍTULO UNO EQUIPO 10.xlsx" o "_ALIADOS CAPÍTULO UNO EQUIPO 11.xlsx"
        pattern1 = os.path.join(ONEDRIVE_DIR, f"*EQUIPO {team}.xlsx")
        pattern2 = os.path.join(ONEDRIVE_DIR, f"*EQUIPO {team} *.xlsx")
        files = glob.glob(pattern1) + glob.glob(pattern2)
        # Quitar duplicados por si acaso
        files = list(set(files))
        
        if not files:
            print(f"  [WARN] No se encontró archivo de Aliados C1 para el Equipo {team}")
            continue
            
        file_path = files[0]
        total_files += 1
        
        ok, msg = process_team_file(team, file_path, db_participants, conn)
        if ok:
            success_count += 1
        else:
            errors.append(f"Equipo {team}: {msg}")
            
    conn.close()
    
    summary_msg = f"Sincronizados con éxito: {success_count}/{total_files} archivos Excel de aliados C1."
    if errors:
        summary_msg += f" Errores detectados: {'; '.join(errors)}"
        log_blackbox("SYNC_COMPLETED_WITH_WARNINGS", summary_msg, "WARNING")
        print(f"\n⚠️ ADVERTENCIA: {summary_msg}")
        return False
    else:
        log_blackbox("SYNC_COMPLETED_SUCCESS", summary_msg, "SUCCESS")
        print(f"\n🎉 ¡ÉXITO! {summary_msg}")
        return True

if __name__ == "__main__":
    run_agent()
