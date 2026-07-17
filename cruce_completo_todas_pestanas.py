import pandas as pd
import re
import sys
import os

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

def limpiar_tel(t):
    if pd.isna(t): return ''
    t = ''.join(filter(str.isdigit, str(t)))
    if len(t) > 9 and t.startswith('51'): t = t[2:]
    if t == '0': return ''
    return t

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
                            excluidos.add(norm(val))
                        break
            except:
                pass
    return excluidos

# ============================================================
# 1. CARGAR TODAS LAS PESTAÑAS DE REPORTE EQUIPOS
# ============================================================
print("="*70)
print(" CRUCE COMPLETO: PRODUCTIVIDAD (3 CC) × REPORTE EQUIPOS (E25-E28)")
print("="*70)

reporte_path = r'C:\Users\josem\Downloads\reporte_equipos.xlsx'
prod_path = r'C:\Users\josem\Downloads\productividad_coordinador.xlsx'

# Cargar TODAS las pestañas del reporte
reporte_sheets = ['25', '26', '27', '28']
dfs_reporte = []
for sheet in reporte_sheets:
    df = pd.read_excel(reporte_path, sheet_name=sheet)
    df['Pestaña_Reporte'] = f'E{sheet}'
    dfs_reporte.append(df)
    print(f"  Reporte E{sheet}: {len(df)} filas")

df_reporte = pd.concat(dfs_reporte, ignore_index=True)
df_reporte['key'] = df_reporte.apply(lambda r: norm(str(r['NombreCompleto']) + ' ' + str(r['ApellidoCompleto'])), axis=1)
df_reporte_dedup = df_reporte.drop_duplicates(subset='key', keep='first')
print(f"  TOTAL Reporte (todas las pestañas): {len(df_reporte)} filas, {len(df_reporte_dedup)} únicos")

# ============================================================
# 2. CARGAR TODAS LAS PESTAÑAS DE PRODUCTIVIDAD
# ============================================================
prod_sheets = ['DIANA MOSCOSO', 'JOYCE MARIN', 'JOSE SANCHEZ']
dfs_prod = []
for sheet in prod_sheets:
    df = pd.read_excel(prod_path, sheet_name=sheet)
    df['Coordinador_Pestaña'] = sheet
    dfs_prod.append(df)
    print(f"  Productividad {sheet}: {len(df)} filas")

df_prod = pd.concat(dfs_prod, ignore_index=True)
df_prod['Fecha Gestión'] = pd.to_datetime(df_prod['Fecha Gestión'], errors='coerce')
df_prod = df_prod.sort_values('Fecha Gestión', ascending=False)
df_prod_unicos = df_prod.drop_duplicates(subset=['ClienteId', 'Coordinador_Pestaña'], keep='first')
# Ahora dedup global por nombre (un px puede estar en más de una pestaña)
df_prod_unicos['key'] = df_prod_unicos.apply(lambda r: norm(str(r['NombreCompleto']) + ' ' + str(r['ApellidoCompleto'])), axis=1)
df_prod_unicos_global = df_prod_unicos.drop_duplicates(subset='key', keep='first')
print(f"  TOTAL Productividad (todas las pestañas): {len(df_prod)} filas, {len(df_prod_unicos_global)} únicos")

# ============================================================
# 3. CRUCE
# ============================================================
keys_reporte = set(df_reporte_dedup['key'])
keys_prod = set(df_prod_unicos_global['key'])
comunes = keys_reporte & keys_prod
solo_reporte = keys_reporte - keys_prod
solo_prod = keys_prod - keys_reporte

print(f"\n{'='*70}")
print(f"EN AMBOS ARCHIVOS: {len(comunes)}")
print(f"Solo en Reporte Equipos: {len(solo_reporte)}")
print(f"Solo en Productividad: {len(solo_prod)}")
print(f"{'='*70}")

# ============================================================
# 4. FILTRAR APTOS (Asistencia vacía, sin No Interesados, etc.)
# ============================================================
excluidos = cargar_listas_negras()

df_vacio = df_prod_unicos_global[df_prod_unicos_global['Asistencia'].isna()].copy()
print(f"\nAsistencia VACÍA (todas las pestañas, sin duplicados): {len(df_vacio)}")

# Extraer equipo num
df_vacio['Equipo_Num'] = df_vacio['Equipo'].apply(lambda x: int(re.search(r'\d+', str(x)).group()) if re.search(r'\d+', str(x)) else 0)

