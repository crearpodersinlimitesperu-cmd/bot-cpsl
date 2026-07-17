"""
AGENTE VIGILANTE Y NORMALIZADOR DE GRADUADOS - CREAR PODER SIN LÍMITES
=====================================================================
Supervisa y normaliza el estado de graduados en el CRM (torre_control.db)
alineándolo estrictamente con los 365 graduados del Excel oficial.
Aplica deduplicación inteligente y estricta (primer nombre) para evitar falsas fusiones.
"""
import os
import sys
import shutil
import sqlite3
import unicodedata
import pandas as pd
from rapidfuzz import fuzz

sys.stdout.reconfigure(encoding='utf-8')

# Configuración de rutas
BASE_DIR = r"C:\Users\josem\Downloads\bot-cpsl-review"
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
TEMP_PATH = os.path.join(BASE_DIR, "scratch", "temp_graduados_vigilante.xlsx")
GRAD_PATH = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx"

# IDs protegidos que no se deben fusionar ni eliminar bajo ninguna circunstancia
PROTECTED_IDS = {283, 3173, 3883, 4024, 4647}

def norm(s):
    if not s or str(s) == 'nan':
        return ''
    s = str(s).strip().upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = ' '.join(s.split())
    return s

def obtener_primer_nombre(fullname):
    parts = fullname.split()
    return parts[0] if parts else ""

