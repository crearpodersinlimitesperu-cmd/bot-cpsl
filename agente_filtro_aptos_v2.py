import pandas as pd
import os
import re

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).upper().strip()
    # Remove accents
    replacements = (
        ("á", "A"), ("é", "E"), ("í", "I"), ("ó", "O"), ("ú", "U"),
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U")
    )
    for a, b in replacements:
        name = name.replace(a, b)
    return re.sub(r'\s+', ' ', name)

def get_desertores():
    path = r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_desertores_total.csv"
    desertores = set()
    try:
        if os.path.exists(path):
            df = pd.read_csv(path, on_bad_lines='skip', encoding='utf-8')
            if 'Nombre' in df.columns:
                for name in df['Nombre']:
                    desertores.add(normalize_name(name))
    except Exception as e:
        print(f"Error loading desertores: {e}")
    return desertores

def get_rebotes():
    path = r"c:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_2AÑOS.csv"
    rebotes = set()
    try:
        if os.path.exists(path):
            df = pd.read_csv(path, on_bad_lines='skip', encoding='utf-8')
            # Extract names or emails if possible. Assuming it has some identifiable data.
    except:
        pass
    return rebotes

def main():
    print("Iniciando Agente de Filtro de Aptos para Joyce y Diana...")
    
    file1 = r"c:\Users\josem\Downloads\bot-cpsl-review\Asignacion_C1.xlsx"
    file2 = r"c:\Users\josem\Downloads\bot-cpsl-review\Asignaciones_Web.xlsx"
    
    df_main = None
    usuario_col = None
    for f in [file1, file2]:
        try:
            if os.path.exists(f):
                df_temp = pd.read_excel(f)
                if 'Usuario Registro' in df_temp.columns or 'Usuario Actual' in df_temp.columns:
                    df_main = df_temp
                    usuario_col = 'Usuario Registro' if 'Usuario Registro' in df_temp.columns else 'Usuario Actual'
                    print(f"Loaded source file: {f}")
                    break
        except Exception as e:
            pass
            
    if df_main is None:
        print("No se encontró el archivo principal de asignaciones.")
        return

    coordinators = ['jmarin', 'dmoscoso', 'joyce', 'diana', 'joyce pamela marín suarez', 'diana yesenia moscoso robles']
    df_main['Usuario_Norm'] = df_main[usuario_col].astype(str).str.lower().str.strip()
    
    mask_jmarin = df_main['Usuario_Norm'].isin(coordinators)
    
    df_jd = df_main[mask_jmarin].copy()
    print(f"Total asignados a Joyce y Diana antes de filtros: {len(df_jd)}")
    
    desertores = get_desertores()
    print(f"Total desertores/devoluciones a excluir (por nombre): {len(desertores)}")
    
    aptos = []
    motivos_exclusion = []
    
    for idx, row in df_jd.iterrows():
        nombre_completo = normalize_name(str(row.get('NombreCompleto', '')) + " " + str(row.get('ApellidoCompleto', '')))
        
        excluir = False
        motivo = ""
        
        if nombre_completo in desertores:
            excluir = True
            motivo = "Desertor/Devolucion/No Asiste"

        if not excluir:
            aptos.append(row)
        else:
            motivos_exclusion.append({'Nombre': nombre_completo, 'Motivo': motivo})
            
    df_aptos = pd.DataFrame(aptos)
    if not df_aptos.empty and 'Usuario_Norm' in df_aptos.columns:
        df_aptos = df_aptos.drop(columns=['Usuario_Norm'])
        
    out_file = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana.csv"
    if not df_aptos.empty:
        df_aptos.to_csv(out_file, index=False, encoding='utf-8-sig')
        print(f"Filtro completado. Total Aptos: {len(df_aptos)}")
        print(f"Archivo guardado en: {out_file}")
    else:
        print("No se encontraron personas aptas.")
    
    print("\n--- Resumen de Excluidos ---")
    for exc in motivos_exclusion:
        print(f"Excluido: {exc['Nombre']} -> {exc['Motivo']}")

if __name__ == "__main__":
    main()
