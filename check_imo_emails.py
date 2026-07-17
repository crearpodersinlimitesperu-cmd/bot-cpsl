import sqlite3, sys, re
sys.stdout.reconfigure(encoding='utf-8')
import pandas as pd

conn = sqlite3.connect('torre_control.db')

# IMOs con teléfono
imos = conn.execute("""
    SELECT DISTINCT imo, tel_imo FROM participantes 
    WHERE c1='NO' AND es_pendiente_real='SI' AND imo IS NOT NULL AND imo != '' AND imo != 'nan'
    AND tel_imo IS NOT NULL AND tel_imo != '' AND tel_imo != 'nan'
""").fetchall()
print(f"IMOs con teléfono propio: {len(imos)}")

# Cruzar con contacts
contacts_path = r"C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv"
df = pd.read_csv(contacts_path, dtype=str)

email_por_tel = {}
for _, row in df.iterrows():
    email = str(row.get('E-mail 1 - Value', '')).strip().lower()
    if not email or '@' not in email or email == 'nan':
        continue
    phone = re.sub(r'[^\d]', '', str(row.get('Phone 1 - Value', '')))
    if phone.startswith('51') and len(phone) > 9:
        phone = phone[2:]
    if phone and len(phone) >= 9:
        email_por_tel[phone] = email

# Buscar IMOs por teléfono
encontrados = 0
for imo_nombre, tel_imo in imos:
    tel = re.sub(r'[^\d]', '', str(tel_imo))
    if tel.startswith('51') and len(tel) > 9:
        tel = tel[2:]
    if tel in email_por_tel:
        encontrados += 1

print(f"IMOs con email encontrado por teléfono: {encontrados}")
conn.close()