def log_blackbox(action, details, status="SUCCESS"):
    try:
        conn = sqlite3.connect(os.path.join(BASE_DIR, "caja_negra.db"))
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (categoria, evento, detalle, estado)
            VALUES ('VIGILANTE_GRADUADOS', ?, ?, ?)
        """, (action, details, status))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error escribiendo en caja negra: {e}")

def run_normalization():
    print("=================================================================")
    print("   INICIANDO AGENTE VIGILANTE: NORMALIZACIÓN DE GRADUADOS (ESTRICTO)")
    print("=================================================================")
    
    if not os.path.exists(GRAD_PATH):
        print(f"ERROR: Archivo oficial no encontrado en {GRAD_PATH}")
        log_blackbox("ERROR_ARCH_NO_ENCONTRADO", f"No se encontró {GRAD_PATH}", "ERROR")
        return False

    # 1. Copia temporal
    try:
        shutil.copy2(GRAD_PATH, TEMP_PATH)
    except Exception as e:
        print(f"ERROR al copiar archivo: {e}")
        log_blackbox("ERROR_COPIA_TEMP", str(e), "ERROR")
        return False

    try:
        df = pd.read_excel(TEMP_PATH, sheet_name='GRADUADOS ')
    except Exception as e:
        print(f"ERROR al leer la pestaña del Excel: {e}")
        log_blackbox("ERROR_LECTURA_EXCEL", str(e), "ERROR")
        if os.path.exists(TEMP_PATH):
            os.remove(TEMP_PATH)
        return False

    # Obtener graduados del Excel
    excel_graduados = []
    for idx, row in df.iterrows():
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

    print(f"Cargados {len(excel_graduados)} graduados desde el Excel oficial.")
    log_blackbox("CARGA_EXCEL", f"Cargados {len(excel_graduados)} graduados oficiales.")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    db_participants = [dict(r) for r in c.execute("SELECT * FROM participantes").fetchall()]
    print(f"Total participantes en DB: {len(db_participants)}")

    insertados = 0
    actualizados = 0
    fusionados = 0
    matched_db_ids = set()

    for xl_p in excel_graduados:
        xl_norm = xl_p['nombre_norm']
        xl_first = obtener_primer_nombre(xl_norm)
        xl_tokens = set(xl_norm.split())
        
        candidates = []
        for db_p in db_participants:
            db_fullname = norm(f"{db_p['nombre']} {db_p['apellido']}")
            db_first = obtener_primer_nombre(db_fullname)
            
            # Exigir que compartan el primer nombre con alta coincidencia Fuzzy
            first_name_score = fuzz.token_set_ratio(xl_first, db_first)
            if first_name_score >= 85:
                # Comprobar tokens en común
                db_tokens = set(db_fullname.split())
                common_tokens = xl_tokens & db_tokens
                if len(common_tokens) >= 1:
                    score = fuzz.token_set_ratio(xl_norm, db_fullname)
                    if score >= 80:
                        candidates.append((score, db_p))
                        
        # Ordenar por puntaje descendente
        candidates.sort(key=lambda x: x[0], reverse=True)
        
        if not candidates:
            # Caso A: No existe en la DB -> Se crea uno nuevo
            print(f"  [+] Creando graduado: '{xl_p['nombre_original']}'")
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
            log_blackbox("CREACION_GRADUADO", f"Creado participante graduado: {xl_p['nombre_original']} (ID {new_id})")
        else:
            # Caso B: Existen una o más coincidencias
            best_cand = candidates[0][1]
            best_id = best_cand['id']
            
            if len(candidates) > 1:
                # Ordenar para elegir el candidato principal (DNI > Tel > ID)
                sorted_candidates = []
                for score, cand in candidates:
                    has_dni = 1 if cand['identificacion'] else 0
                    has_tel = 1 if cand['telefono'] else 0
                    sorted_candidates.append((has_dni, has_tel, cand))
                sorted_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
                
                principal_cand = sorted_candidates[0][2]
                principal_id = principal_cand['id']
                
                # Fusionar duplicados, respetando IDs protegidos
                for _, _, dup in sorted_candidates[1:]:
                    dup_id = dup['id']
                    if dup_id == principal_id or dup_id in PROTECTED_IDS:
                        continue
                        
                    # Unir campos vacíos
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
                        
                    # Re-enrutar relaciones
                    c.execute("UPDATE relaciones SET px_id = ? WHERE px_id = ?", (principal_id, dup_id))
                    c.execute("UPDATE relaciones SET relacionado_id = ?, nombre_relacionado = ? WHERE relacionado_id = ?", 
                              (principal_id, f"{principal_cand['nombre']} {principal_cand['apellido']}".strip(), dup_id))
                    
                    # Re-enrutar imo
                    dup_fullname = f"{dup['nombre']} {dup['apellido']}".strip()
                    principal_fullname = f"{principal_cand['nombre']} {principal_cand['apellido']}".strip()
                    c.execute("UPDATE participantes SET imo = ? WHERE imo = ?", (principal_fullname, dup_fullname))
                    
                    # Eliminar duplicado
                    c.execute("DELETE FROM participantes WHERE id = ?", (dup_id,))
                    print(f"    [-] Fusionado y eliminado duplicado ID {dup_id} con principal ID {principal_id}")
                    fusionados += 1
                    log_blackbox("FUSION_DUPLICADO", f"Fusionado duplicado ID {dup_id} con principal ID {principal_id} ({principal_fullname})")
                
                best_id = principal_id
                
            c.execute("UPDATE participantes SET estado = 'GRADUADO_COMPLETO', c1 = 'SI', c2 = 'SI', maestria = 'SI' WHERE id = ?", (best_id,))
            matched_db_ids.add(best_id)
            actualizados += 1

    # 4. Normalizar Falsos Graduados (excluyendo IDs protegidos)
    c.execute("SELECT id, nombre, apellido, estado FROM participantes WHERE estado = 'GRADUADO_COMPLETO'")
    current_grads = c.fetchall()
    
    revertidos = 0
    for row in current_grads:
        gid = row[0]
        if gid not in matched_db_ids and gid not in PROTECTED_IDS:
            gfullname = f"{row[1]} {row[2]}".strip()
            print(f"  [*] Revertiendo a ACTIVO falso graduado: '{gfullname}' (ID {gid})")
            c.execute("UPDATE participantes SET estado = 'ACTIVO' WHERE id = ?", (gid,))
            revertidos += 1
            log_blackbox("REVERSION_FALSO_GRADUADO", f"Revertido {gfullname} (ID {gid}) a estado ACTIVO.")

    conn.commit()

    # 5. Validación final del conteo de graduados en la DB
    total_db_grad = c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'").fetchone()[0]
    print(f"\n=================================================================")
    print(f"NORMALIZACIÓN COMPLETADA:")
    print(f"  - Graduados en Excel:            {len(excel_graduados)}")
    print(f"  - Nuevos insertados en DB:       {insertados}")
    print(f"  - Actualizados a graduado en DB: {actualizados}")
    print(f"  - Duplicados fusionados y eliminados: {fusionados}")
    print(f"  - Falsos graduados revertidos:   {revertidos}")
    print(f"  - Total GRADUADO_COMPLETO en DB: {total_db_grad}")
    print("=================================================================")

    if total_db_grad == len(excel_graduados):
        print("  🎉 ¡ÉXITO! Conteo de graduados exacto y sincronizado al 100%.")
        log_blackbox("SINK_SUCCESS", f"Normalización exitosa. Conteo de graduados alineado a {total_db_grad} exactos.")
        success = True
    else:
        print("  ⚠️ ADVERTENCIA: El conteo en DB difiere del Excel.")
        log_blackbox("SINK_WARNING", f"Conteo difiere: DB {total_db_grad} vs Excel {len(excel_graduados)}", "WARNING")
        success = False

    conn.close()

    if os.path.exists(TEMP_PATH):
        try:
            os.remove(TEMP_PATH)
        except:
            pass
            
    return success

if __name__ == '__main__':
    run_normalization()
