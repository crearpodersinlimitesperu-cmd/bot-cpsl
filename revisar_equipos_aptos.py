import pandas as pd
import sys
import re
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U")
    )
    for a, b in replacements:
        name = name.replace(a, b)
    return re.sub(r'\s+', ' ', name)

def cargar_listas_negras():
    excluidos = set()
    files = [
        r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_desertores_total.csv",
        r"c:\Users\josem\Downloads\bot-cpsl-review\Excluidos_Profundos.csv",
        r"c:\Users\josem\Downloads\bot-cpsl-review\Excluidos_OneDrive_C1_C2.csv",
    ]
    for path in files:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path, on_bad_lines='skip')
                for col in df.columns:
                    if 'nombre' in col.lower() or 'participante' in col.lower():
                        for val in df[col].dropna():
                            excluidos.add(normalize_name(val))
                        break
            except Exception as e:
                pass
    return excluidos

def extraer_numero_equipo(equipo_str):
    if pd.isna(equipo_str): return 0
    match = re.search(r'\d+', str(equipo_str))
    if match:
        return int(match.group())
    return 0

def revisar_equipos():
    file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
    df = pd.read_excel(file_path, sheet_name=0)
    df['Fecha Gestión'] = pd.to_datetime(df['Fecha Gestión'], errors='coerce')
    df = df.sort_values(by='Fecha Gestión', ascending=False)
    
    df_unicos = df.drop_duplicates(subset=['ClienteId'], keep='first').copy()
    df_vacio = df_unicos[df_unicos['Asistencia'].isna()].copy()
    
    excluidos_nombres = cargar_listas_negras()
    
    aptos = []
    
    for _, row in df_vacio.iterrows():
        nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip()
        n_norm = normalize_name(nombre)
        gestion = str(row.get('Resultado Gestión', '')).upper()
        
        if 'NO LE INTERESA' in gestion or 'SIGUIENTE' in gestion:
            continue
        if n_norm in excluidos_nombres:
            continue
            
        aptos.append(row)
            
    df_aptos = pd.DataFrame(aptos)
    
    # Extraer numero de equipo
    df_aptos['Equipo_Num'] = df_aptos['Equipo'].apply(extraer_numero_equipo)
    
    equipos_objetivo = [25, 26, 27, 28]
    df_objetivo = df_aptos[df_aptos['Equipo_Num'].isin(equipos_objetivo)]
    df_otros = df_aptos[~df_aptos['Equipo_Num'].isin(equipos_objetivo)]
    
    print("="*60)
    print(" DISTRIBUCIÓN DE LOS 415 APTOS POR EQUIPO")
    print("="*60)
    
    print(f"\nPERTENECEN A LOS EQUIPOS [25, 26, 27, 28]: {len(df_objetivo)} personas")
    if len(df_objetivo) > 0:
        print(df_objetivo['Equipo_Num'].value_counts().sort_index().to_string())
        
        print("\nDesglose de los equipos objetivos por Resultado de Gestión:")
        print(df_objetivo['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)').value_counts().to_string())
        
    print(f"\nPERTENECEN A OTROS EQUIPOS: {len(df_otros)} personas")
    if len(df_otros) > 0:
        # Mostrar los top 10 equipos
        print(df_otros['Equipo_Num'].value_counts().head(10).to_string())

if __name__ == "__main__":
    revisar_equipos()
