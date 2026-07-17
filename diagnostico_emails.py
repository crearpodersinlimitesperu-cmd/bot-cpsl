import sqlite3, sys, os
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect('torre_control.db')

# 1. ¿Tienen email los participantes?
print("=== EMAILS EN DB ===")
cols = [c[1] for c in conn.execute("PRAGMA table_info(participantes)").fetchall()]
email_cols = [c for c in cols if 'mail' in c.lower() or 'correo' in c.lower() or 'email' in c.lower()]
print(f"Columnas email: {email_cols}")

# 2. Verificar si hay emails
for col in email_cols:
    con_email = conn.execute(f"SELECT COUNT(*) FROM participantes WHERE {col} IS NOT NULL AND {col} != '' AND {col} != 'nan'").fetchone()[0]
    print(f"  PX con {col}: {con_email}")

# 3. Rezagados C1 reales con email
print("\n=== REZAGADOS C1 REALES ===")
rez = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI'").fetchone()[0]
print(f"Total pendientes reales C1: {rez}")

# 4. IMOs únicos de pendientes
imos = conn.execute("""
    SELECT DISTINCT imo, tel_imo FROM participantes 
    WHERE c1='NO' AND es_pendiente_real='SI' AND imo IS NOT NULL AND imo != '' AND imo != 'nan'
""").fetchall()
print(f"IMOs únicos de pendientes: {len(imos)}")

# 5. Datos de muestra
print("\n=== MUESTRA PENDIENTES C1 ===")
for r in conn.execute("""
    SELECT nombre, apellido, nombre_preferido, telefono, equipo, cc_nombre, imo, resultado_gestion
    FROM participantes WHERE c1='NO' AND es_pendiente_real='SI' LIMIT 5
"""):
    print(f"  {r[0]} {r[1]} | Pref: {r[2]} | Eq: {r[4]} | CC: {r[5]} | IMO: {r[6]} | Gest: {r[7]}")

# 6. ¿Hay columna de email en Master?
import pandas as pd
master = pd.read_csv(r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Master_Participantes_Limpio.csv", dtype=str, nrows=5)
email_master = [c for c in master.columns if 'mail' in c.lower() or 'correo' in c.lower() or 'email' in c.lower()]
print(f"\nColumnas email en Master CSV: {email_master}")

# 7. Buscar en los CSVs de IMO (participantes originales)
import glob
for f in glob.glob(r"C:\Users\josem\OneDrive*\**\participantes*.csv", recursive=True)[:1]:
    df_imo = pd.read_csv(f, dtype=str, nrows=3)
    email_imo = [c for c in df_imo.columns if 'mail' in c.lower() or 'correo' in c.lower() or 'email' in c.lower()]
    print(f"Columnas email en IMO CSV: {email_imo}")
    if email_imo:
        print(df_imo[email_imo].head().to_string())

# 8. Revisar .env de torre control
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            if 'GMAIL' in line.upper() or 'MAIL' in line.upper() or 'CORREO' in line.upper():
                key = line.split('=')[0].strip()
                print(f"\n.env tiene: {key}")

# 9. Verificar IMO emails - buscar en archivos de asistencia
for f in glob.glob(r"C:\Users\josem\OneDrive*\**\ASISTENCIA*.xlsx", recursive=True)[:1]:
    print(f"\nBuscando emails en: {os.path.basename(f)}")
    try:
        xl = pd.ExcelFile(f)
        df_a = xl.parse(xl.sheet_names[0], dtype=str, nrows=3)
        email_a = [c for c in df_a.columns if 'mail' in c.lower() or 'correo' in c.lower() or 'email' in c.lower()]
        print(f"  Columnas email: {email_a}")
    except: pass

conn.close()
