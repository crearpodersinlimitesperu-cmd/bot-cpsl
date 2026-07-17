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
    
    # También podemos descartar los que tienen "DESERTOR" en el archivo de productividad_coordinador
    df_prod = pd.read_excel(r'C:\Users\josem\Downloads\productividad_coordinador.xlsx', sheet_name=0)
    desertores_prod = df_prod[df_prod['Asistencia'] == 'DESERTOR']
    for _, row in desertores_prod.iterrows():
        n = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}"
        excluidos.add(normalize_name(n))

    return excluidos

def generar_nuevo_reporte():
    file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
    df = pd.read_excel(file_path, sheet_name=0)
    df['Fecha Gestión'] = pd.to_datetime(df['Fecha Gestión'], errors='coerce')
    df = df.sort_values(by='Fecha Gestión', ascending=False)
    
    df_unicos = df.drop_duplicates(subset=['ClienteId'], keep='first').copy()
    df_vacio = df_unicos[df_unicos['Asistencia'].isna()].copy()
    
    print(f"Total inicial de Asistencia VACÍA: {len(df_vacio)}")
    
    excluidos = cargar_listas_negras()
    print(f"Total de nombres en listas de exclusión: {len(excluidos)}")
    
    aptos = []
    descartados = []
    
    for _, row in df_vacio.iterrows():
        nombre = f"{row['NombreCompleto']} {row['ApellidoCompleto']}".strip()
        n_norm = normalize_name(nombre)
        
        if n_norm in excluidos:
            descartados.append(nombre)
        else:
            aptos.append(row)
            
    df_aptos = pd.DataFrame(aptos)
    df_aptos['Resultado Gestión'] = df_aptos['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)')
    
    print(f"\nParticipantes Descartes: {len(descartados)}")
    print(f"Participantes APTOS y VACÍOS finales: {len(df_aptos)}")
    
    # Generar nuevo artefacto
    md_lines = []
    md_lines.append("# Revisión de Participantes APTOS sin Asistencia (C1)")
    md_lines.append(f"\nSe encontraron **{len(df_aptos)}** participantes APTOS (se descartaron {len(descartados)} no aptos) cuya asistencia está VACÍA.")
    md_lines.append("*(Se eliminaron duplicados conservando el resultado de su gestión más reciente)*\n")
    md_lines.append("Aquí tienes el desglose según su **Resultado de Gestión**:\n")

    for gestion, group in df_aptos.groupby('Resultado Gestión'):
        md_lines.append(f"## {gestion} ({len(group)} personas)")
        md_lines.append("| Equipo | Nombre Completo | Última Gestión |")
        md_lines.append("|---|---|---|")
        for _, row in group.iterrows():
            nombre = f"{row['NombreCompleto']} {row['ApellidoCompleto']}".strip().title()
            fecha_str = row['Fecha Gestión'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['Fecha Gestión']) else 'Sin fecha'
            equipo = str(row['Equipo'])
            md_lines.append(f"| {equipo} | {nombre} | {fecha_str} |")
        md_lines.append("\n")

    out_md = r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\revision_productividad_aptos.md'
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
        
    print("Reporte de APTOS generado.")

if __name__ == "__main__":
    generar_nuevo_reporte()
