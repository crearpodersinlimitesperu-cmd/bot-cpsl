import pandas as pd, sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

# 1. Revisar Auditoria.json (tiene datos de IMO: confirmados, NC, no interesa, devoluciones)
aud_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Auditoria.json"
if os.path.exists(aud_path):
    with open(aud_path, 'r', encoding='utf-8') as f:
        aud = json.load(f)
    print("=== AUDITORÍA IMO (resultado_llamadas.php) ===")
    print(f"Total registros: {len(aud)}")
    
    total_asignados = sum(r.get('Total_Asignados', 0) for r in aud)
    total_conf = sum(r.get('Confirmados', 0) for r in aud)
    total_nc = sum(r.get('NC', 0) for r in aud)
    total_no_interesa = sum(r.get('No_Interesa', 0) for r in aud)
    total_siguiente = sum(r.get('Siguiente', 0) for r in aud)
    total_por_conf = sum(r.get('Por_Confirmar', 0) for r in aud)
    total_devol = sum(r.get('Devolucion', 0) for r in aud)
    
    print(f"\n  Asignados:     {total_asignados}")
    print(f"  Confirmados:   {total_conf}")
    print(f"  NC:            {total_nc}")
    print(f"  No Interesa:   {total_no_interesa}")
    print(f"  Siguiente:     {total_siguiente}")
    print(f"  Por Confirmar: {total_por_conf}")
    print(f"  Devolución:    {total_devol}")
    
    # Por equipo C1
    print("\n--- C1 por equipo ---")
    c1_data = [r for r in aud if r.get('Capitulo') == 'C1']
    for eq in sorted(set(r['Equipo'] for r in c1_data)):
        eq_data = [r for r in c1_data if r['Equipo'] == eq]
        conf = sum(r.get('Confirmados', 0) for r in eq_data)
        ni = sum(r.get('No_Interesa', 0) for r in eq_data)
        dev = sum(r.get('Devolucion', 0) for r in eq_data)
        sig = sum(r.get('Siguiente', 0) for r in eq_data)
        nc = sum(r.get('NC', 0) for r in eq_data)
        pend = sum(r.get('Por_Confirmar', 0) for r in eq_data)
        print(f"  {eq}: Conf={conf} | NC={nc} | No_Interesa={ni} | Sig={sig} | Devol={dev} | Pend={pend}")

# 2. Revisar el Master con "Ident. Cambio Cupo"
master = pd.read_csv(r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Master_Participantes_Limpio.csv", dtype=str)
c1no = master[master['C1'] == 'NO']

# Cambios de cupo
cambios = c1no[c1no['Ident. Cambio Cupo'].notna() & (c1no['Ident. Cambio Cupo'] != '-') & (c1no['Ident. Cambio Cupo'].str.strip() != '')]
print(f"\n=== CAMBIOS DE CUPO en pendientes C1: {len(cambios)} ===")

# 3. Buscar resultado gestión en historial
hist_path = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Gestion_Llamadas.xlsx"
if os.path.exists(hist_path):
    df_g = pd.read_excel(hist_path, dtype=str)
    print(f"\n=== GESTIÓN LLAMADAS ===")
    print(f"Total: {len(df_g)}")
    print(f"Columnas: {list(df_g.columns)}")
    for col in df_g.columns:
        if any(x in col.upper() for x in ['RESULT', 'PRIMERA', 'ESTADO', 'GESTION']):
            print(f"\n{col}:")
            print(df_g[col].value_counts().head(15).to_string())
