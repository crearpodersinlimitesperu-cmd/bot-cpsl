import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
df = pd.read_excel(file_path, sheet_name=0)

print(f"Total registros brutos: {len(df)}")

# Asegurarse que Fecha Gestión sea tipo datetime
df['Fecha Gestión'] = pd.to_datetime(df['Fecha Gestión'], errors='coerce')

# Ordenar por fecha de gestión descendente para que la más reciente quede primero
df = df.sort_values(by='Fecha Gestión', ascending=False)

# Eliminar duplicados por ClienteId, conservando solo el más reciente
df_unicos = df.drop_duplicates(subset=['ClienteId'], keep='first').copy()
print(f"Participantes únicos encontrados: {len(df_unicos)}")

# Filtrar vacíos en Columna Asistencia
df_vacio = df_unicos[df_unicos['Asistencia'].isna()].copy()
print(f"Participantes únicos con Asistencia VACÍA: {len(df_vacio)}")

# Rellenar vacíos en Resultado Gestión para no romper el group_by
df_vacio['Resultado Gestión'] = df_vacio['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)')

# Generar Markdown
md_lines = []
md_lines.append("# Revisión de Participantes sin Asistencia Confirmada (C1)")
md_lines.append(f"\nSe encontraron **{len(df_vacio)}** participantes únicos cuya asistencia está VACÍA.")
md_lines.append("*(Se eliminaron duplicados conservando el resultado de su gestión más reciente)*\n")
md_lines.append("Aquí tienes el desglose según su **Resultado de Gestión**:\n")

# Agrupar por Resultado de Gestión
for gestion, group in df_vacio.groupby('Resultado Gestión'):
    md_lines.append(f"## {gestion} ({len(group)} personas)")
    md_lines.append("| Equipo | Nombre Completo | Última Gestión |")
    md_lines.append("|---|---|---|")
    for _, row in group.iterrows():
        nombre = f"{row['NombreCompleto']} {row['ApellidoCompleto']}".strip().title()
        fecha_str = row['Fecha Gestión'].strftime('%d/%m/%Y %H:%M') if pd.notnull(row['Fecha Gestión']) else 'Sin fecha'
        equipo = str(row['Equipo'])
        md_lines.append(f"| {equipo} | {nombre} | {fecha_str} |")
    md_lines.append("\n")

with open(r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\revision_productividad_unica.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))

print("Artefacto markdown generado correctamente.")
