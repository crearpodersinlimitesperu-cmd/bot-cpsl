import pandas as pd
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Cargar todos los reportes de equipos y combinarlos
files = [
    r'C:\Users\josem\Downloads\reporte_equipos.xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (1).xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (2).xlsx',
    r'C:\Users\josem\Downloads\reporte_equipos (3).xlsx',
]

dfs_reportes = []
for f in files:
    df = pd.read_excel(f)
    dfs_reportes.append(df)
df_reportes = pd.concat(dfs_reportes, ignore_index=True)
print(f"Total registros combinados de reportes: {len(df_reportes)}")

# Limpiar identificaciones
df_reportes['id_clean'] = df_reportes['Identificación'].astype(str).str.strip().str.replace('.0', '', regex=False)

# Cargar los asignados aptos
csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
df_aptos = pd.read_csv(csv_path)

# Filtrar E25, E26, E27
df_aptos['equipo_num'] = df_aptos['NombreEquipo'].str.extract(r'(\d+)').astype(float)
df_aptos = df_aptos[df_aptos['equipo_num'].isin([25, 26, 27])].copy()
print(f"Participantes aptos E25/E26/E27: {len(df_aptos)}")

# Limpiar IdentificacionIMO
df_aptos['imo_id_clean'] = df_aptos['IdentificacionIMO'].astype(str).str.strip().str.replace('.0', '', regex=False)

# Obtener IMOs únicos
imo_ids = df_aptos['imo_id_clean'].unique()
print(f"IMOs únicos: {len(imo_ids)}")

# Ahora buscar en los reportes: un IMO es alguien cuya Identificación coincide con IdentificacionIMO
# Pero los reportes tienen la info del participante, no del IMO directamente.
# Sin embargo, los reportes SÍ tienen NombreIMO y TelefonoIMO.
# Necesitamos buscar al IMO como PARTICIPANTE en los reportes (su propia Identificación = IdentificacionIMO del apto)

# Buscar IMOs como participantes en los reportes (ellos mismos están registrados)
imo_como_px = df_reportes[df_reportes['id_clean'].isin(imo_ids)].copy()
print(f"IMOs encontrados como participantes en reportes: {len(imo_como_px['id_clean'].unique())}")

# Extraer su correo y teléfono
imo_info_from_reportes = {}
for _, row in imo_como_px.iterrows():
    imo_id = row['id_clean']
    if imo_id not in imo_info_from_reportes:
        correo = row.get('Correo', None)
        tel = row.get('TelefonoMovil', None)
        nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip()
        if correo and pd.notna(correo) and '@' in str(correo):
            imo_info_from_reportes[imo_id] = {
                'nombre': nombre,
                'correo': str(correo).strip(),
                'telefono': str(tel).strip() if pd.notna(tel) else ''
            }

print(f"IMOs con correo encontrado en reportes (como participantes): {len(imo_info_from_reportes)}")

# SEGUNDA ESTRATEGIA: Buscar en los registros donde ese IMO aparece como NombreIMO/TelefonoIMO
# Los reportes tienen participantes que fueron enrolados por un IMO. 
# Si buscamos registros donde la IdentificaciónIMO del apto aparece, 
# pero los reportes no tienen IdentificaciónIMO... solo NombreIMO y TelefonoIMO.
# Podemos cruzar por nombre: en el CSV de aptos tenemos IdentificacionIMO.
# Busquemos a esos IMOs que aparecen como participantes en otros equipos.

# Ahora busquemos los que FALTAN
todos_imos_encontrados = set(imo_info_from_reportes.keys())

