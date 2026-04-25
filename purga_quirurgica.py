"""
PURGA QUIRURGICA DE DUPLICADOS - CREAR LIMA 🔱🛡️
Reglas de Fusión:
1. Agrupar por DNI (la llave maestra)
2. Para cada grupo, usar el nombre más completo (más caracteres)
3. Preservar datos más ricos de cada campo (no vacíos, no '—')
4. Participantes con CE (Carnet Extranjería) = identificador alfanumérico válido
5. Nombre 'oficial' = el de mayor longitud o el verificado por RENIEC
6. Guardar resultado sin duplicados en Master_Database.xlsx
"""
import pandas as pd
import os
import unicodedata
import re
from sync_cloud import conectar_sheets, SHEET_ID

def normalize(text):
    if not text or pd.isna(text): return ""
    s = str(text).strip().upper()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', s).strip()

def mejor_valor(*vals):
    """Retorna el valor más informativo (más largo, no vacío ni '—')."""
    candidates = [str(v).strip() for v in vals if v and str(v).strip() not in ('', '—', 'nan', 'NaN')]
    if not candidates: return "—"
    return max(candidates, key=len)

def fusionar_grupo(grupo):
    """Fusiona filas del mismo DNI en un único registro unificado."""
    merged = {}
    for col in grupo.columns:
        vals = grupo[col].tolist()
        if col in ('Nombres', 'Apellidos'):
            # Usar el nombre más largo verificado por RENIEC si existe
            reniec_col = 'RENIEC_Nombres' if col == 'Nombres' else 'RENIEC_Paterno'
            reniec_val = merged.get(reniec_col, '')
            merged[col] = mejor_valor(reniec_val, *vals)
        else:
            merged[col] = mejor_valor(*vals)
    return merged

MINERIA = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Mineria_DNIs.xlsx"

print("=" * 60)
print("🔱 PURGA QUIRURGICA CLOUD - BLINDAJE DE DATOS EN LA NUBE")
print("=" * 60)

# 1. Cargar Master desde Google Sheets
client = conectar_sheets()
if not client:
    print("❌ No se pudo conectar a Google Sheets.")
    exit()

try:
    sh = client.open_by_key(SHEET_ID)
    ws = sh.get_worksheet(0)
    data = ws.get_all_records()
    df = pd.DataFrame(data).fillna("—")
    print(f"\n📋 Master CLOUD cargado: {len(df)} registros")
except Exception as e:
    print(f"❌ Error cargando Sheets: {e}")
    exit()

# 3. Limpiar DNI
def clean_id(val):
    if not val or str(val).strip() in ('', '—', 'nan'): return ""
    s = str(val).strip().upper().replace('.0', '')
    try:
        if 'E+' in s: s = "{:.0f}".format(float(s))
    except: pass
    clean = re.sub(r'[^A-Z0-9]', '', s)
    return clean if len(clean) >= 7 else ""

df['DNI'] = df['DNI'].apply(clean_id)

# 4. Enriquecer con nombres RENIEC
if os.path.exists(MINERIA):
    dm = pd.read_excel(MINERIA, dtype=str).fillna("")
    dm = dm[dm['Estatus'].isin(['VERIFICADO', 'VERIFICADO_TABLA'])]
    dm['DNI'] = dm['DNI'].apply(clean_id)
    reniec_map = {}
    for _, r in dm.iterrows():
        dni = r['DNI']
        nombre_reniec = f"{r.get('RENIEC_Nombres','').strip()} {r.get('RENIEC_Paterno','').strip()} {r.get('RENIEC_Materno','').strip()}".strip()
        if dni and nombre_reniec:
            reniec_map[dni] = nombre_reniec
    print(f"🔍 {len(reniec_map)} identidades RENIEC disponibles para blindaje")
    
    # Aplicar nombre RENIEC si disponible
    def aplicar_reniec_nombre(row):
        dni = row['DNI']
        if dni in reniec_map:
            partes = reniec_map[dni].split()
            # Nombre = primeras palabras, apellidos = últimas 2
            if len(partes) >= 3:
                row['Nombres'] = " ".join(partes[:-2]).title()
                row['Apellidos'] = " ".join(partes[-2:]).title()
            elif len(partes) == 2:
                row['Nombres'] = partes[0].title()
                row['Apellidos'] = partes[1].title()
        return row
    
    df = df.apply(aplicar_reniec_nombre, axis=1)
    print("✅ Nombres RENIEC aplicados como referencia oficial")

# 5. Separar registros SIN DNI
df_sin_dni = df[df['DNI'] == ""].copy()
df_con_dni = df[df['DNI'] != ""].copy()
print(f"\n📊 Con DNI: {len(df_con_dni)} | Sin DNI: {len(df_sin_dni)}")

# 6. FUSIÓN POR DNI: Conservar el registro más completo
print("\n🔄 Fusionando duplicados por DNI...")
grupos = df_con_dni.groupby('DNI')
fusionados = []
total_grupos = len(grupos)
eliminados = 0

for dni, grupo in grupos:
    if len(grupo) == 1:
        fusionados.append(grupo.iloc[0].to_dict())
    else:
        eliminados += len(grupo) - 1
        merged = fusionar_grupo(grupo)
        fusionados.append(merged)

df_fusionado = pd.DataFrame(fusionados)
print(f"✅ Fusión completa: {eliminados} duplicados eliminados")
print(f"   Registros únicos por DNI: {len(df_fusionado)}")

# 7. Fusión de duplicados por NOMBRE (sin DNI o con DNI diferente)
print("\n🔄 Detectando duplicados por nombre normalizado...")
df_fusionado['_norm'] = (df_fusionado['Nombres'].fillna('') + " " + df_fusionado['Apellidos'].fillna('')).apply(normalize)
mask_dup_nombre = df_fusionado.duplicated(subset=['_norm'], keep=False) & (df_fusionado['_norm'] != "")
dup_nombres = df_fusionado[mask_dup_nombre]
print(f"   Duplicados por nombre detectados: {len(dup_nombres)}")

# Para duplicados por nombre, quedarse con el que tiene DNI más completo
df_final = df_fusionado.sort_values('DNI', ascending=False).drop_duplicates(subset=['_norm'], keep='first')
df_final = df_final.drop(columns=['_norm'])

# Agregar sin DNI (participantes sin documento registrado)
df_total = pd.concat([df_final, df_sin_dni], ignore_index=True)
print(f"\n📊 RESULTADO FINAL:")
print(f"   Total registros únicos: {len(df_total)}")
print(f"   Registros eliminados/fusionados: {len(df) - len(df_total)}")

# 8. Guardar Master blindado en la Nube
df_out = df_total.fillna("").astype(str)
ws.clear()
ws.update([df_out.columns.values.tolist()] + df_out.values.tolist())
print(f"\n🔱 Master en la nube actualizado y blindado: {len(df_total)} registros únicos")

# 9. Reporte de participantes CE (Carnet Extranjería)
ce = df_total[df_total['DNI'].apply(lambda x: bool(re.search(r'[A-Z]', str(x))) if x and x != '—' else False)]
if not ce.empty:
    print(f"\n🌍 Participantes con Carnet Extranjería: {len(ce)}")
    print(ce[['Nombres','Apellidos','DNI']].to_string(index=False))
else:
    print("\n📋 No se detectaron Carnets de Extranjería (documentos alfanuméricos) en el maestro.")

print("\n✅ PURGA COMPLETADA - BASE DE DATOS BLINDADA Y LISTA PARA LA GUERRA 🔱🛡️")
