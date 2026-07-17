"""
AGENTE VIGILANTE Y NORMALIZADOR COMPLETO DE GRADUADOS Y STAFF - CREAR PODER SIN LÍMITES
=====================================================================================
Supervisa, normaliza y audita de forma diaria y autónoma:
1. El estado de graduados (alineado a 365 graduados únicos en la pestaña visible 'GRADUADOS ').
2. El historial de staff y apoyos recorriendo todas las pestañas (ocultas y visibles) del Excel.
3. Actualiza las tablas 'participantes' y 'trayectoria_staff' de forma atómica y limpia.
4. Genera un análisis clínico-sistémico de cambios usando IA gratuita (ia_multimodelo.py).
5. Registra logs de auditoría en caja_negra.db.
"""
import os
import sys
import shutil
import sqlite3
import unicodedata
import re
import openpyxl
import pandas as pd
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = r"C:\Users\josem\Downloads\bot-cpsl-review"
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
CAJA_NEGRA_PATH = os.path.join(BASE_DIR, "caja_negra.db")
TEMP_EXCEL = os.path.join(BASE_DIR, "scratch", "temp_graduados_completo.xlsx")
GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"

# IDs protegidos que no se deben fusionar ni eliminar bajo ninguna circunstancia
PROTECTED_IDS = {283, 3173, 3883, 4024, 4647}

def norm(text):
    if not text or pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def obtener_primer_nombre(fullname):
    parts = fullname.split()
    return parts[0] if parts else ""

