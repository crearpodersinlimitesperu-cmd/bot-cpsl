"""
SÚPER AGENTE VIGILANTE UNIFICADO DE ALIADOS C1 Y C2 - CREAR PODER SIN LÍMITES
=============================================================================
Monitorea cada hora de manera autónoma los archivos Excel en OneDrive de:
1. PORCENTAJE ALIADOS C1 (Equipos 10 al 28)
2. PORCENTAJE ALIADOS C2 (Equipos 9 al 27)

Recorre todas las pestañas (visibles y ocultas) de cada libro Excel, extrae las relaciones
de Aliados C1, Aliados C2 e IMOs, resuelve sus IDs en la base de datos central (torre_control.db)
soporta redirección de participantes fusionados e integra la auditoría en caja_negra.db.
"""
import os
import sys
import re
import glob
import shutil
import sqlite3
import unicodedata
import openpyxl
import pandas as pd
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = r"C:\Users\josem\Downloads\bot-cpsl-review"
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
CAJA_NEGRA_PATH = os.path.join(BASE_DIR, "caja_negra.db")
TEMP_DIR = os.path.join(BASE_DIR, "scratch")
ONEDRIVE_C1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"
ONEDRIVE_C2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2"

def norm(text):
    if not text or pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def log_blackbox(action, details, status="SUCCESS"):
    try:
        conn = sqlite3.connect(CAJA_NEGRA_PATH, timeout=60.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (datetime('now', 'localtime'), 'VIGILANTE_ALIADOS', ?, ?, ?)
        """, (action, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error escribiendo en caja negra: {e}", file=sys.stderr)

def split_names(name_str):
    if not name_str or pd.isna(name_str):
        return []
    s = str(name_str).strip()
    s = s.replace('//', '|').replace('/', '|').replace(' AND ', '|').replace(' and ', '|')
    s = re.sub(r'\s+[ye]\s+', '|', s, flags=re.IGNORECASE)
    parts = [p.strip() for p in s.split('|') if p.strip()]
    return parts

def obtener_id_principal_redireccionado(pid, conn_or_cursor=None):
    if not pid:
        return pid
    if conn_or_cursor is None:
        try:
            conn = sqlite3.connect(DB_PATH, timeout=60.0)
            c = conn.cursor()
            row = c.execute("SELECT id_principal FROM redirecciones_fusiones WHERE id_eliminado = ?", (pid,)).fetchone()
            conn.close()
            if row:
                return obtener_id_principal_redireccionado(row[0])
        except:
            pass
    else:
        try:
            cursor = conn_or_cursor if hasattr(conn_or_cursor, 'execute') else conn_or_cursor.cursor()
            row = cursor.execute("SELECT id_principal FROM redirecciones_fusiones WHERE id_eliminado = ?", (pid,)).fetchone()
            if row:
                return obtener_id_principal_redireccionado(row[0], conn_or_cursor)
        except:
            pass
    return pid

def resolve_name_in_db(name_str, db_participants, min_score=85, conn_or_cursor=None):
    name_norm = norm(name_str)
    if not name_norm or len(name_norm) < 4:
        return None, ""
        
    if name_norm in ['staff', 'apoyos', 'sombras', 'responsable', 'creador cuantico', 'sin aliado', 'ninguno', 'no tiene', '-', 'sin asignar']:
        return None, ""
        
    words = name_norm.split()
    matches = []
    
    # Heurística 1: Coincidencia exacta de palabras
    for pid, db_name, db_norm in db_participants:
        if all(w in db_norm for w in words):
            matches.append((pid, db_name))
            
    pid_found = None
    name_found = ""
    
    if len(matches) == 1:
        pid_found, name_found = matches[0][0], matches[0][1]
    elif len(matches) > 1:
        for pid, db_name in matches:
            db_norm = norm(db_name)
            if sorted(db_norm.split()) == sorted(words):
                pid_found, name_found = pid, db_name
                break
        if not pid_found:
            pid_found, name_found = matches[0][0], matches[0][1]
        
    # Heurística 2: Coincidencia Fuzzy
    if not pid_found:
        best_cand = None
        max_score = 0
        for pid, db_name, db_norm in db_participants:
            score = fuzz.token_set_ratio(name_norm, db_norm)
            if score > max_score:
                max_score = score
                best_cand = (pid, db_name)
                
        if max_score >= min_score and best_cand:
            pid_found, name_found = best_cand[0], best_cand[1]
            
    if pid_found:
        # Redirección si fue eliminado por fusión
        pid_found = obtener_id_principal_redireccionado(pid_found, conn_or_cursor)
        return pid_found, name_found
        
    return None, name_str.strip()

def process_excel_file(file_path, is_c2, db_participants, conn):
    c = conn.cursor()
    filename = os.path.basename(file_path)
    
    # Determinar el número de equipo
    eq_match = re.search(r"EQUIPO\s+(\d+)", filename, re.IGNORECASE)
    team_num = int(eq_match.group(1)) if eq_match else 0
    if team_num == 0:
        print(f"  [WARN] No se pudo determinar el número de equipo en '{filename}'")
        return False, "Nombre de archivo inválido"
        
    prefix = "C2" if is_c2 else "C1"
    context = f"{prefix}_E{team_num}"
    
    # Copia temporal local
    temp_excel = os.path.join(TEMP_DIR, f"temp_aliados_{prefix}_e{team_num}.xlsx")
    try:
        shutil.copy2(file_path, temp_excel)
    except Exception as e:
        print(f"  Error copiando {filename} a temporal: {e}")
        return False, f"Copia temporal fallida: {e}"
        
    # Extraer todas las pestañas (visibles y ocultas)
    try:
        wb = openpyxl.load_workbook(temp_excel, read_only=False)
        sheet_names = [sheet.title for sheet in wb.worksheets]
        wb.close()
    except Exception as e:
        print(f"  Error leyendo pestañas con openpyxl en {filename}: {e}")
        if os.path.exists(temp_excel):
            os.remove(temp_excel)
        return False, f"Lectura openpyxl fallida: {e}"
        
    # Limpiar todas las relaciones previas de este contexto en la DB
    # Esto elimina relaciones obsoletas de una ejecución anterior de OneDrive
    c.execute("DELETE FROM relaciones WHERE tipo IN ('ALIADO_C1', 'ALIADO_C2', 'IMO') AND contexto = ?", (context,))
    
    total_aliados = 0
    total_imos = 0
    
    # Procesar cada pestaña que parezca relevante
    for sheet in sheet_names:
        sheet_upper = sheet.upper()
        if not any(k in sheet_upper for k in ['PX', 'ALIADO', 'ALIADOS', 'SALTO', 'SALTOS', 'BORRADOR']):
            continue
            
        try:
            xl = pd.ExcelFile(temp_excel)
            df = xl.parse(sheet)
            xl.close()
            
            # Limpiar columnas
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Buscar columnas
            col_nombres = next((col for col in df.columns if any(k in col for k in ['NOMBRE', 'NOMBRES']) and 'PREFIERE' not in col and 'APELLIDO' not in col), None)
            col_apellidos = next((col for col in df.columns if any(k in col for k in ['APELLIDO', 'APELLIDOS'])), None)
            col_fullname = next((col for col in df.columns if any(k in col for k in ['NOMBRES APELLIDOS', 'NOMBRE COMPLETO', 'CREAR CUANTICO', 'CREADOR CUANTICO'])), None)
            col_aliado = next((col for col in df.columns if any(k in col for k in ['ALIADO', 'ALIADOS'])), None)
            col_imo = next((col for col in df.columns if 'IMO' in col and 'TEL' not in col and 'NUM' not in col), None)
            
            # Si no hay forma de encontrar el nombre del participante, omitir la pestaña
            if not col_fullname and (not col_nombres or not col_apellidos):
                continue
                
            for idx, row in df.iterrows():
                # Obtener nombre del PX
                if col_fullname and not pd.isna(row.get(col_fullname)):
                    px_fullname = str(row.get(col_fullname)).strip()
                else:
                    n = str(row.get(col_nombres, '')).strip() if col_nombres else ''
                    a = str(row.get(col_apellidos, '')).strip() if col_apellidos else ''
                    px_fullname = f"{n} {a}".strip()
                    
                if not px_fullname or px_fullname.lower() in ['nan', '', '-']:
                    continue
                    
                # Resolver PX en DB (con soporte de redirección de fusiones)
                px_id, db_px_name = resolve_name_in_db(px_fullname, db_participants, min_score=85, conn_or_cursor=c)
                if not px_id:
                    continue
                    
                # A. Aliados
                if col_aliado:
                    aliado_raw = str(row.get(col_aliado, '')).strip()
                    if aliado_raw and aliado_raw.lower() not in ['nan', '', '-', 'sin aliado', 'ninguno', 'no tiene', 'sin asignar']:
                        aliados = split_names(aliado_raw)
                        tipo_aliado = 'ALIADO_C2' if is_c2 else 'ALIADO_C1'
                        for al in aliados:
                            rel_id, rel_name = resolve_name_in_db(al, db_participants, min_score=85, conn_or_cursor=c)
                            c.execute("""
                                INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                                VALUES (?, ?, ?, ?, ?)
                            """, (px_id, rel_id, rel_name or al.strip(), tipo_aliado, context))
                            total_aliados += 1
                            
                # B. IMOs
                if col_imo:
                    imo_raw = str(row.get(col_imo, '')).strip()
                    if imo_raw and imo_raw.lower() not in ['nan', '', '-', 'sin asignar', 'ninguno']:
                        rel_id, rel_name = resolve_name_in_db(imo_raw, db_participants, min_score=85, conn_or_cursor=c)
                        c.execute("""
                            INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                            VALUES (?, ?, ?, 'IMO', ?)
                        """, (px_id, rel_id, rel_name or imo_raw.strip(), context))
                        total_imos += 1
                        
                        # Actualizar el campo imo en la tabla participantes para mayor consistencia
                        c.execute("UPDATE participantes SET imo = ? WHERE id = ?", (rel_name or imo_raw.strip(), px_id))
                        
            conn.commit()
        except Exception as e:
            print(f"    [WARN] Error procesando pestaña '{sheet}' en {filename}: {e}")
            
    # Limpiar archivo temporal
    if os.path.exists(temp_excel):
        os.remove(temp_excel)
        
    print(f"  [OK] {filename} ({context}) | Aliados: {total_aliados} | IMOs: {total_imos}")
    return True, f"Aliados: {total_aliados}, IMOs: {total_imos}"

def run_agent():
    print("=================================================================")
    print("   INICIANDO SUPER AGENTE: VIGILANTE DE ALIADOS C1 Y C2")
    print("=================================================================")
    
    # 1. Cargar participantes para mapeo fuzzy
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        c = conn.cursor()
        c.execute("SELECT id, nombre, apellido FROM participantes")
        db_data = c.fetchall()
        db_participants = []
        for pid, nombre, apellido in db_data:
            fullname = f"{nombre or ''} {apellido or ''}".strip()
            db_participants.append((pid, fullname, norm(fullname)))
        print(f"Cargados {len(db_participants)} participantes del CRM.")
    except Exception as e:
        print(f"Error cargando participantes de la DB: {e}")
        log_blackbox("ERROR_CARGA_DB", str(e), "ERROR")
        return False
        
    success_count = 0
    total_files = 0
    errors = []
    
    # 2. Procesar Aliados C1
    print("\n--- PROCESANDO CARPETA ALIADOS C1 ---")
    if os.path.exists(ONEDRIVE_C1):
        c1_files = glob.glob(os.path.join(ONEDRIVE_C1, "*.xlsx"))
        for f in c1_files:
            if os.path.basename(f).startswith("Formato"):
                continue
            total_files += 1
            ok, msg = process_excel_file(f, is_c2=False, db_participants=db_participants, conn=conn)
            if ok:
                success_count += 1
            else:
                errors.append(f"C1 {os.path.basename(f)}: {msg}")
    else:
        print(f"  [WARN] Carpeta C1 no existe: {ONEDRIVE_C1}")
        
    # 3. Procesar Aliados C2
    print("\n--- PROCESANDO CARPETA ALIADOS C2 ---")
    if os.path.exists(ONEDRIVE_C2):
        c2_files = glob.glob(os.path.join(ONEDRIVE_C2, "*.xlsx"))
        for f in c2_files:
            if os.path.basename(f).startswith("Formato"):
                continue
            total_files += 1
            ok, msg = process_excel_file(f, is_c2=True, db_participants=db_participants, conn=conn)
            if ok:
                success_count += 1
            else:
                errors.append(f"C2 {os.path.basename(f)}: {msg}")
    else:
        print(f"  [WARN] Carpeta C2 no existe: {ONEDRIVE_C2}")
        
    conn.close()
    
    summary_msg = f"Sincronizados con éxito {success_count}/{total_files} archivos Excel de aliados C1 y C2."
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
