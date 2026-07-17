import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

file_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'
df = pd.read_excel(file_path, sheet_name=0)

# Filtrar vacíos en Columna D (Asistencia)
df_vacio = df[df.iloc[:, 3].isna()].copy()

# Rellenar vacíos en Resultado Gestión para no romper
df_vacio.iloc[:, 9] = df_vacio.iloc[:, 9].fillna('SIN GESTIÓN (VACÍO)')

# Limpiar columnas de nombre y apellido
nombre_col = df.columns[5]
apellido_col = df.columns[4]
tel_col = df.columns[6]
res_gestion_col = df.columns[9]
equipo_col = df.columns[1]

md_lines = []
md_lines.append("# Revisión de Participantes sin Asistencia Confirmada (C1)")
md_lines.append(f"\nSe encontraron **{len(df_vacio)}** participantes cuya asistencia (Columna D) está VACÍA.")
md_lines.append("Aquí tienes el desglose según su **Resultado de Gestión** (Columna J):\n")

# Agrupar por Resultado de Gestión
for gestion, group in df_vacio.groupby(df_vacio.columns[9]):
    md_lines.append(f"## {gestion} ({len(group)} personas)")
    md_lines.append("| Equipo | Nombre Completo | Teléfono |")
    md_lines.append("|---|---|---|")
    for _, row in group.iterrows():
        nombre = f"{row[nombre_col]} {row[apellido_col]}".strip().title()
        tel = str(row[tel_col]).replace('.0', '')
        equipo = str(row[equipo_col])
        md_lines.append(f"| {equipo} | {nombre} | {tel} |")
    md_lines.append("\n")

with open(r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\revision_productividad.md', 'w', encoding='utf-8') as f:
    f.write("\n".join(md_lines))

print("Artefacto markdown generado.")
