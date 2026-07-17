import pandas as pd
import re
import requests
import urllib.parse

# Rutas de archivos
CSV_PATH = r'C:\Users\josem\Downloads\participantes_2026-05-25.csv'
EXCEL_PATH = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'

# Configuración MacroDroid (ya usada en otros scripts)
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

# Mapeo de username a nombre completo del coordinador (según datos previos)
COORD_MAP = {
    "jmarin": "Joyce Pamela Martínez Suárez",
    "dmoscoso": "Diana Yesenia Moscoso Robles",
    "jsanchez": "José Sánchez"
}

# 1. Cargar CSV de participantes (contiene al menos columnas: NombreCompleto, ApellidoCompleto, TelefonoMovil, IdentificacionIMO)
print("Cargando CSV de participantes...")
# Use a tolerant CSV parser to skip malformed lines
participants = pd.read_csv(CSV_PATH, engine='python', on_bad_lines='skip', encoding='utf-8')

# Cargando Excel de asignaciones
print("Cargando Excel de asignaciones...")
assignments = pd.read_excel(EXCEL_PATH)

# Filtrar solo los del Equipo 28 (asumiendo que la columna 'NombreEquipo' contiene el número del equipo)
assign_e28 = assignments[assignments['NombreEquipo'].astype(str).str.contains('28', case=False, na=False)].copy()
assign_e28 = assign_e28[['IdentificacionIMO', 'Usuario Actual']].drop_duplicates()
assign_e28['Usuario Actual'] = assign_e28['Usuario Actual'].astype(str).str.strip().str.lower()

# Normalizar nombre de columna de DNI en el CSV (puede variar)
# Buscamos columnas que contengan la palabra 'ident' (ignora acentos y mayúsculas)
ident_cols = [col for col in participants.columns if 'ident' in col.lower()]
if ident_cols:
    participants = participants.rename(columns={ident_cols[0]: 'IdentificacionIMO'})
else:
    raise KeyError('No se encontró columna de IdentificacionIMO en el CSV')

# Normalizar columna de teléfono (puede ser 'Teléfono' o similar)
phone_cols = [col for col in participants.columns if 'tel' in col.lower()]
if phone_cols:
    participants = participants.rename(columns={phone_cols[0]: 'TelefonoMovil'})
else:
    raise KeyError('No se encontró columna de Teléfono en el CSV')

# Normalizar nombre y apellido
name_col = next((col for col in participants.columns if col.lower() == 'nombre'), None)
surname_col = next((col for col in participants.columns if col.lower() == 'apellido'), None)
if name_col and surname_col:
    participants = participants.rename(columns={name_col: 'NombreCompleto', surname_col: 'ApellidoCompleto'})
else:
    raise KeyError('No se encontró columna de Nombre/Apellido en el CSV')

# Unir datos de participantes con su coordinador
merged = participants.merge(assign_e28, on='IdentificacionIMO', how='inner')
print(f"Participantes del E28 encontrados: {len(merged)}")

# 5. Función para formatear teléfono móvil a formato internacional peruano (+51)
def format_phone(p):
    p = str(p).strip()
    p_clean = re.sub(r'\D', '', p)
    # Si ya tiene el código 51 y tiene al menos 11 dígitos, lo dejamos
    if p_clean.startswith('51') and len(p_clean) >= 11:
        return "+" + p_clean
    # Si tiene 9 dígitos (formato peruano típico) lo precedemos con +51
    if len(p_clean) == 9:
        return "+51 " + p_clean
    # Caso fallback: regresar tal cual (puede que sea inválido)
    return p_clean

# 6. Enviar SMS a cada participante
sent_count = 0
for idx, row in merged.iterrows():
    nombre = str(row['NombreCompleto']).title() + " " + str(row['ApellidoCompleto']).title()
    telefono_raw = row.get('TelefonoMovil') or row.get('Tel_imo') or row.get('telefono')
    if pd.isna(telefono_raw):
        print(f" -> {nombre} no tiene número de teléfono registrado, se omite.")
        continue
    telefono = format_phone(telefono_raw)
    if not telefono.startswith('+51'):
        print(f" -> {nombre} tiene un número de teléfono inesperado ({telefono_raw}), se omite.")
        continue
    # Determinar coordinador
    username = row['Usuario Actual']
    coordinador = COORD_MAP.get(username, username)
    # Texto del SMS
    sms_text = f"Hola {nombre}, tu coordinador es {coordinador}. Por favor guarda su número de contacto."
    sms_encoded = urllib.parse.quote(sms_text)
    url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}?numero={telefono}&mensaje={sms_encoded}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            print(f" -> SMS enviado a {telefono} (Coordinador: {coordinador})")
            sent_count += 1
        else:
            print(f" -> Falló envío a {telefono}: HTTP {resp.status_code}")
    except Exception as e:
        print(f" -> Error enviando a {telefono}: {e}")

print(f"\nResumen: se enviaron {sent_count} SMS a participantes del Equipo 28.")
