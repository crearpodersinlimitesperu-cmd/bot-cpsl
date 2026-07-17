import pandas as pd
import sys
import os

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

import re

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).upper().strip()
    replacements = (
        ("Á", "A"), ("É", "E"), ("Í", "I"), ("Ó", "O"), ("Ú", "U")
    )
    for a, b in replacements:
        name = name.replace(a, b)
    return re.sub(r'\s+', ' ', name)

def cruzar_con_data_maestra():
    csv_aptos = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
    df_aptos = pd.read_csv(csv_aptos)
    
    nombres_validos = set()
    for _, row in df_aptos.iterrows():
        n = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}"
        nombres_validos.add(normalize_name(n))
        
    print(f"Total de Nombres válidos en la base maestra APTOS: {len(nombres_validos)}")
    
    file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
    df_prod = pd.read_excel(file_path, sheet_name=0)
    
    df_prod['Fecha Gestión'] = pd.to_datetime(df_prod['Fecha Gestión'], errors='coerce')
    df_prod = df_prod.sort_values(by='Fecha Gestión', ascending=False)
    
    df_unicos = df_prod.drop_duplicates(subset=['ClienteId'], keep='first').copy()
    df_vacio = df_unicos[df_unicos['Asistencia'].isna()].copy()
    
    print(f"Total inicial en productividad (Asistencia VACÍA, sin duplicados): {len(df_vacio)}")
    
    # 3. CRUCE INTELIGENTE POR NOMBRE
    df_vacio['Nombre_Norm'] = df_vacio.apply(lambda row: normalize_name(f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}"), axis=1)
    df_final = df_vacio[df_vacio['Nombre_Norm'].isin(nombres_validos)].copy()
    
    descartados = len(df_vacio) - len(df_final)
    print(f"No Aptos descartados en este cruce: {descartados}")
    print(f"Participantes APTOS reales y VACÍOS finales: {len(df_final)}")
    
    # 4. Generar Reporte Markdown
    df_final['Resultado Gestión'] = df_final['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)')
    
    md_lines = []
    md_lines.append("# Revisión de Participantes APTOS sin Asistencia (C1)")
    md_lines.append(f"\nSe cruzó la información de productividad con la base maestra global de APTOS.")
    md_lines.append(f"Se descartaron **{descartados}** participantes por no cumplir los requisitos de Aptos.")
    md_lines.append(f"Quedaron **{len(df_final)}** participantes APTOS reales con Asistencia VACÍA.")
    md_lines.append("*(Se eliminaron duplicados conservando el resultado de su gestión más reciente)*\n")
    md_lines.append("Aquí tienes el desglose según su **Resultado de Gestión**:\n")

    for gestion, group in df_final.groupby('Resultado Gestión'):
        md_lines.append(f"## {gestion} ({len(group)} personas)")
        md_lines.append("| Equipo | Nombre Completo | Teléfono | Última Gestión |")
        md_lines.append("|---|---|---|---|")
        for _, row in group.iterrows():
            nombre = f"{row['NombreCompleto']} {row['ApellidoCompleto']}".strip().title()
            fecha_str = row['Fecha Gestión'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['Fecha Gestión']) else 'Sin fecha'
            equipo = str(row['Equipo'])
            # Extract phone safely based on available columns
            tel = ""
            for col in ['TelefonoMovil', 'Telefono', 'Celular']:
                if col in row.index and pd.notnull(row[col]):
                    tel = str(row[col]).replace('.0', '')
                    break
            
            md_lines.append(f"| {equipo} | {nombre} | {tel} | {fecha_str} |")
        md_lines.append("\n")

    out_md = r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\revision_productividad_final.md'
    with open(out_md, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
        
    print("Reporte final generado con éxito.")

if __name__ == "__main__":
    cruzar_con_data_maestra()
