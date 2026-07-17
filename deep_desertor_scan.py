import os
import glob
import re
import pandas as pd
import sqlite3
import unicodedata

# Rutas
ONEDRIVE_BASE = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
DIR_C1 = os.path.join(ONEDRIVE_BASE, "CREAR LIMA", "PORCENTAJE ALIADOS C1")
DIR_C2 = os.path.join(ONEDRIVE_BASE, "CREAR LIMA", "PORCENTAJE ALIADOS C2")
DB_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"

def clean_string(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

def normalize_text(text):
    if not text:
        return ""
    text = str(text).upper().strip()
    # Remove accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
    return re.sub(r'\s+', ' ', text)

def find_name_in_row(row, df_columns):
    # Try to find columns that look like name or last name
    col_nombre = None
    col_apellido = None
    col_completo = None
    
    for col in df_columns:
        c_norm = normalize_text(col)
        if "COMPLETO" in c_norm or "NOMBRESYAPELLIDOS" in c_norm or "NOMBRES Y APELLIDOS" in c_norm:
            col_completo = col
            break
        elif "NOMBRE" in c_norm or "PARTICANTE" in c_norm or "ALUMNO" in c_norm or "PX" in c_norm:
            if "REPRESENTANTE" not in c_norm and "IMO" not in c_norm and "CC" not in c_norm:
                col_nombre = col
        elif "APELLIDO" in c_norm:
            col_apellido = col

    if col_completo:
        return clean_string(row[col_completo]), ""
    
    n = clean_string(row[col_nombre]) if col_nombre else ""
    a = clean_string(row[col_apellido]) if col_apellido else ""
    
    # If we couldn't find named columns, check if there's any string that looks like a full name
    if not n and not a:
        string_cells = [clean_string(x) for x in row.values if pd.notnull(x) and isinstance(x, str) and len(clean_string(x)) > 3]
        # Filter out common keywords
        string_cells = [x for x in string_cells if not any(kw in normalize_text(x) for kw in ["DESERTOR", "DEVOLUCION", "RETIRADO", "EQUIPO", "IMO", "SI", "NO", "PAGO", "BANCO", "EFECTIVO", "VISA"])]
        if string_cells:
            # Assume first long string is the name
            n = string_cells[0]
            if len(string_cells) > 1:
                a = " ".join(string_cells[1:])
                
    return n, a

def scan_file_for_desertores(filepath, capitulo):
    fname = os.path.basename(filepath)
    results = []
    
    # Extract team number from filename
    eq_match = re.search(r'(?:EQUIPO|E)\s*(\d+)', fname, re.IGNORECASE)
    equipo = eq_match.group(1) if eq_match else "N/A"
    
    try:
        xls = pd.ExcelFile(filepath)
        for sheet in xls.sheet_names:
            sheet_upper = normalize_text(sheet)
            
            # Read worksheet
            df = pd.read_excel(filepath, sheet_name=sheet)
            if df.empty:
                continue
                
            # Check if sheet itself is a desertion list
            sheet_is_baja_list = any(kw in sheet_upper for kw in ["DESERTOR", "DEVOLUCION", "RETIRADO", "BAJA", "REZAGADO", "NO SIGUE"])
            
            # Normalize headers
            df_columns = list(df.columns)
            
            # Scan each row
            for idx, row in df.iterrows():
                row_text_upper = " | ".join([normalize_text(x) for x in row.values if pd.notna(x)])
                
                # Check for dropout keywords
                is_desertor = False
                matched_keyword = ""
                
                # Keywords to look for in cell values
                keywords = ["DESERTOR", "DESERTORA", "DEVOLUCION", "RETIRADO", "RETIRADA", "BAJA", "NO SIGUE", "NO CONTINUA", "ABANDONO", "RETIRAR", "DESERTO"]
                for kw in keywords:
                    if kw in row_text_upper:
                        is_desertor = True
                        matched_keyword = kw
                        break
                
                # If the sheet itself is a dropout sheet, every row is a dropout row (if it contains a name)
                if sheet_is_baja_list:
                    is_desertor = True
                    matched_keyword = f"Sheet: {sheet}"
                    
                if is_desertor:
                    # Try to extract participant details
                    n, a = find_name_in_row(row, df_columns)
                    full_name = f"{n} {a}".strip()
                    
                    if len(full_name) > 4:
                        # Find specific status column value if possible
                        status_val = ""
                        for col in df_columns:
                            c_norm = normalize_text(col)
                            if any(x in c_norm for x in ["STATUS", "ESTADO", "RESULTADO", "OBSERVACION", "ASISTENCIA", "DETALLE"]):
                                status_val = clean_string(row[col])
                                break
                        
                        if not status_val:
                            # Fallback to the matched keyword or row contents
                            status_val = matched_keyword
                            
                        # Also look for phone or DNI
                        phone = ""
                        dni = ""
                        for col in df_columns:
                            c_norm = normalize_text(col)
                            if "TEL" in c_norm or "CEL" in c_norm or "MOVIL" in c_norm or "CONTACTO" in c_norm:
                                phone = clean_string(row[col])
                            elif "DNI" in c_norm or "CE" in c_norm or "DOCUMENTO" in c_norm or "IDENTI" in c_norm:
                                dni = clean_string(row[col])
                                
                        results.append({
                            "Archivo": fname,
                            "Capitulo": capitulo,
                            "Equipo": equipo,
                            "Pestaña": sheet,
                            "RowIndex": idx + 2, # 1-based + 1 for Excel header
                            "Nombre_Completo": full_name,
                            "Nombre": n,
                            "Apellido": a,
                            "DNI": dni,
                            "Telefono": phone,
                            "Status_Encontrado": status_val,
                            "Match_Type": "Cell Match" if not sheet_is_baja_list else "Sheet Name Match",
                            "Fila_Completa": row_text_upper[:300] # truncate for size
                        })
    except Exception as e:
        print(f"Error scanning {fname}: {e}")
        
    return results

def main():
    print("=== DEEP DESERTOR SEARCH IN ONEDRIVE ALIADOS ===")
    
    files_c1 = glob.glob(os.path.join(DIR_C1, "*.xlsx"))
    files_c2 = glob.glob(os.path.join(DIR_C2, "*.xlsx"))
    
    files_c1 = [f for f in files_c1 if not os.path.basename(f).startswith("~$")]
    files_c2 = [f for f in files_c2 if not os.path.basename(f).startswith("~$")]
    
    print(f"Scanning C1 files: {len(files_c1)}")
    print(f"Scanning C2 files: {len(files_c2)}")
    
    all_results = []
    
    for f in files_c1:
        res = scan_file_for_desertores(f, "C1")
        all_results.extend(res)
        
    for f in files_c2:
        res = scan_file_for_desertores(f, "C2")
        all_results.extend(res)
        
    df_results = pd.DataFrame(all_results)
    print(f"\nTotal matches found: {len(df_results)}")
    
    # Save the results to a CSV
    output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\deep_scan_desertores.csv"
    df_results.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Results saved to: {output_path}")
    
    # Let's group by unique names and keep the most descriptive status
    # Normalize names for grouping
    df_results['Norm_Name'] = df_results['Nombre_Completo'].apply(normalize_text)
    
    # Drop rows where Norm_Name is empty or too short
    df_results = df_results[df_results['Norm_Name'].str.len() > 4]
    
    unique_desertores = {}
    for idx, row in df_results.iterrows():
        name = row['Norm_Name']
        # If we already have this name, see if the current one has a better status or is C2 (more recent)
        if name in unique_desertores:
            prev = unique_desertores[name]
            # Prefer C2 over C1, or prefer explicit statuses
            if row['Capitulo'] == 'C2' and prev['Capitulo'] == 'C1':
                unique_desertores[name] = row.to_dict()
            elif any(x in str(row['Status_Encontrado']).upper() for x in ["DESERTOR", "DEVOLUCION"]):
                unique_desertores[name] = row.to_dict()
        else:
            unique_desertores[name] = row.to_dict()
            
    df_unique = pd.DataFrame(list(unique_desertores.values()))
    unique_output_path = r"C:\Users\josem\Downloads\bot-cpsl-review\deep_scan_desertores_unicos.csv"
    df_unique.to_csv(unique_output_path, index=False, encoding='utf-8-sig')
    print(f"Unique desertores saved to: {unique_output_path} (Count: {len(df_unique)})")
    
    # Check against database
    print("\nCross-referencing with database 'torre_control.db'...")
    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            db_df = pd.read_sql_query("SELECT id, nombre, apellido, c1, c2, maestria, estado, equipo FROM participantes", conn)
            db_df['Norm_Name'] = (db_df['nombre'] + " " + db_df['apellido']).apply(normalize_text)
            
            discrepancies = []
            for idx, row in df_unique.iterrows():
                db_matches = db_df[db_df['Norm_Name'] == row['Norm_Name']]
                if not db_matches.empty:
                    db_px = db_matches.iloc[0]
                    # Check if DB status is ACTIVO or not marked as desertor
                    db_status = str(db_px['estado']).upper()
                    c1_db = str(db_px['c1']).upper()
                    c2_db = str(db_px['c2']).upper()
                    
                    is_db_active = db_status in ["ACTIVO", "N/A", "", "NONE", "ACTIVA"]
                    
                    if is_db_active:
                        discrepancies.append({
                            "ID_DB": db_px['id'],
                            "Nombre_Completo": row['Nombre_Completo'],
                            "DNI_OD": row['DNI'],
                            "Telefono_OD": row['Telefono'],
                            "Equipo_OD": row['Equipo'],
                            "Capitulo_OD": row['Capitulo'],
                            "Archivo_OD": row['Archivo'],
                            "Pestaña_OD": row['Pestaña'],
                            "Status_OD": row['Status_Encontrado'],
                            "Estado_DB": db_px['estado'],
                            "C1_DB": db_px['c1'],
                            "C2_DB": db_px['c2'],
                            "Maestria_DB": db_px['maestria']
                        })
            
            conn.close()
            df_disc = pd.DataFrame(discrepancies)
            disc_path = r"C:\Users\josem\Downloads\bot-cpsl-review\deep_scan_discrepancias.csv"
            df_disc.to_csv(disc_path, index=False, encoding='utf-8-sig')
            print(f"Discrepancies saved to: {disc_path} (Count: {len(df_disc)})")
            
            # Print sample discrepancies
            if len(df_disc) > 0:
                print("\nSample discrepancies found (Active in DB but Desertor in OneDrive):")
                print(df_disc[['Nombre_Completo', 'Capitulo_OD', 'Status_OD', 'Estado_DB']].head(10))
            else:
                print("No discrepancies found between unique desertores and database!")
        except Exception as e:
            print(f"Error cross-referencing with DB: {e}")
            
if __name__ == "__main__":
    main()
