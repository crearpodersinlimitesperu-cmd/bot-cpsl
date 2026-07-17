import pandas as pd
import re
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def norm(n):
    if pd.isna(n): return ''
    n = str(n).upper().strip()
    for a,b in [('Á','A'),('É','E'),('Í','I'),('Ó','O'),('Ú','U')]:
        n = n.replace(a,b)
    return re.sub(r'\s+',' ',n)

df1 = pd.read_excel(r'C:\Users\josem\Downloads\reporte_equipos.xlsx')
df2 = pd.read_excel(r'C:\Users\josem\Downloads\productividad_coordinador.xlsx')

# Crear clave de nombre normalizado
df1['key'] = df1.apply(lambda r: norm(str(r['NombreCompleto']) + ' ' + str(r['ApellidoCompleto'])), axis=1)
df2['key'] = df2.apply(lambda r: norm(str(r['NombreCompleto']) + ' ' + str(r['ApellidoCompleto'])), axis=1)

# Dedup productividad
df2['Fecha Gestión'] = pd.to_datetime(df2['Fecha Gestión'], errors='coerce')
df2 = df2.sort_values('Fecha Gestión', ascending=False)
df2_unicos = df2.drop_duplicates(subset='ClienteId', keep='first')

keys1 = set(df1['key'])
keys2 = set(df2_unicos['key'])

comunes = keys1 & keys2
solo_reporte = keys1 - keys2
solo_prod = keys2 - keys1

print(f"Reporte Equipos (personas): {len(df1)} | Nombres únicos: {len(keys1)}")
print(f"Productividad (personas únicas): {len(df2_unicos)} | Nombres únicos: {len(keys2)}")
print(f"\nEN AMBOS ARCHIVOS: {len(comunes)}")
print(f"Solo en Reporte Equipos: {len(solo_reporte)}")
print(f"Solo en Productividad: {len(solo_prod)}")

# Equipos del reporte
print("\n--- Equipos en Reporte Equipos ---")
print(df1['NombreEquipo'].value_counts().to_string())

print("\n--- Equipos en Productividad (top 15) ---")
print(df2_unicos['Equipo'].value_counts().head(15).to_string())

# Ahora el cruce real: enriquecer productividad con datos del reporte
# Para los que están en ambos, traer: Identificación, TelefonoMovil, Correo, NombreIMO, TelefonoIMO
df2_vacio = df2_unicos[df2_unicos['Asistencia'].isna()].copy()

# Filtrar no aptos
aptos = []
for _, row in df2_vacio.iterrows():
    gestion = str(row.get('Resultado Gestión', '')).upper()
    if 'NO LE INTERESA' in gestion or 'SIGUIENTE' in gestion:
        continue
    aptos.append(row)

df_aptos = pd.DataFrame(aptos)

# Extraer numero de equipo
df_aptos['Equipo_Num'] = df_aptos['Equipo'].apply(lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0)
df_objetivo = df_aptos[df_aptos['Equipo_Num'].isin([25, 26, 27, 28])].copy()

print(f"\n{'='*70}")
print(f"APTOS con Asistencia VACÍA en Equipos 25-28: {len(df_objetivo)}")
print(f"{'='*70}")

# Merge con reporte_equipos para traer teléfono, correo, DNI, IMO
df1_dedup = df1.drop_duplicates(subset='key', keep='first')
df_merged = df_objetivo.merge(df1_dedup[['key', 'Identificación', 'TelefonoMovil', 'Correo', 'NombreIMO', 'TelefonoIMO', 'EquipoIMO']], on='key', how='left')

encontrados = df_merged['TelefonoMovil'].notna().sum()
no_encontrados = df_merged['TelefonoMovil'].isna().sum()

print(f"Cruce exitoso (con teléfono/correo del reporte): {encontrados}")
print(f"Sin datos adicionales del reporte: {no_encontrados}")

# Generar Markdown
df_merged['Resultado Gestión'] = df_merged['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)')

md = []
md.append("# Cruce: Productividad × Reporte Equipos (E25-E28)")
md.append(f"\nSe cruzaron los **{len(df_objetivo)}** participantes APTOS (Asistencia VACÍA) de los Equipos 25-28")
md.append(f"con el Reporte de Equipos para obtener sus datos de contacto (DNI, Teléfono, Correo, IMO).\n")
md.append(f"- Datos de contacto encontrados: **{encontrados}**")
md.append(f"- Sin datos adicionales: **{no_encontrados}**\n")

for equipo_num in [25, 26, 27, 28]:
    grupo_eq = df_merged[df_merged['Equipo_Num'] == equipo_num]
    if len(grupo_eq) == 0:
        continue
    md.append(f"## Equipo {equipo_num} ({len(grupo_eq)} personas)")
    
    for gestion, group in grupo_eq.groupby('Resultado Gestión'):
        md.append(f"### {gestion} ({len(group)})")
        md.append("| DNI | Nombre | Teléfono | Correo | IMO | Última Gestión |")
        md.append("|---|---|---|---|---|---|")
        for _, row in group.iterrows():
            nombre = (str(row['NombreCompleto']) + ' ' + str(row['ApellidoCompleto'])).strip().title()
            dni = str(row.get('Identificación', '')).replace('.0', '').replace('nan', '')
            tel = str(row.get('TelefonoMovil', '')).replace('.0', '').replace('nan', '')
            correo = str(row.get('Correo', '')).replace('nan', '')
            imo = str(row.get('NombreIMO', '')).replace('nan', '').title()
            fecha = row['Fecha Gestión'].strftime('%d/%m/%Y') if pd.notnull(row['Fecha Gestión']) else 'Sin fecha'
            md.append(f"| {dni} | {nombre} | {tel} | {correo} | {imo} | {fecha} |")
    md.append("\n")

out = r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\cruce_productividad_reporte.md'
with open(out, 'w', encoding='utf-8') as f:
    f.write("\n".join(md))

print("\nReporte de cruce generado exitosamente.")
