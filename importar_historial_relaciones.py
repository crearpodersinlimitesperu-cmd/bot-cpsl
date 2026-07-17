"""
IMPORTADOR DE RELACIONES HISTÓRICAS (ALIADOS C1, C2 E IMO)
=========================================================
Recorre los excels de aliados en OneDrive, extrae las conexiones 
y las importa en la tabla 'relaciones' en torre_control.db.
"""
import os
import sqlite3
import pandas as pd
import glob
import re
import unicodedata
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Configurar rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'torre_control.db')

def normalize_name(text):
    if not text or pd.isna(text):
        return ""
    # Pasar a minúsculas y quitar espacios en los extremos
    text = str(text).lower().strip()
    # Eliminar acentos
    text = "".join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')
    # Reemplazar múltiples espacios por uno solo
    text = re.sub(r'\s+', ' ', text)
    return text

def resolve_name(name_str, participants_list):
    name_norm = normalize_name(name_str)
    # Ignorar celdas vacías o con guiones
    if not name_norm or len(name_norm) < 3 or name_norm in ['-', 'none', 'n/a', 'imo', 'sin asignar']:
        return None, ""
        
    words = name_norm.split()
    if not words:
        return None, ""
        
    matches = []
    for pid, p_fullname in participants_list:
        # Verificar que todas las palabras buscadas estén en el nombre del participante
        if all(w in p_fullname for w in words):
            matches.append((pid, p_fullname))
            
    if len(matches) == 1:
        return matches[0][0], matches[0][1]
    elif len(matches) > 1:
        # Si hay homónimos, intentar ver si hay coincidencia de palabras exacta (sin importar el orden)
        for pid, p_fullname in matches:
            p_words = p_fullname.split()
            if sorted(p_words) == sorted(words):
                return pid, p_fullname
        # De lo contrario, retornar la primera coincidencia
        return matches[0][0], matches[0][1]
        
    return None, name_str.strip()

def split_names(name_str):
    if not name_str:
        return []
    s = str(name_str).strip()
    s = s.replace('//', '|').replace('/', '|').replace(' AND ', '|').replace(' and ', '|')
    s = re.sub(r'\s+[ye]\s+', '|', s, flags=re.IGNORECASE)
    parts = [p.strip() for p in s.split('|') if p.strip()]
    return parts