# Buscar también en los reportes donde el IMO enroló a alguien
# Cada fila del reporte tiene NombreIMO y TelefonoIMO
# Podemos vincular: en el CSV de aptos, el participante tiene IdentificacionIMO
# Si buscamos ese participante en los reportes, encontramos NombreIMO y TelefonoIMO de su IMO
for _, apto in df_aptos.iterrows():
    imo_id = apto['imo_id_clean']
    if imo_id in todos_imos_encontrados:
        continue
    
    px_id = str(apto.get('Identificación', '')).strip().replace('.0', '')
    if not px_id:
        continue
    
    # Buscar este participante en los reportes
    match = df_reportes[df_reportes['id_clean'] == px_id]
    if len(match) > 0:
        row = match.iloc[0]
        nombre_imo = str(row.get('NombreIMO', '')).strip()
        tel_imo = str(row.get('TelefonoIMO', '')).strip()
        
        if nombre_imo and nombre_imo != 'nan':
            if imo_id not in imo_info_from_reportes:
                imo_info_from_reportes[imo_id] = {
                    'nombre': nombre_imo.title(),
                    'correo': '',  # No tenemos correo del IMO por esta vía
                    'telefono': tel_imo if tel_imo != 'nan' else ''
                }
                todos_imos_encontrados.add(imo_id)

print(f"\nIMOs con info (nombre/tel) después de cruzar por participante: {len(imo_info_from_reportes)}")

# Ahora buscar correo del IMO: si el IMO tiene Identificación, buscar en reportes como participante
for imo_id, info in imo_info_from_reportes.items():
    if info['correo']:
        continue
    # Buscar al IMO como participante en los reportes por su Identificación
    match = df_reportes[df_reportes['id_clean'] == imo_id]
    if len(match) > 0:
        for _, row in match.iterrows():
            correo = row.get('Correo', None)
            if correo and pd.notna(correo) and '@' in str(correo):
                info['correo'] = str(correo).strip()
                break

# Resumen final
con_correo = sum(1 for v in imo_info_from_reportes.values() if v['correo'])
con_tel = sum(1 for v in imo_info_from_reportes.values() if v['telefono'] and v['telefono'] != 'nan')
sin_nada = len(imo_ids) - len(imo_info_from_reportes)

print(f"\n{'='*80}")
print(f"  RESUMEN FINAL DE COBERTURA DE IMOS")
print(f"{'='*80}")
print(f"Total IMOs únicos: {len(imo_ids)}")
print(f"IMOs con CORREO: {con_correo}")
print(f"IMOs con TELÉFONO (sin correo): {con_tel - con_correo}")
print(f"IMOs sin datos de contacto: {sin_nada}")

# Guardar resultado
with open(r'C:\Users\josem\Downloads\bot-cpsl-review\imos_contacto_final.txt', 'w', encoding='utf-8') as f:
    f.write("DIRECTORIO DE CONTACTO DE IMOS (E25, E26, E27)\n")
    f.write("="*80 + "\n\n")
    
    f.write(f"Total IMOs: {len(imo_ids)}\n")
    f.write(f"Con correo: {con_correo}\n")
    f.write(f"Con teléfono (sin correo): {con_tel - con_correo}\n")
    f.write(f"Sin datos: {sin_nada}\n\n")
    
    f.write("--- CON CORREO ---\n")
    for imo_id, info in sorted(imo_info_from_reportes.items(), key=lambda x: x[1].get('correo', '') != '', reverse=True):
        if info['correo']:
            f.write(f"  DNI {imo_id} | {info['nombre']} | Email: {info['correo']} | Tel: {info['telefono']}\n")
    
    f.write("\n--- SOLO TELÉFONO ---\n")
    for imo_id, info in sorted(imo_info_from_reportes.items()):
        if not info['correo'] and info['telefono'] and info['telefono'] != 'nan':
            f.write(f"  DNI {imo_id} | {info['nombre']} | Tel: {info['telefono']}\n")
    
    f.write("\n--- SIN DATOS ---\n")
    for imo_id in sorted(imo_ids):
        if imo_id not in imo_info_from_reportes:
            f.write(f"  DNI {imo_id}\n")

print(f"\nReporte guardado en: imos_contacto_final.txt")
