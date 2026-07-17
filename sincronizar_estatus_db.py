import os
import glob
import re
import sys
import sqlite3
from datetime import datetime
import pandas as pd

# Asegurar codificación UTF-8 en consola
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Rutas de base de datos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
LOG_DB = os.path.join(BASE_DIR, "caja_negra.db")

# Rutas de OneDrive
ONEDRIVE_BASE = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
DIR_C1 = os.path.join(ONEDRIVE_BASE, "CREAR LIMA", "PORCENTAJE ALIADOS C1")
DIR_C2 = os.path.join(ONEDRIVE_BASE, "CREAR LIMA", "PORCENTAJE ALIADOS C2")
DIR_MJ = os.path.join(ONEDRIVE_BASE, "MAESTRIA DEL JUEGO GLOBAL", "Equipos", "Lima")
GRAD_FILE = os.path.join(ONEDRIVE_BASE, "CREAR LIMA", "GRADUADOS LIMA.xlsx")

def registrar_log(categoria, evento, detalle, estado="OK"):
    try:
        conn = sqlite3.connect(LOG_DB, timeout=60.0)
        c = conn.cursor()
        c.execute("""
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al registrar log en caja_negra: {e}")

def norm(name):
    if pd.isna(name):
        return ""
    n = str(name).upper().strip()
    for a, b in [("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U")]:
        n = n.replace(a, b)
    return re.sub(r'\s+', ' ', n)

def split_fullname(fullname):
    parts = str(fullname).strip().split()
    if len(parts) == 0:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    if len(parts) == 2:
        return parts[0], parts[1]
    return parts[0], " ".join(parts[1:])

def clean_phone(p):
    if pd.isna(p) or not p:
        return ""
    p_clean = re.sub(r'\D', '', str(p))
    if p_clean.endswith('.0'):
        p_clean = p_clean[:-2]
    return p_clean

def find_column(df, keywords):
    for col in df.columns:
        col_str = str(col).lower().strip()
        if all(k in col_str for k in keywords):
            return col
    return None

def build_db_lookups(cursor):
    cursor.execute("SELECT id, nombre, apellido, telefono, identificacion, c1, c2, maestria, estado, equipo FROM participantes")
    rows = cursor.fetchall()
    by_name = {}
    by_phone = {}
    by_dni = {}
    
    for r in rows:
        full_name_norm = norm(f"{r[1]} {r[2]}")
        if full_name_norm:
            by_name[full_name_norm] = r
            
        phone_clean = clean_phone(r[3])
        if phone_clean and len(phone_clean) >= 9:
            by_phone[phone_clean[-9:]] = r
            
        if r[4] and str(r[4]).strip():
            by_dni[str(r[4]).strip()] = r
            
    return by_name, by_phone, by_dni

def buscar_participante(nombre_completo, telefono, dni, lookups):
    by_name, by_phone, by_dni = lookups
    
    dni_str = str(dni).strip() if dni else ""
    if dni_str and dni_str in by_dni:
        return by_dni[dni_str]
        
    tel_clean = clean_phone(telefono)
    if tel_clean and len(tel_clean) >= 9:
        last9 = tel_clean[-9:]
        if last9 in by_phone:
            return by_phone[last9]
            
    name_norm = norm(nombre_completo)
    if name_norm and name_norm in by_name:
        return by_name[name_norm]
        
    return None

def procesar_cambios_de_cupo(conn):
    print(">>> 1. PROCESANDO CAMBIOS DE CUPO (TRASPASOS)...")
    cursor = conn.cursor()
    
    files = []
    # Buscar solo en subcarpetas de CREAR LIMA y Archivos de Crearpsl para evitar escanear todo OneDrive
    for subfolder in ["CREAR LIMA", "Archivos de Crearpsl - Pamela Carrillo - CREAR LIMA"]:
        target_dir = os.path.join(ONEDRIVE_BASE, subfolder)
        if os.path.exists(target_dir):
            files.extend(glob.glob(os.path.join(target_dir, "**", "*Cambio de Cupo*.xlsx"), recursive=True))
    files = [f for f in files if not os.path.basename(f).startswith("~$")]
    
    print(f"  Archivos de Cambio de Cupo encontrados: {len(files)}")
    transfers_count = 0
    inserts_count = 0
    
    for filepath in files:
        fname = os.path.basename(filepath)
        eq_match = re.search(r'Equipo\s+(\d+)', fname, re.IGNORECASE)
        equipo_archivo = eq_match.group(1) if eq_match else "N/A"
        
        try:
            df = pd.read_excel(filepath)
            
            col_imo_name = find_column(df, ['aliado', 'nombre'])
            col_imo_dni = find_column(df, ['dni'])
            col_imo_tel = find_column(df, ['contacto', 'tel'])
            col_sale_name = find_column(df, ['sale', 'nombre'])
            col_sale_dni = find_column(df, ['sale', 'dni'])
            if not col_sale_dni:
                col_sale_dni = find_column(df, ['sale', 'documento'])
                
            col_nuevo_name = find_column(df, ['nuevo', 'nombre'])
            col_nuevo_pref = find_column(df, ['prefiere'])
            col_nuevo_dni = find_column(df, ['nuevo', 'dni'])
            if not col_nuevo_dni:
                col_nuevo_dni = find_column(df, ['nuevo', 'documento'])
                
            col_nuevo_tel = find_column(df, ['móvil'])
            if not col_nuevo_tel:
                col_nuevo_tel = find_column(df, ['movil'])
            if not col_nuevo_tel:
                col_nuevo_tel = find_column(df, ['teléfono', 'nuevo'])
                
            col_nuevo_email = find_column(df, ['correo', 'principal'])
            
            if not all([col_sale_name, col_nuevo_name, col_nuevo_dni]):
                continue
                
            for idx, row in df.iterrows():
                sale_name = str(row.get(col_sale_name, '')).strip()
                sale_dni = str(row.get(col_sale_dni, '')).split('.')[0].strip() if pd.notna(row.get(col_sale_dni)) else ""
                
                nuevo_name = str(row.get(col_nuevo_name, '')).strip()
                nuevo_dni = str(row.get(col_nuevo_dni, '')).split('.')[0].strip() if pd.notna(row.get(col_nuevo_dni)) else ""
                nuevo_tel = clean_phone(row.get(col_nuevo_tel, ''))
                nuevo_email = str(row.get(col_nuevo_email, '')).strip() if pd.notna(row.get(col_nuevo_email)) else ""
                nuevo_pref = str(row.get(col_nuevo_pref, '')).strip() if pd.notna(row.get(col_nuevo_pref)) else ""
                
                imo_name = str(row.get(col_imo_name, '')) if col_imo_name else ""
                imo_dni = str(row.get(col_imo_dni, '')) if col_imo_dni else ""
                imo_tel = clean_phone(row.get(col_imo_tel, '')) if col_imo_tel else ""
                
                if not sale_name or not nuevo_name or not nuevo_dni:
                    continue
                
                px_saliente = None
                if sale_dni:
                    cursor.execute("SELECT id FROM participantes WHERE identificacion = ?", (sale_dni,))
                    px_saliente = cursor.fetchone()
                if not px_saliente:
                    sale_nom_split = split_fullname(sale_name)
                    cursor.execute("SELECT id FROM participantes WHERE nombre LIKE ? AND apellido LIKE ?", (f"%{sale_nom_split[0]}%", f"%{sale_nom_split[1]}%"))
                    px_saliente = cursor.fetchone()
                    
                if px_saliente:
                    cursor.execute("""
                        UPDATE participantes
                        SET estado = 'TRANSFERIDO', nuevo_titular_dni = ?, tiene_cambio_cupo = 'SI', fecha_actualizacion = ?
                        WHERE id = ? AND estado != 'TRANSFERIDO'
                    """, (nuevo_dni, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px_saliente[0]))
                    if cursor.rowcount > 0:
                        transfers_count += 1
                
                cursor.execute("SELECT id FROM participantes WHERE identificacion = ?", (nuevo_dni,))
                px_nuevo = cursor.fetchone()
                nom_nuevo_split = split_fullname(nuevo_name)
                
                if px_nuevo:
                    cursor.execute("""
                        UPDATE participantes
                        SET telefono = COALESCE(NULLIF(telefono, ''), ?),
                            email = COALESCE(NULLIF(email, ''), ?),
                            nombre_preferido = COALESCE(NULLIF(nombre_preferido, ''), ?),
                            equipo = ?,
                            imo = ?,
                            tel_imo = ?,
                            estado = 'ACTIVO',
                            fecha_actualizacion = ?
                        WHERE id = ?
                    """, (nuevo_tel, nuevo_email, nuevo_pref, equipo_archivo, imo_name, imo_tel, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px_nuevo[0]))
                else:
                    cursor.execute("""
                        INSERT INTO participantes (
                            nombre, apellido, nombre_preferido, telefono, email, equipo, imo, tel_imo,
                            c1, c2, maestria, tipo, identificacion, estado, tiene_cambio_cupo, fecha_registro, fecha_actualizacion
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'NO', 'NO', 'NO', 'PX', ?, 'ACTIVO', 'NO', ?, ?)
                    """, (nom_nuevo_split[0], nom_nuevo_split[1], nuevo_pref, nuevo_tel, nuevo_email, equipo_archivo, imo_name, imo_tel, nuevo_dni, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    inserts_count += 1
                    
        except Exception as e:
            print(f"  ❌ Error procesando {fname}: {e}")
            registrar_log("SYNC_CAMBIO_CUPO_ERR", f"Error en archivo {fname}", str(e), "FAILED")
            
    conn.commit()
    res_msg = f"Cambios de Cupo completados. Transferencias: {transfers_count}, Nuevos registrados: {inserts_count}"
    print(f"  ✅ {res_msg}")
    registrar_log("SYNC_CAMBIO_CUPO_OK", "Procesamiento de Cambios de Cupo finalizado", res_msg, "SUCCESS")

def sincronizar_carpetas_aliados(conn):
    print("\n>>> 2. SINCRONIZANDO ESTATUS C1 Y C2 DESDE CARPETAS DE ALIADOS...")
    cursor = conn.cursor()
    
    lookups = build_db_lookups(cursor)
    
    files_c1 = glob.glob(os.path.join(DIR_C1, "*.xlsx"))
    files_c2 = glob.glob(os.path.join(DIR_C2, "*.xlsx"))
    
    files_c1 = [f for f in files_c1 if not os.path.basename(f).startswith("~$")]
    files_c2 = [f for f in files_c2 if not os.path.basename(f).startswith("~$")]
    
    print(f"  Archivos C1: {len(files_c1)} | Archivos C2: {len(files_c2)}")
    
    updates_count = 0
    inserts_count = 0
    
    # 2.1 Procesar C1
    for filepath in files_c1:
        fname = os.path.basename(filepath)
        eq_match = re.search(r'EQUIPO\s+(\d+)', fname, re.IGNORECASE)
        equipo = eq_match.group(1) if eq_match else "N/A"
        
        try:
            xls = pd.ExcelFile(filepath)
            if 'PX' not in xls.sheet_names:
                continue
                
            df = pd.read_excel(filepath, sheet_name='PX')
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            col_nombre = find_column(df, ['nombre'])
            col_apellido = find_column(df, ['apellido'])
            col_tel = find_column(df, ['tel'])
            col_imo = find_column(df, ['imo'])
            col_status = find_column(df, ['status'])
            if not col_status:
                col_status = find_column(df, ['estado'])
                
            if not col_nombre:
                continue
                
            for idx, row in df.iterrows():
                n = str(row.get(col_nombre, '')).strip()
                a = str(row.get(col_apellido, '')).strip() if col_apellido else ""
                full_name = f"{n} {a}".strip()
                
                if not n or len(full_name) < 4:
                    continue
                    
                tel = clean_phone(row.get(col_tel, '')) if col_tel else ""
                imo = str(row.get(col_imo, '')) if col_imo else ""
                status_val = str(row.get(col_status, '')).strip().upper() if col_status else ""
                
                c1_status = 'SI'
                db_state = 'ACTIVO'
                
                if any(x in status_val for x in ["DESERTOR", "DEVOLUCION", "RETIRADO", "NO"]):
                    c1_status = 'NO'
                    db_state = status_val
                
                px = buscar_participante(full_name, tel, "", lookups)
                
                if px:
                    cursor.execute("""
                        UPDATE participantes
                        SET telefono = COALESCE(NULLIF(telefono, ''), ?),
                            imo = COALESCE(NULLIF(imo, ''), ?),
                            c1 = ?,
                            estado = ?,
                            fecha_actualizacion = ?
                        WHERE id = ?
                    """, (tel, imo, c1_status, db_state, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
                    updates_count += 1
                else:
                    nom_split = split_fullname(full_name)
                    cursor.execute("""
                        INSERT INTO participantes (
                            nombre, apellido, telefono, imo, c1, c2, maestria, tipo, estado, equipo, fecha_registro, fecha_actualizacion
                        ) VALUES (?, ?, ?, ?, ?, 'NO', 'NO', 'PX', ?, ?, ?, ?)
                    """, (nom_split[0], nom_split[1], tel, imo, c1_status, db_state, equipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                    inserts_count += 1
                    lookups = build_db_lookups(cursor)
                    
        except Exception as e:
            print(f"    ❌ Error en C1 {fname}: {e}")
            
    # 2.2 Procesar C2
    for filepath in files_c2:
        fname = os.path.basename(filepath)
        eq_match = re.search(r'EQUIPO\s+(\d+)', fname, re.IGNORECASE)
        equipo = eq_match.group(1) if eq_match else "N/A"
        
        try:
            xls = pd.ExcelFile(filepath)
            
            if 'PX' in xls.sheet_names:
                df = pd.read_excel(filepath, sheet_name='PX')
                df.columns = [str(c).strip().upper() for c in df.columns]
                
                col_nombre = find_column(df, ['nombre'])
                col_apellido = find_column(df, ['apellido'])
                col_tel = find_column(df, ['tel'])
                col_imo = find_column(df, ['imo'])
                col_status = find_column(df, ['status'])
                if not col_status:
                    col_status = find_column(df, ['estado'])
                    
                if col_nombre:
                    for idx, row in df.iterrows():
                        n = str(row.get(col_nombre, '')).strip()
                        a = str(row.get(col_apellido, '')).strip() if col_apellido else ""
                        full_name = f"{n} {a}".strip()
                        
                        if not n or len(full_name) < 4:
                            continue
                            
                        tel = clean_phone(row.get(col_tel, '')) if col_tel else ""
                        imo = str(row.get(col_imo, '')) if col_imo else ""
                        status_val = str(row.get(col_status, '')).strip().upper() if col_status else ""
                        
                        c1_status = 'SI'
                        c2_status = 'SI'
                        maestria_status = 'NO'
                        db_state = 'ACTIVO'
                        
                        if any(x in status_val for x in ["DESERTOR", "DEVOLUCION", "RETIRADO"]):
                            c2_status = 'NO'
                            db_state = status_val
                        elif any(x in status_val for x in ["MJ", "C2+MJ", "ABONO"]):
                            maestria_status = 'SI'
                            
                        px = buscar_participante(full_name, tel, "", lookups)
                        
                        if px:
                            cursor.execute("""
                                UPDATE participantes
                                SET telefono = COALESCE(NULLIF(telefono, ''), ?),
                                    imo = COALESCE(NULLIF(imo, ''), ?),
                                    c1 = ?,
                                    c2 = ?,
                                    maestria = CASE WHEN ? = 'SI' THEN 'SI' ELSE maestria END,
                                    estado = ?,
                                    fecha_actualizacion = ?
                                WHERE id = ?
                            """, (tel, imo, c1_status, c2_status, maestria_status, db_state, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
                            updates_count += 1
                        else:
                            nom_split = split_fullname(full_name)
                            cursor.execute("""
                                INSERT INTO participantes (
                                    nombre, apellido, telefono, imo, c1, c2, maestria, tipo, estado, equipo, fecha_registro, fecha_actualizacion
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'PX', ?, ?, ?, ?)
                            """, (nom_split[0], nom_split[1], tel, imo, c1_status, c2_status, maestria_status, db_state, equipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            inserts_count += 1
                            lookups = build_db_lookups(cursor)
                            
            if 'SALTO CUANTICO' in xls.sheet_names:
                df_mj = pd.read_excel(filepath, sheet_name='SALTO CUANTICO')
                df_mj.columns = [str(c).strip().upper() for c in df_mj.columns]
                
                col_nombre = find_column(df_mj, ['nombre'])
                col_apellido = find_column(df_mj, ['apellido'])
                
                if col_nombre:
                    for idx, row in df_mj.iterrows():
                        n = str(row.get(col_nombre, '')).strip()
                        a = str(row.get(col_apellido, '')).strip() if col_apellido else ""
                        full_name = f"{n} {a}".strip()
                        
                        if not n or len(full_name) < 4:
                            continue
                            
                        px = buscar_participante(full_name, "", "", lookups)
                        if px:
                            cursor.execute("""
                                UPDATE participantes
                                SET c1 = 'SI', c2 = 'SI', maestria = 'SI', fecha_actualizacion = ?
                                WHERE id = ?
                            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
                            updates_count += 1
                        else:
                            nom_split = split_fullname(full_name)
                            cursor.execute("""
                                INSERT INTO participantes (
                                    nombre, apellido, c1, c2, maestria, tipo, estado, equipo, fecha_registro, fecha_actualizacion
                                ) VALUES (?, ?, 'SI', 'SI', 'SI', 'PX', 'ACTIVO', ?, ?, ?)
                            """, (nom_split[0], nom_split[1], equipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                            inserts_count += 1
                            lookups = build_db_lookups(cursor)
                            
        except Exception as e:
            print(f"    ❌ Error en C2 {fname}: {e}")
            
    conn.commit()
    res_msg = f"Sincronizacion de aliados completada. Actualizados: {updates_count}, Creados: {inserts_count}"
    print(f"  ✅ {res_msg}")
    registrar_log("SYNC_ALIADOS_OK", "Sincronizacion de carpetas de aliados finalizada", res_msg, "SUCCESS")

def sincronizar_maestria(conn):
    print("\n>>> 3. SINCRONIZANDO ESTATUS DE MAESTRÍA (MJ) DESDE ONEDRIVE...")
    cursor = conn.cursor()
    
    if not os.path.exists(DIR_MJ):
        print(f"  ❌ Directorio de Maestría no existe: {DIR_MJ}")
        return
        
    lookups = build_db_lookups(cursor)
    
    des_file = os.path.join(DIR_MJ, "DESERTORES Y REZAGADOS LIMA.xlsx")
    desertores_names = set()
    rezagados_names = set()
    
    if os.path.exists(des_file):
        try:
            xls_des = pd.ExcelFile(des_file)
            if 'DESERTORES' in xls_des.sheet_names:
                df_des = pd.read_excel(des_file, sheet_name='DESERTORES')
                col_name = None
                for col in df_des.columns:
                    col_str = str(col).lower().strip()
                    if 'nombre' in col_str or 'participante' in col_str:
                        col_name = col
                        break
                if col_name:
                    for idx, row in df_des.iterrows():
                        name = str(row.get(col_name, '')).strip()
                        if name and len(name) > 4:
                            desertores_names.add(norm(name))
                            
            if 'REZAGADOS' in xls_des.sheet_names:
                df_rez = pd.read_excel(des_file, sheet_name='REZAGADOS')
                col_name = None
                for col in df_rez.columns:
                    col_str = str(col).lower().strip()
                    if 'nombre' in col_str or 'participante' in col_str:
                        col_name = col
                        break
                if col_name:
                    for idx, row in df_rez.iterrows():
                        name = str(row.get(col_name, '')).strip()
                        if name and len(name) > 4:
                            rezagados_names.add(norm(name))
        except Exception as e_des:
            print(f"    ❌ Error al leer desertores MJ: {e_des}")
            
    print(f"  Bajas MJ detectadas: Desertores={len(desertores_names)} | Rezagados={len(rezagados_names)}")
    
    des_updates = 0
    for d_name in desertores_names:
        px = buscar_participante(d_name, "", "", lookups)
        if px:
            cursor.execute("""
                UPDATE participantes
                SET c1 = 'SI', c2 = 'SI', maestria = 'NO', estado = 'DESERTOR_MJ', fecha_actualizacion = ?
                WHERE id = ? AND estado != 'DESERTOR_MJ'
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
            if cursor.rowcount > 0:
                des_updates += 1
            
    for r_name in rezagados_names:
        px = buscar_participante(r_name, "", "", lookups)
        if px:
            cursor.execute("""
                UPDATE participantes
                SET c1 = 'SI', c2 = 'SI', maestria = 'NO', estado = 'REZAGADO_MJ', fecha_actualizacion = ?
                WHERE id = ? AND estado != 'REZAGADO_MJ'
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
            if cursor.rowcount > 0:
                des_updates += 1
                
    conn.commit()
    lookups = build_db_lookups(cursor)
    
    files = glob.glob(os.path.join(DIR_MJ, "**", "*.xlsx"), recursive=True)
    files = [f for f in files if "DESERTORES Y REZAGADOS" not in os.path.basename(f) and not os.path.basename(f).startswith("~$")]
    
    print(f"  Archivos de Maestría a procesar: {len(files)}")
    
    mj_updates = 0
    mj_inserts = 0
    
    for filepath in files:
        fname = os.path.basename(filepath)
        eq_match = re.search(r'EQUIPO\s+(\d+)', fname, re.IGNORECASE)
        if not eq_match:
            eq_match = re.search(r'E(\d+)', fname, re.IGNORECASE)
        equipo = eq_match.group(1) if eq_match else "N/A"
        
        try:
            xls = pd.ExcelFile(filepath)
            for sheet in xls.sheet_names:
                df = pd.read_excel(filepath, sheet_name=sheet)
                
                col_name = None
                for col in df.columns:
                    col_str = str(col).lower().strip()
                    if 'nombre' in col_str or 'participante' in col_str or 'enrolamiento' in col_str:
                        if 'imo' not in col_str and 'manager' not in col_str:
                            col_name = col
                            break
                if not col_name:
                    for col in df.columns:
                        if 'nombre' in str(col).lower():
                            col_name = col
                            break
                            
                if not col_name:
                    continue
                    
                for idx, row in df.iterrows():
                    val = row.get(col_name)
                    if pd.isna(val):
                        continue
                        
                    name_clean = str(val).strip()
                    name_upper = name_clean.upper()
                    
                    if any(x in name_upper for x in ['SENTADOS', 'CONFIRMADOS', 'DECLARACION', 'TOTAL', 'SUMA', 'SEMAFORO', 'LLAMADA', 'REPORTE', 'EQUIPO', 'ROL', 'ROLL']):
                        continue
                    if name_clean.startswith('Unnamed:') or len(name_clean) < 5:
                        continue
                        
                    name_norm = norm(name_clean)
                    
                    if name_norm in desertores_names or name_norm in rezagados_names:
                        continue
                        
                    px = buscar_participante(name_clean, "", "", lookups)
                    
                    if px:
                        cursor.execute("""
                            UPDATE participantes
                            SET c1 = 'SI', c2 = 'SI', maestria = 'SI', estado = 'ACTIVO', fecha_actualizacion = ?
                            WHERE id = ? AND (c1 != 'SI' OR c2 != 'SI' OR maestria != 'SI' OR estado != 'ACTIVO')
                        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), px[0]))
                        if cursor.rowcount > 0:
                            mj_updates += 1
                    else:
                        nom_split = split_fullname(name_clean)
                        cursor.execute("""
                            INSERT INTO participantes (
                                nombre, apellido, c1, c2, maestria, tipo, estado, equipo, fecha_registro, fecha_actualizacion
                            ) VALUES (?, ?, 'SI', 'SI', 'SI', 'PX', 'ACTIVO', ?, ?, ?)
                        """, (nom_split[0], nom_split[1], equipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                        mj_inserts += 1
                        lookups = build_db_lookups(cursor)
                        
        except Exception as e_file:
            print(f"    ❌ Error procesando archivo MJ {fname}: {e_file}")
            
    conn.commit()
    res_msg = f"Sincronizacion de Maestria finalizada. Actualizados/Activos: {mj_updates}, Registrados: {mj_inserts}, Bajas aplicadas: {des_updates}"
    print(f"  ✅ {res_msg}")
    registrar_log("SYNC_MAESTRIA_OK", "Sincronizacion de Maestria (MJ) finalizada", res_msg, "SUCCESS")

def sincronizar_graduados(conn):
    print("\n>>> 4. SINCRONIZANDO GRADUADOS DESDE GRADUADOS LIMA.XLSX...")
    cursor = conn.cursor()
    
    if not os.path.exists(GRAD_FILE):
        print(f"  ❌ Archivo de Graduados no existe: {GRAD_FILE}")
        return
        
    lookups = build_db_lookups(cursor)
    
    try:
        df = pd.read_excel(GRAD_FILE, sheet_name='GRADUADOS ')
        df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        
        excel_names = []
        for col in df.columns:
            vals = df[col].dropna().astype(str).str.strip().str.upper()
            for v in vals:
                # Filtrar nombres válidos y no cabeceras
                if len(v) > 5 and ' ' in v and not any(x in v for x in ['FECHA', 'EQUIPO', 'TOTAL', 'CREAR', 'CUANTICO', 'ORIGINAL']):
                    excel_names.append(v)
                    
        # Cargar todos los participantes de la BD
        cursor.execute("SELECT id, nombre, apellido, c1, c2, maestria, estado FROM participantes")
        db_px = cursor.fetchall()
        
        matched_ids = set()
        
        for ex_name in excel_names:
            ex_name_norm = norm(ex_name)
            if not ex_name_norm or len(ex_name_norm) < 5:
                continue
                
            for px in db_px:
                # px: (id, nombre, apellido, c1, c2, maestria, estado)
                db_name_norm = norm(f"{px[1]} {px[2]}")
                if ex_name_norm in db_name_norm or db_name_norm in ex_name_norm:
                    matched_ids.add(px[0])
                    
        if matched_ids:
            cursor.execute(f"""
                UPDATE participantes 
                SET c1 = 'SI', c2 = 'SI', maestria = 'SI', estado = 'ACTIVO', fecha_actualizacion = ?
                WHERE id IN ({','.join(map(str, matched_ids))})
            """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'),))
            conn.commit()
            
        res_msg = f"Sincronizacion de Graduados completada. Registros cruzados y marcados en BD: {len(matched_ids)}."
        print(f"  ✅ {res_msg}")
        registrar_log("SYNC_GRADUADOS_OK", "Sincronizacion de Graduados finalizada", res_msg, "SUCCESS")
        
    except Exception as e:
        print(f"  ❌ Error procesando archivo de Graduados: {e}")
        registrar_log("SYNC_GRADUADOS_ERR", "Error al procesar graduados", str(e), "FAILED")

def main():
    print("="*60)
    print(f"  CREAR GLOBAL - SINCRONIZADOR DE ESTATUS MAESTRO (12H)")
    print(f"  Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    start_time = datetime.now()
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=60.0)
        
        # 1. Procesar Cambios de Cupo
        procesar_cambios_de_cupo(conn)
        
        # 2. Sincronizar Carpetas C1/C2 de Aliados
        sincronizar_carpetas_aliados(conn)
        
        # 3. Sincronizar Maestría (MJ)
        sincronizar_maestria(conn)
        
        # 4. Sincronizar Graduados
        sincronizar_graduados(conn)
        
        conn.close()
        
        # 5. Lanzar la auditoría de discrepancias
        print("\n>>> 5. INICIANDO AUDITORÍA DE DISCREPANCIAS Y EXCLUSIONES...")
        try:
            sys.path.append(BASE_DIR)
            from validar_status_onedrive import ejecutar_auditoria
            ejecutor_auditoria = ejecutar_auditoria # Para compatibilidad de nombres
            ejecutar_auditoria()
            print("  ✅ Auditoría ejecutada correctamente.")
        except Exception as e_aud:
            print(f"  ❌ Error ejecutando auditoría de discrepancias: {e_aud}")
            registrar_log("AUDITORIA_ERR", "Error al llamar a validar_status_onedrive", str(e_aud), "FAILED")
            
        duracion = datetime.now() - start_time
        print(f"\n🎉 ¡PROCESO DE SINCRONIZACIÓN EXITOSO! Duración: {duracion}")
        registrar_log("SYNC_MASTER_OK", "Proceso de sincronizacion maestro completado", f"Completado con exito en {duracion}", "FINISHED")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO en el Sincronizador Maestro: {e}")
        registrar_log("SYNC_MASTER_CRIT_ERR", "Fallo critico en sincronizador maestro", str(e), "CRITICAL")

if __name__ == "__main__":
    main()