def main():
    print("=================================================================")
    print("   INICIANDO IMPORTACIÓN DE RELACIONES HISTÓRICAS")
    print("=================================================================")

    # 1. Crear tabla relaciones en la DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS relaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            px_id INTEGER NOT NULL,
            relacionado_id INTEGER,
            nombre_relacionado TEXT,
            tipo TEXT NOT NULL,
            contexto TEXT,
            FOREIGN KEY(px_id) REFERENCES participantes(id),
            FOREIGN KEY(relacionado_id) REFERENCES participantes(id),
            UNIQUE(px_id, tipo, nombre_relacionado, relacionado_id) ON CONFLICT REPLACE
        )
    """)
    conn.commit()

    # 2. Cargar todos los participantes de la DB para mapeo en memoria
    c.execute("SELECT id, nombre, apellido FROM participantes")
    db_participants = c.fetchall()
    # Lista de tuplas (id, nombre_completo_normalizado)
    participants_list = []
    for row in db_participants:
        pid = row[0]
        full_name = f"{row[1] or ''} {row[2] or ''}"
        participants_list.append((pid, normalize_name(full_name)))

    print(f"Cargados {len(participants_list)} participantes de la base de datos para mapeo.")

    # 3. Buscar carpetas de aliados
    c1_dir = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"
    c2_dir = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2"

    inserted_count = 0

    # --- PROCESAR ALIADOS C1 ---
    print("\n--- PROCESANDO ARCHIVOS C1 ---")
    c1_files = glob.glob(os.path.join(c1_dir, "*.xlsx"))
    for file_path in c1_files:
        filename = os.path.basename(file_path)
        # Extraer el número de equipo
        eq_match = re.search(r"EQUIPO\s+(\d+)", filename, re.IGNORECASE)
        eq_name = f"EQUIPO {eq_match.group(1)}" if eq_match else "C1"
        
        print(f"Leyendo: {filename} ({eq_name})")
        try:
            xl = pd.ExcelFile(file_path)
            sheet_name = 'PX' if 'PX' in xl.sheet_names else xl.sheet_names[0]
            df = xl.parse(sheet_name)
            
            # Limpiar nombres de columnas
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            # Buscar columnas necesarias
            col_nombres = next((c for c in df.columns if 'NOMBRE' in c and 'PREFIERE' not in c), None)
            col_apellidos = next((c for c in df.columns if 'APELLIDO' in c), None)
            col_aliado = next((c for c in df.columns if 'ALIADO' in c), None)
            col_imo = next((c for c in df.columns if 'IMO' in c), None)

            if not col_nombres or not col_apellidos:
                print(f"  ⚠️ Columnas de nombre/apellido no encontradas en {filename}")
                continue

            for _, row in df.iterrows():
                nombres = str(row.get(col_nombres, '')).strip()
                apellidos = str(row.get(col_apellidos, '')).strip()
                if not nombres or nombres.lower() in ['nan', '']:
                    continue
                    
                full_px_name = f"{nombres} {apellidos}"
                
                # 1. Resolver el ID del participante
                px_id, _ = resolve_name(full_px_name, participants_list)
                if not px_id:
                    # Intentar resolver usando solo nombre o apellido parcial
                    continue
                
                # 2. Insertar relación Aliado C1
                if col_aliado:
                    aliado_raw = str(row.get(col_aliado, '')).strip()
                    if aliado_raw and aliado_raw.lower() not in ['nan', '', '-']:
                        names = split_names(aliado_raw)
                        for name in names:
                            rel_id, rel_name = resolve_name(name, participants_list)
                            c.execute("""
                                INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                                VALUES (?, ?, ?, 'ALIADO_C1', ?)
                            """, (px_id, rel_id, rel_name or name, eq_name))
                            inserted_count += 1

                # 3. Insertar relación IMO
                if col_imo:
                    imo_name = str(row.get(col_imo, '')).strip()
                    if imo_name and imo_name.lower() not in ['nan', '', '-']:
                        rel_id, rel_name = resolve_name(imo_name, participants_list)
                        c.execute("""
                            INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                            VALUES (?, ?, ?, 'IMO', ?)
                        """, (px_id, rel_id, rel_name or imo_name, eq_name))
                        inserted_count += 1
                        
            conn.commit()
        except Exception as e:
            print(f"  ❌ Error al procesar {filename}: {e}")

    # --- PROCESAR ALIADOS C2 ---
    print("\n--- PROCESANDO ARCHIVOS C2 ---")
    c2_files = glob.glob(os.path.join(c2_dir, "*.xlsx"))
    for file_path in c2_files:
        filename = os.path.basename(file_path)
        # Extraer el número de equipo
        eq_match = re.search(r"EQUIPO\s+(\d+)", filename, re.IGNORECASE)
        eq_name = f"EQUIPO {eq_match.group(1)}" if eq_match else "C2"
        
        print(f"Leyendo: {filename} ({eq_name})")
        try:
            xl = pd.ExcelFile(file_path)
            sheet_name = 'PX' if 'PX' in xl.sheet_names else xl.sheet_names[0]
            df = xl.parse(sheet_name)
            
            df.columns = [str(col).strip().upper() for col in df.columns]
            
            col_nombres = next((c for c in df.columns if 'NOMBRE' in c and 'PREFIERE' not in c), None)
            col_apellidos = next((c for c in df.columns if 'APELLIDO' in c), None)
            col_aliado = next((c for c in df.columns if 'ALIADO' in c), None)
            col_imo = next((c for c in df.columns if 'IMO' in c), None)

            if not col_nombres or not col_apellidos:
                print(f"  ⚠️ Columnas de nombre/apellido no encontradas en {filename}")
                continue

            for _, row in df.iterrows():
                nombres = str(row.get(col_nombres, '')).strip()
                apellidos = str(row.get(col_apellidos, '')).strip()
                if not nombres or nombres.lower() in ['nan', '']:
                    continue
                    
                full_px_name = f"{nombres} {apellidos}"
                
                px_id, _ = resolve_name(full_px_name, participants_list)
                if not px_id:
                    continue
                
                # Insertar relación Aliado C2
                if col_aliado:
                    aliado_raw = str(row.get(col_aliado, '')).strip()
                    if aliado_raw and aliado_raw.lower() not in ['nan', '', '-']:
                        names = split_names(aliado_raw)
                        for name in names:
                            rel_id, rel_name = resolve_name(name, participants_list)
                            c.execute("""
                                INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                                VALUES (?, ?, ?, 'ALIADO_C2', ?)
                            """, (px_id, rel_id, rel_name or name, eq_name))
                            inserted_count += 1

                # Insertar relación IMO (si no existía en C1, o para complementar)
                if col_imo:
                    imo_name = str(row.get(col_imo, '')).strip()
                    if imo_name and imo_name.lower() not in ['nan', '', '-']:
                        rel_id, rel_name = resolve_name(imo_name, participants_list)
                        c.execute("""
                            INSERT OR REPLACE INTO relaciones (px_id, relacionado_id, nombre_relacionado, tipo, contexto)
                            VALUES (?, ?, ?, 'IMO', ?)
                        """, (px_id, rel_id, rel_name or imo_name, eq_name))
                        inserted_count += 1
                        
            conn.commit()
        except Exception as e:
            print(f"  ❌ Error al procesar {filename}: {e}")

    # 4. Cerrar base de datos
    conn.close()
    print("\n=================================================================")
    print(f"✅ IMPORTACIÓN COMPLETADA: {inserted_count} relaciones importadas.")
    print("=================================================================")

if __name__ == '__main__':
    main()
