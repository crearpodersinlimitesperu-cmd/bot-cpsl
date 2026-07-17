import pandas as pd
import sqlite3
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

df = pd.read_csv(csv_path)

# Mapeo de coordinadoras
COORDINADORAS = {
    'jmarin': {'nombre': 'Joyce Marin', 'telefono': '933 599 903'},
    'dmoscoso': {'nombre': 'Diana Moscoso', 'telefono': '912 379 744'},
}

print("="*80)
print("  REVISIÓN DETALLADA DE DATOS PARA CORREO A IMOS")
print("="*80)

print(f"\nColumnas disponibles: {df.columns.tolist()}")
print(f"Total de registros en CSV: {len(df)}")

# Filtrar solo E25, E26, E27
df['equipo_num'] = df['NombreEquipo'].str.extract(r'(\d+)').astype(float)
df_filtrado = df[df['equipo_num'].isin([25, 26, 27])].copy()
print(f"\nRegistros filtrados (E25, E26, E27): {len(df_filtrado)}")
print(f"Distribución por equipo:")
print(df_filtrado['NombreEquipo'].value_counts())

print(f"\nDistribución por coordinadora (Usuario Registro):")
print(df_filtrado['Usuario Registro'].value_counts())

# Agrupar por IMO
imo_ids = df_filtrado['IdentificacionIMO'].dropna().unique()
print(f"\nTotal IMOs únicos: {len(imo_ids)}")

# Buscar info de IMOs en la BD
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Convertir a strings para la query
imo_ids_str = [str(int(x)) if not pd.isna(x) else '' for x in imo_ids]
placeholders = ','.join(['?' for _ in imo_ids_str])
query = f"SELECT identificacion, nombre, apellido, email, telefono FROM participantes WHERE identificacion IN ({placeholders})"
cursor.execute(query, imo_ids_str)
imo_rows = cursor.fetchall()

imo_dict = {}
for row in imo_rows:
    imo_dict[str(row[0])] = {
        'nombre': row[1],
        'apellido': row[2],
        'email': row[3],
        'telefono': row[4]
    }

print(f"IMOs encontrados en BD con datos: {len(imo_dict)}")

# Ahora hacer el desglose completo
print("\n" + "="*80)
print("  DESGLOSE POR IMO: PARTICIPANTES ASIGNADOS")
print("="*80)

imos_con_email = 0
imos_sin_email = 0
total_px_con_imo_email = 0
total_px_sin_imo_email = 0

reporte_lineas = []

for imo_id in sorted(imo_ids_str):
    if not imo_id:
        continue
    px_de_este_imo = df_filtrado[df_filtrado['IdentificacionIMO'].astype(str).str.replace('.0','',regex=False) == imo_id]
    if len(px_de_este_imo) == 0:
        continue
    
    imo_info = imo_dict.get(imo_id, None)
    
    if imo_info and imo_info['email'] and imo_info['email'] != 'REBOTE' and '@' in str(imo_info['email']):
        imo_nombre = f"{imo_info['nombre']} {imo_info['apellido']}".strip().title()
        imo_email = imo_info['email']
        imo_tel = imo_info['telefono']
        imos_con_email += 1
        total_px_con_imo_email += len(px_de_este_imo)
        estado = "✅ CON EMAIL"
    else:
        imo_nombre = f"DNI {imo_id}"
        imo_email = "NO ENCONTRADO"
        imo_tel = "N/A"
        if imo_info:
            imo_nombre = f"{imo_info.get('nombre','')} {imo_info.get('apellido','')}".strip().title()
            imo_tel = imo_info.get('telefono', 'N/A')
        imos_sin_email += 1
        total_px_sin_imo_email += len(px_de_este_imo)
        estado = "❌ SIN EMAIL"
    
    linea = f"\n--- IMO: {imo_nombre} (DNI: {imo_id}) [{estado}]"
    linea += f"\n    Email: {imo_email} | Tel: {imo_tel}"
    linea += f"\n    Participantes asignados ({len(px_de_este_imo)}):"
    
    for _, px in px_de_este_imo.iterrows():
        coord_key = str(px['Usuario Registro']).strip().lower()
        coord_info = COORDINADORAS.get(coord_key, {'nombre': coord_key, 'telefono': '???'})
        nombre_px = f"{px['NombreCompleto']} {px['ApellidoCompleto']}".strip().title()
        equipo = px['NombreEquipo']
        tel_px = px.get('TelefonoMovil', 'N/A')
        linea += f"\n      • {nombre_px} ({equipo}) -> Coord: {coord_info['nombre']} ({coord_info['telefono']}) | Tel PX: {tel_px}"
    
    reporte_lineas.append(linea)
    print(linea)

print("\n" + "="*80)
print("  RESUMEN FINAL")
print("="*80)
print(f"IMOs con email válido (SE ENVIARÁN):    {imos_con_email} ({total_px_con_imo_email} participantes)")
print(f"IMOs sin email (NO SE ENVIARÁN):        {imos_sin_email} ({total_px_sin_imo_email} participantes)")
print(f"Total participantes E25/E26/E27:        {len(df_filtrado)}")

# Guardar reporte completo
with open(r'C:\Users\josem\Downloads\bot-cpsl-review\revision_detallada_imos_aptos.txt', 'w', encoding='utf-8') as f:
    f.write("REVISIÓN DETALLADA DE DATOS PARA CORREO A IMOS\n")
    f.write("="*80 + "\n")
    f.write(f"Total registros E25/E26/E27: {len(df_filtrado)}\n")
    f.write(f"IMOs únicos: {len(imo_ids)}\n")
    f.write(f"IMOs con email: {imos_con_email}\n")
    f.write(f"IMOs sin email: {imos_sin_email}\n")
    f.write("="*80 + "\n")
    for linea in reporte_lineas:
        f.write(linea + "\n")

print("\nReporte guardado en: revision_detallada_imos_aptos.txt")
conn.close()