def log_blackbox(action, details, status="SUCCESS"):
    try:
        conn = sqlite3.connect(CAJA_NEGRA_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (datetime('now', 'localtime'), 'VIGILANTE_GRADUADOS_Y_STAFF', ?, ?, ?)
        """, (action, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error escribiendo en caja negra: {e}", file=sys.stderr)

def parse_sheet_metadata(sheet_name):
    sheet_upper = sheet_name.upper()
    
    # 1. Capítulo
    if 'CAP 1' in sheet_upper or 'CAP1' in sheet_upper or 'C1' in sheet_upper:
        capitulo = 'C1'
    elif 'CAP 2' in sheet_upper or 'CAP2' in sheet_upper or 'C2' in sheet_upper:
        capitulo = 'C2'
    elif 'MJ' in sheet_upper:
        capitulo = 'MJ'
    elif 'CAMINATA' in sheet_upper:
        capitulo = 'CAMINATA'
    else:
        capitulo = 'C1'
        
    # 2. Rol
    if 'STAFF ELITE' in sheet_upper:
        rol = 'STAFF ELITE'
    elif 'APOYO' in sheet_upper:
        rol = 'APOYO'
    elif 'SOMBRA' in sheet_upper or 'SOMBRAS' in sheet_upper:
        rol = 'SOMBRA'
    elif 'MANAGER' in sheet_upper or 'MANAGERS' in sheet_upper:
        rol = 'MANAGER'
    elif 'CONFIANZA' in sheet_upper:
        rol = 'APOYO CONFIANZA'
    else:
        rol = 'APOYO'
        
    # 3. Equipo Evento
    eq_match = re.search(r'E\s*(\d+[\d\-\s]*)', sheet_upper)
    if eq_match:
        equipo = f"E{eq_match.group(1).replace(' ', '')}"
    elif 'EQUIPO' in sheet_upper:
        eq_match = re.search(r'EQUIPO\s*(\d+)', sheet_upper)
        equipo = f"E{eq_match.group(1)}" if eq_match else "N/A"
    else:
        equipo = "N/A"
        
    return rol, capitulo, equipo

def find_name_column(df):
    best_col = None
    max_names = 0
    for col in df.columns:
        count = 0
        for val in df[col].dropna():
            val_str = str(val).strip()
            if len(val_str) > 7 and len(val_str) < 50:
                words = val_str.split()
                if len(words) >= 2 and not any(c.isdigit() for c in val_str):
                    val_upper = val_str.upper()
                    if not any(x in val_upper for x in ['CONFIRM', 'OBSERVACION', 'EQUIPO', 'ESTADO', 'GROUNDING', 'VIERNES', 'SABADO', 'DOMINGO', 'RESPONSABLE', 'TOTAL', 'LEYENDA', 'Unnamed:']):
                        count += 1
        if count > max_names:
            max_names = count
            best_col = col
    return best_col

def obtener_id_principal_redireccionado(pid, conn_or_cursor=None):
    if not pid:
        return pid
    if conn_or_cursor is None:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            row = c.execute("SELECT id_principal FROM redirecciones_fusiones WHERE id_eliminado = ?", (pid,)).fetchone()
            conn.close()
            if row:
                return obtener_id_principal_redireccionado(row[0])
        except:
            pass
    else:
        try:
            # Funciona si es cursor o connection
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
        
    if name_norm in ['staff', 'apoyos', 'sombras', 'responsable', 'creador cuantico', 'staff elite', 'apoyo']:
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
        # Redireccionar si el ID fue eliminado en una fusión
        pid_found = obtener_id_principal_redireccionado(pid_found, conn_or_cursor)
        return pid_found, name_found
        
    return None, name_str.strip()

def run_graduados_normalization(conn, excel_graduados, db_participants):
    """
    Normaliza el estado de graduados (igual que agente_vigilante_graduados.py)
    """
    c = conn.cursor()
    insertados = 0
    actualizados = 0
    fusionados = 0
    matched_db_ids = set()

    for xl_p in excel_graduados:
        xl_norm = xl_p['nombre_norm']
        xl_first = obtener_primer_nombre(xl_norm)
        xl_tokens = set(xl_norm.split())
        
        candidates = []
        for pid, db_name, db_norm in db_participants:
            db_first = obtener_primer_nombre(db_norm)
            
            # Exigir que compartan el primer nombre
            first_name_score = fuzz.token_set_ratio(xl_first, db_first)
            if first_name_score >= 85:
                db_tokens = set(db_norm.split())
                common_tokens = xl_tokens & db_tokens
                if len(common_tokens) >= 1:
                    score = fuzz.token_set_ratio(xl_norm, db_norm)
                    if score >= 80:
                        # Buscar el registro completo en la DB para pasarlo al candidato
                        c.execute("SELECT * FROM participantes WHERE id = ?", (pid,))
                        row = c.fetchone()
                        if row:
                            db_p_row = dict(row)
                            candidates.append((score, db_p_row))
                        
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        if not candidates:
            # Caso A: No existe -> Crear uno nuevo
            parts = xl_p['nombre_original'].split()
            nombre = parts[0] if parts else ""
            apellido = " ".join(parts[1:]) if len(parts) > 1 else ""
            
            c.execute("""
                INSERT INTO participantes (nombre, apellido, equipo, c1, c2, maestria, tipo, estado, fecha_registro, fecha_actualizacion)
                VALUES (?, ?, ?, 'SI', 'SI', 'SI', 'NUEVO', 'GRADUADO_COMPLETO', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (nombre, apellido, f"EQUIPO {xl_p['equipo_original']}" if xl_p['equipo_original'] else None))
            new_id = c.lastrowid
            matched_db_ids.add(new_id)
            insertados += 1
        else:
            # Caso B: Coincidencias encontradas
            best_cand = candidates[0][1]
            best_id = best_cand['id']
            
            if len(candidates) > 1:
                sorted_candidates = []
                for score, cand in candidates:
                    has_dni = 1 if cand['identificacion'] else 0
                    has_tel = 1 if cand['telefono'] else 0
                    sorted_candidates.append((has_dni, has_tel, cand))
                sorted_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                
                principal_cand = sorted_candidates[0][2]
                principal_id = principal_cand['id']
                
                # Fusionar
                for _, _, dup in sorted_candidates[1:]:
                    dup_id = dup['id']
                    if dup_id == principal_id or dup_id in PROTECTED_IDS:
                        continue
                        
                    update_fields = {}
                    for key in ['identificacion', 'telefono', 'email', 'equipo', 'imo', 'tel_imo', 'cc_asignada', 'cc_nombre', 'cc_tel', 'observaciones']:
                        p_val = principal_cand[key]
                        d_val = dup[key]
                        if (not p_val or str(p_val).strip() == "") and d_val:
                            update_fields[key] = d_val
                            
                    if update_fields:
                        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
                        params = list(update_fields.values()) + [principal_id]
                        c.execute(f"UPDATE participantes SET {set_clause} WHERE id = ?", params)
                        
                    c.execute("UPDATE relaciones SET px_id = ? WHERE px_id = ?", (principal_id, dup_id))
                    c.execute("UPDATE relaciones SET relacionado_id = ?, nombre_relacionado = ? WHERE relacionado_id = ?", 
                              (principal_id, f"{principal_cand['nombre']} {principal_cand['apellido']}".strip(), dup_id))
                    
                    dup_fullname = f"{dup['nombre']} {dup['apellido']}".strip()
                    principal_fullname = f"{principal_cand['nombre']} {principal_cand['apellido']}".strip()
                    c.execute("UPDATE participantes SET imo = ? WHERE imo = ?", (principal_fullname, dup_fullname))
                    
                    # Registrar la fusión para redirección e integridad histórica
                    c.execute("""
                        INSERT OR REPLACE INTO redirecciones_fusiones (id_eliminado, id_principal, nombre_eliminado, nombre_principal, fecha_fusion)
                        VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                    """, (dup_id, principal_id, dup_fullname, principal_fullname))
                    
                    c.execute("DELETE FROM participantes WHERE id = ?", (dup_id,))
                    fusionados += 1
                
                best_id = principal_id
                
            c.execute("UPDATE participantes SET estado = 'GRADUADO_COMPLETO', c1 = 'SI', c2 = 'SI', maestria = 'SI' WHERE id = ?", (best_id,))
            matched_db_ids.add(best_id)
            actualizados += 1

    # Revertir falsos graduados
    c.execute("SELECT id, nombre, apellido, estado FROM participantes WHERE estado = 'GRADUADO_COMPLETO'")
    current_grads = c.fetchall()
    revertidos = 0
    for row in current_grads:
        gid = row[0]
        if gid not in matched_db_ids and gid not in PROTECTED_IDS:
            c.execute("UPDATE participantes SET estado = 'ACTIVO' WHERE id = ?", (gid,))
            revertidos += 1
            
    conn.commit()
    total_db_grad = c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'").fetchone()[0]
    
    return {
        "insertados": insertados,
        "actualizados": actualizados,
        "fusionados": fusionados,
        "revertidos": revertidos,
        "total_db_grad": total_db_grad
    }

def run_agent():
    print("=================================================================")
    print("   INICIANDO SUPER AGENTE: GRADUADOS Y STAFF COMPLETO")
    print("=================================================================")
    
    if not os.path.exists(GRAD_PATH):
        print(f"ERROR: Archivo oficial de graduados no encontrado: {GRAD_PATH}")
        log_blackbox("ERROR_EXCEL_NO_ENCONTRADO", f"No existe {GRAD_PATH}", "ERROR")
        return False
        
    # 1. Copia temporal
    try:
        shutil.copy2(GRAD_PATH, TEMP_EXCEL)
    except Exception as e:
        print(f"Error al copiar archivo: {e}")
        log_blackbox("ERROR_COPIA_TEMP", str(e), "ERROR")
        return False
        
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Asegurar que existe la tabla trayectoria_staff
    c.execute("""
        CREATE TABLE IF NOT EXISTS trayectoria_staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            px_id INTEGER NOT NULL,
            nombre_staff TEXT NOT NULL,
            rol TEXT NOT NULL,
            capitulo TEXT NOT NULL,
            equipo_evento TEXT NOT NULL,
            sheet_name TEXT NOT NULL,
            FOREIGN KEY(px_id) REFERENCES participantes(id),
            UNIQUE(px_id, rol, capitulo, equipo_evento, sheet_name) ON CONFLICT IGNORE
        )
    """)
    conn.commit()
    
    # 2. Cargar participantes de la DB para mapeo
    c.execute("SELECT id, nombre, apellido FROM participantes")
    db_data = c.fetchall()
    db_participants = []
    for row in db_data:
        fullname = f"{row['nombre'] or ''} {row['apellido'] or ''}".strip()
        db_participants.append((row['id'], fullname, norm(fullname)))
        
    # 3. Leer pestaña GRADUADOS
    try:
        df_grad = pd.read_excel(TEMP_EXCEL, sheet_name='GRADUADOS ')
        excel_graduados = []
        for idx, row in df_grad.iterrows():
            nombre_raw = row.get('CREAR CUANTICO')
            eq_original = row.get('EQUIPO ORIGINAL ')
            if pd.isna(nombre_raw):
                continue
            nombre_str = str(nombre_raw).strip()
            if nombre_str and nombre_str.lower() != 'nan':
                excel_graduados.append({
                    'nombre_original': nombre_str,
                    'nombre_norm': norm(nombre_str),
                    'equipo_original': str(eq_original).strip() if not pd.isna(eq_original) else None
                })
    except Exception as e:
        print(f"Error leyendo pestaña GRADUADOS: {e}")
        log_blackbox("ERROR_LECTURA_GRADUADOS", str(e), "ERROR")
        conn.close()
        if os.path.exists(TEMP_EXCEL):
            os.remove(TEMP_EXCEL)
        return False
        
    # Ejecutar normalización de graduados
    print("Normalizando lista de graduados...")
    grad_res = run_graduados_normalization(conn, excel_graduados, db_participants)
    print(f"  Graduados en DB: {grad_res['total_db_grad']} (Excel: {len(excel_graduados)})")
    
    # 4. Procesar Historial de Staff en todas las demás pestañas (visibles y ocultas)
    wb = openpyxl.load_workbook(TEMP_EXCEL, read_only=False)
    sheet_names = [sheet.title for sheet in wb.worksheets]
    wb.close()
    
    staff_inserted = 0
    staff_skipped = 0
    processed_sheets = []
    
    # Registrar conteo previo de trayectoria
    prev_trayectorias = c.execute("SELECT COUNT(*) FROM trayectoria_staff").fetchone()[0]
    
    for sheet in sheet_names:
        sheet_upper = sheet.upper()
        # Filtrar pestañas válidas para trayectoria de staff
        if not any(k in sheet_upper for k in ['STAFF', 'APOYO', 'SOMBRA', 'MANAGER', 'NOCHE DE CONFIANZA', 'Hoja1']):
            continue
            
        # Pestaña 'GRADUADOS ' no es de trayectoria directa de staff
        if sheet.strip() == 'GRADUADOS':
            continue
            
        print(f"Procesando trayectoria de staff en pestaña: '{sheet}'")
        try:
            xl_file = pd.ExcelFile(TEMP_EXCEL)
            df = xl_file.parse(sheet)
            xl_file.close()
            
            # Encontrar columna de nombres
            col_name = find_name_column(df)
            if not col_name:
                print(f"  [WARN] No se detectó columna de nombres en '{sheet}'")
                continue
                
            rol, capitulo, equipo = parse_sheet_metadata(sheet)
            processed_sheets.append(sheet)
            
            # Limpieza atómica de la pestaña para evitar duplicados u obsoletos
            c.execute("DELETE FROM trayectoria_staff WHERE sheet_name = ?", (sheet,))
            
            sheet_inserted = 0
            for idx, row in df.iterrows():
                val = row.get(col_name)
                if pd.isna(val):
                    continue
                val_str = str(val).strip()
                
                # Filtrar ruidos
                if len(val_str) < 5 or any(x in val_str.upper() for x in ['STAFF', 'APOYO', 'SOMBRA', 'MANAGER', 'RESPONSABLE', 'Nº', 'NOCHE', 'CODIGO', 'GROUNDING', 'VIERNES', 'SABADO', 'DOMINGO', 'TOTAL', 'CREADOR CUANTICO', 'ESTADO', 'LEYENDA']):
                    continue
                    
                pid, db_fullname = resolve_name_in_db(val_str, db_participants, min_score=85)
                if pid:
                    c.execute("""
                        INSERT OR IGNORE INTO trayectoria_staff (px_id, nombre_staff, rol, capitulo, equipo_evento, sheet_name)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (pid, val_str, rol, capitulo, equipo, sheet))
                    if c.rowcount > 0:
                        sheet_inserted += 1
                else:
                    staff_skipped += 1
                    
            conn.commit()
            print(f"  [OK] Ingestados {sheet_inserted} registros de staff.")
            staff_inserted += sheet_inserted
            
        except Exception as e:
            print(f"  [ERROR] Procesando pestaña '{sheet}': {e}")
            
    # Registrar conteo final de trayectoria
    curr_trayectorias = c.execute("SELECT COUNT(*) FROM trayectoria_staff").fetchone()[0]
    nuevas_trayectorias = curr_trayectorias - prev_trayectorias
    
    # 5. ANÁLISIS DE CAMBIOS CON IA GRATUITA (ia_multimodelo.py)
    diagnostico_ia = "No se pudo realizar el análisis de IA por fallo de importación."
    try:
        # Agregar directorio al path para importar ia_multimodelo.py
        sys.path.append(BASE_DIR)
        from ia_multimodelo import ia_responder, PROMPTS
        
        PROMPTS["vigilante_graduados"] = (
            "Eres un analista de datos experto en auditoria de CRM de desarrollo humano. "
            "El Agente de CRM acaba de realizar una ejecucion de normalizacion y sincronizacion del Excel de Graduados. "
            "Analiza las estadisticas de la corrida y genera un reporte breve en espanol (max 4 lineas) con un tono profesional, "
            "evaluando la calidad del proceso e indicando si hay algo relevante que requiera revision. No uses emojis."
        )
        
        prompt_ia = (
            f"Resultados de la sincronización del Excel de Graduados:\n"
            f"- Graduados en Excel Oficial: {len(excel_graduados)}\n"
            f"- Conteo Graduados en CRM (DB): {grad_res['total_db_grad']}\n"
            f"- Graduados insertados: {grad_res['insertados']}, actualizados: {grad_res['actualizados']}, "
            f"fusionados/deduplicados: {grad_res['fusionados']}, falsos revertidos: {grad_res['revertidos']}\n"
            f"- Pestañas de staff analizadas: {len(processed_sheets)} (Hojas: {', '.join(processed_sheets[:6])}...)\n"
            f"- Nuevas trayectorias de staff insertadas: {nuevas_trayectorias} (Total en DB: {curr_trayectorias})\n"
            f"- Nombres de staff no emparejados (omitidos): {staff_skipped}\n\n"
            f"Genera el reporte de auditoría:"
        )
        
        res_ia = ia_responder(prompt_ia, contexto="vigilante_graduados", timeout=15)
        if res_ia:
            diagnostico_ia = res_ia.strip()
        else:
            diagnostico_ia = "Sincronización finalizada. Las APIs de IA no respondieron (usando fallback heurístico local)."
    except Exception as e:
        diagnostico_ia = f"Sincronización finalizada. Análisis de IA no disponible: {e}"
        
    conn.commit()
    conn.close()
    
    if os.path.exists(TEMP_EXCEL):
        os.remove(TEMP_EXCEL)
        
    # Escribir log en caja negra con el diagnóstico de la IA
    detalle_final = (
        f"Graduados: {grad_res['total_db_grad']}/{len(excel_graduados)} | "
        f"Staff Ingestado: {staff_inserted} (Omitidos: {staff_skipped}) | "
        f"Reporte IA: {diagnostico_ia}"
    )
    
    # Determinar estado
    log_status = "SUCCESS"
    if grad_res['total_db_grad'] != len(excel_graduados):
        log_status = "WARNING"
        
    log_blackbox("SYNC_COMPLETED", detalle_final, log_status)
    
    print("\n==================================================")
    print("   PROCESO TERMINADO CON ÉXITO")
    print(f"   Graduados en DB: {grad_res['total_db_grad']} (Excel: {len(excel_graduados)})")
    print(f"   Registros de trayectoria de staff: {curr_trayectorias} (Nuevos: {nuevas_trayectorias})")
    print(f"   Nombres de staff omitidos: {staff_skipped}")
    print(f"   Diagnóstico de IA: {diagnostico_ia}")
    print("==================================================")
    return True

if __name__ == '__main__':
    run_agent()
