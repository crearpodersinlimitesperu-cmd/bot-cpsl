import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')

# Revisar el CSV original
csv_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Prospectos_Pendientes_C1_Depurado_Campana.csv"
df = pd.read_csv(csv_path, dtype=str)
print("=== CSV PROSPECTOS ORIGINAL ===")
print(f"Columnas: {list(df.columns)}")
print(f"Total: {len(df)}")
print(f"\nTipos:")
if 'TIPO' in df.columns:
    print(df['TIPO'].value_counts().to_string())

# Revisar Master Limpio - columna 'Acciones' y cambio de cupo
master_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Master_Participantes_Limpio.csv"
df_m = pd.read_csv(master_path, dtype=str)
print(f"\n=== MASTER LIMPIO ===")
print(f"Columnas: {list(df_m.columns)}")

# Filtrar C1=NO
c1_no = df_m[df_m['C1'] == 'NO']
print(f"\nC1=NO en Master: {len(c1_no)}")

# Acciones
if 'Acciones' in df_m.columns:
    print(f"\nAcciones en C1=NO:")
    print(c1_no['Acciones'].value_counts().to_string())

# Ident. Cambio Cupo
if 'Ident. Cambio Cupo' in df_m.columns:
    cambios = c1_no[c1_no['Ident. Cambio Cupo'].notna() & (c1_no['Ident. Cambio Cupo'] != '-') & (c1_no['Ident. Cambio Cupo'] != '')]
    print(f"\nCon Cambio de Cupo (C1=NO): {len(cambios)}")
    if len(cambios) > 0:
        print(cambios[['Nombre', 'Apellido', 'Ident. Cambio Cupo', 'Tipo']].head(10).to_string())

# Revisar el CSV de campaña E28
try:
    camp_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\campana_e28_diana_joyce.csv"
    df_c = pd.read_csv(camp_path, dtype=str)
    print(f"\n=== CAMPAÑA E28 ===")
    print(f"Columnas: {list(df_c.columns)}")
    print(f"Total: {len(df_c)}")
    for col in df_c.columns:
        if any(x in col.upper() for x in ['ESTADO', 'TIPO', 'RESULT', 'GESTION']):
            print(f"\n{col}:")
            print(df_c[col].value_counts().head(10).to_string())
except:
    pass

# Revisar CSV fuente original de IMO (con más columnas)
try:
    import glob
    imo_files = glob.glob(r"C:\Users\josem\OneDrive*\**\participantes*.csv", recursive=True)
    for f in imo_files[:3]:
        print(f"\n=== {f} ===")
        df_i = pd.read_csv(f, dtype=str, nrows=5)
        print(f"Columnas: {list(df_i.columns)}")
except:
    pass
