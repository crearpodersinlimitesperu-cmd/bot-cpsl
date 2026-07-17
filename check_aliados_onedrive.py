import pandas as pd
import os
import glob
import unicodedata
import re

def normalize_name(name):
    if not isinstance(name, str) or not name.strip(): return ""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8").lower()
    return re.sub(r'[^a-z]', '', name)

def get_names_from_c1(path):
    names = set()
    try:
        df = pd.read_excel(path)
        # Often C1 files have no header and names are in the last columns
        for _, row in df.iterrows():
            parts = [str(x) for x in row.values if pd.notnull(x) and isinstance(x, str) and len(x) > 2]
            if parts:
                full_name = " ".join(parts)
                # This might include noise, but normalization will strip non-letters
                norm = normalize_name(full_name)
                if len(norm) > 5:
                    names.add(norm)
                    
                    # Also try combining the last two parts specifically as First Last
                    if len(parts) >= 2:
                        names.add(normalize_name(parts[-2] + " " + parts[-1]))
                        names.add(normalize_name(parts[-1] + " " + parts[-2]))
    except Exception as e:
        print(f"Error reading C1 file {path}: {e}")
    return names

def get_names_from_c2(path):
    names = set()
    try:
        df = pd.read_excel(path)
        
        # Determine columns
        col_name = None
        col_last = None
        col_status = None
        
        for col in df.columns:
            cl = str(col).lower()
            if 'nombre' in cl: col_name = col
            if 'apellido' in cl: col_last = col
            if 'status' in cl or 'estado' in cl: col_status = col
            
        for _, row in df.iterrows():
            n = str(row.get(col_name, '')) if col_name else ''
            a = str(row.get(col_last, '')) if col_last else ''
            status = str(row.get(col_status, '')).upper() if col_status else ''
            
            # If status says desertor, abandonó, sentado, etc. 
            # The prompt implies: exclude anyone who is seated OR a dropout in C1/C2
            # Actually, to be safe, if they are in these aliado/attendance files, they are either seated or dropouts.
            # We'll just take the name if it's somewhat valid
            
            full = (n + " " + a).strip()
            if len(full) < 3:
                # Try to find string columns
                parts = [str(x) for x in row.values if pd.notnull(x) and isinstance(x, str) and len(x) > 2]
                full = " ".join(parts)
                
            norm = normalize_name(full)
            if len(norm) > 5:
                names.add(norm)
                if n and a:
                    names.add(normalize_name(n + " " + a))
                    names.add(normalize_name(a + " " + n))
    except Exception as e:
        print(f"Error reading C2 file {path}: {e}")
    return names

def main():
    dir_c1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"
    dir_c2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2"
    
    files_c1 = glob.glob(os.path.join(dir_c1, "*.xlsx"))
    files_c2 = glob.glob(os.path.join(dir_c2, "*.xlsx"))
    
    blacklisted_names = set()
    
    print(f"Processing {len(files_c1)} files from C1...")
    for f in files_c1:
        blacklisted_names.update(get_names_from_c1(f))
        
    print(f"Processing {len(files_c2)} files from C2...")
    for f in files_c2:
        blacklisted_names.update(get_names_from_c2(f))
        
    print(f"Total unique normalized names extracted: {len(blacklisted_names)}")
    
    # Check against our base list
    aptos_path = r"c:\Users\josem\Downloads\bot-cpsl-review\Aptos_E26_E27_ZeroBounces.csv"
    if not os.path.exists(aptos_path):
        print("Base file not found!")
        return
        
    df_aptos = pd.read_csv(aptos_path, encoding='utf-8-sig')
    
    valid_rows = []
    excluidos = []
    
    for idx, row in df_aptos.iterrows():
        nombre = str(row.get('NombreCompleto', '')).strip()
        apellido = str(row.get('ApellidoCompleto', '')).strip()
        
        # Variations to check
        norm1 = normalize_name(nombre + " " + apellido)
        norm2 = normalize_name(apellido + " " + nombre)
        
        # Sub-variations (just first name and first last name)
        n_parts = nombre.split()
        a_parts = apellido.split()
        norm3 = ""
        norm4 = ""
        if n_parts and a_parts:
            norm3 = normalize_name(n_parts[0] + " " + a_parts[0])
            norm4 = normalize_name(a_parts[0] + " " + n_parts[0])
            
        if norm1 in blacklisted_names or norm2 in blacklisted_names or (norm3 and norm3 in blacklisted_names) or (norm4 and norm4 in blacklisted_names):
            excluidos.append(row)
        else:
            valid_rows.append(row)
            
    df_validos = pd.DataFrame(valid_rows)
    df_excluidos = pd.DataFrame(excluidos)
    
    df_validos.to_csv(aptos_path, index=False, encoding='utf-8-sig')
    
    if len(df_excluidos) > 0:
        df_excluidos.to_csv(r"c:\Users\josem\Downloads\bot-cpsl-review\Excluidos_OneDrive_C1_C2.csv", index=False, encoding='utf-8-sig')
        
    print("--- RESULTADOS ---")
    print(f"Total en lista antes: {len(df_aptos)}")
    print(f"Excluidos por match en OneDrive (Sentados/Desertores): {len(df_excluidos)}")
    print(f"Lista Definitiva (E26/E27): {len(df_validos)}")
    
    # Print some excluded names for visibility
    if excluidos:
        print("\nEjemplo de excluidos:")
        for r in excluidos[:10]:
            print(f"- {r.get('NombreCompleto', '')} {r.get('ApellidoCompleto', '')}")

if __name__ == "__main__":
    main()
