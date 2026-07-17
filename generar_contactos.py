import pandas as pd
import sqlite3
import re

excel_path = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'
csv_path = r'C:\Users\josem\Downloads\Contactos_Google_E28.csv'
db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

print("Leyendo Excel...")
df = pd.read_excel(excel_path)
df_e28 = df[df['NombreEquipo'].str.contains('28', case=False, na=False)].copy()

print("Conectando a BD para buscar nombres de IMOs...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Cargar un diccionario de DNI -> Nombre del IMO
cursor.execute("SELECT identificacion, nombre, apellido FROM participantes WHERE identificacion IS NOT NULL")
imos_db = {str(row[0]).strip(): f"{row[1]} {row[2]}".strip().title() for row in cursor.fetchall()}
conn.close()

# Funcin para mapear DNI a Nombre
def get_imo_name(dni):
    dni_str = str(dni).strip()
    # Extraer el nombre si existe, sino, dejar el DNI
    return imos_db.get(dni_str, f"DNI: {dni_str}")

# Preparar las columnas para Google Contacts
gcontacts = pd.DataFrame()
gcontacts['Name'] = df_e28['NombreCompleto'].astype(str).str.title() + " " + df_e28['ApellidoCompleto'].astype(str).str.title()
gcontacts['Given Name'] = df_e28['NombreCompleto'].astype(str).str.title()
gcontacts['Family Name'] = df_e28['ApellidoCompleto'].astype(str).str.title()
gcontacts['Group Membership'] = 'Capítulo 1 - E28'
gcontacts['E-mail 1 - Type'] = 'Work'
gcontacts['E-mail 1 - Value'] = df_e28['Correo'].astype(str).str.lower().str.strip()
gcontacts['Phone 1 - Type'] = 'Mobile'

def format_phone(p):
    p = str(p).strip()
    p_clean = re.sub(r'\D', '', p)
    if len(p_clean) == 9 and p_clean.startswith('9'):
        return "+51 " + p_clean
    elif p_clean.startswith('51') and len(p_clean) >= 11:
        return "+" + p_clean
    return p_clean

gcontacts['Phone 1 - Value'] = df_e28['TelefonoMovil'].apply(format_phone)

# Aqu aplicamos el mapeo para que salga el nombre
nombres_imos = df_e28['IdentificacionIMO'].apply(get_imo_name)
gcontacts['Notes'] = "IMO: " + nombres_imos + " | CC: " + df_e28['Usuario Actual'].astype(str)

gcontacts.to_csv(csv_path, index=False, encoding='utf-8')
print(f"Archivo generado y mejorado en: {csv_path} con {len(gcontacts)} contactos.")