aptos = []
descartados_gestion = 0
descartados_lista = 0

for _, row in df_vacio.iterrows():
    gestion = str(row.get('Resultado Gestión', '')).upper()
    n_norm = row['key']
    
    if 'NO LE INTERESA' in gestion or 'SIGUIENTE' in gestion:
        descartados_gestion += 1
        continue
    if n_norm in excluidos:
        descartados_lista += 1
        continue
    aptos.append(row)

df_aptos = pd.DataFrame(aptos)
print(f"Descartados por gestión: {descartados_gestion}")
print(f"Descartados por lista negra: {descartados_lista}")
print(f"APTOS FINALES (Asistencia Vacía): {len(df_aptos)}")

# ============================================================
# 5. ENRIQUECER CON DATOS DEL REPORTE
# ============================================================
df_merged = df_aptos.merge(
    df_reporte_dedup[['key', 'Identificación', 'TelefonoMovil', 'Correo', 'NombreIMO', 'TelefonoIMO', 'EquipoIMO', 'Pestaña_Reporte']],
    on='key', how='left'
)

con_datos = df_merged['TelefonoMovil'].notna().sum()
sin_datos = df_merged['TelefonoMovil'].isna().sum()
print(f"\nEnriquecidos con datos del Reporte: {con_datos}")
print(f"Sin datos adicionales: {sin_datos}")

# Por equipo
print("\nDesglose por equipo:")
print(df_merged['Equipo_Num'].value_counts().sort_index().to_string())

print("\nDesglose por Coordinador (pestaña):")
print(df_merged['Coordinador_Pestaña'].value_counts().to_string())

# ============================================================
# 6. GENERAR REPORTE MARKDOWN
# ============================================================
df_merged['Resultado Gestión'] = df_merged['Resultado Gestión'].fillna('SIN GESTIÓN (VACÍO)')

md = []
md.append("# Cruce Completo: Productividad (3 CC) × Reporte Equipos (E25-E28)")
md.append(f"\n**Fuentes:**")
md.append(f"- Productividad: 3 pestañas (Diana Moscoso, Joyce Marín, José Sánchez)")
md.append(f"- Reporte Equipos: 4 pestañas (E25, E26, E27, E28)")
md.append(f"\n**Resultado del cruce:**")
md.append(f"- Total APTOS con Asistencia VACÍA: **{len(df_aptos)}**")
md.append(f"- Enriquecidos con teléfono/correo: **{con_datos}**")
md.append(f"- Sin datos adicionales: **{sin_datos}**\n")

for equipo_num in sorted(df_merged['Equipo_Num'].unique()):
    grupo_eq = df_merged[df_merged['Equipo_Num'] == equipo_num]
    if len(grupo_eq) == 0:
        continue
    md.append(f"## Equipo {equipo_num} ({len(grupo_eq)} personas)")
    
    for gestion, group in grupo_eq.groupby('Resultado Gestión'):
        md.append(f"### {gestion} ({len(group)})")
        md.append("| CC | DNI | Nombre | Teléfono | Correo | IMO | Últ. Gestión |")
        md.append("|---|---|---|---|---|---|---|")
        for _, row in group.iterrows():
            nombre = (str(row['NombreCompleto']) + ' ' + str(row['ApellidoCompleto'])).strip().title()
            cc = str(row.get('Coordinador_Pestaña', '')).replace('nan', '')
            dni = str(row.get('Identificación', '')).replace('.0', '').replace('nan', '')
            tel = limpiar_tel(row.get('TelefonoMovil', ''))
            correo = str(row.get('Correo', '')).replace('nan', '')
            imo = str(row.get('NombreIMO', '')).replace('nan', '').title()
            fecha = row['Fecha Gestión'].strftime('%d/%m/%Y') if pd.notnull(row['Fecha Gestión']) else 'Sin fecha'
            md.append(f"| {cc} | {dni} | {nombre} | {tel} | {correo} | {imo} | {fecha} |")
    md.append("\n")

out = r'C:\Users\josem\.gemini\antigravity\brain\89f29366-a074-4b6b-8882-8c079d3be98e\cruce_completo_prod_reporte.md'
with open(out, 'w', encoding='utf-8') as f:
    f.write("\n".join(md))

print("\n¡Reporte completo generado!")
