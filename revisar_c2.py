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

def load_pasted():
    with open(r'c:\Users\josem\Downloads\bot-cpsl-review\asignaciones_c2_pasted.txt', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    data = []
    for line in lines:
        parts = line.strip().split('\t')
        if len(parts) >= 8:
            usr = parts[0]
            eq = parts[1]
            asist = parts[2]
            dni = parts[3]
            nombre = parts[4]
            apell = parts[5]
            tel = parts[6]
            correo = parts[7]
            data.append({
                'UsuarioSeg': usr,
                'Equipo': eq,
                'Asistencia': asist,
                'DNI': dni,
                'Nombres': nombre,
                'Apellidos': apell,
                'NombreCompleto': f"{nombre} {apell}",
                'Tel': tel,
                'Correo': correo
            })
    return pd.DataFrame(data)

def load_blacklists():
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

def load_aliados():
    c2_dir = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2"
    c1_dir = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"
    
    def cargar_dir(directory, label):
        dfs = []
        if os.path.exists(directory):
            for file in os.listdir(directory):
                if file.endswith('.xlsx') and not file.startswith('~'):
                    try:
                        df = pd.read_excel(os.path.join(directory, file))
                        df['Origen'] = label
                        dfs.append(df)
                    except:
                        pass
        return dfs
        
    dfs = cargar_dir(c1_dir, 'C1') + cargar_dir(c2_dir, 'C2')
    
    if dfs:
        df_aliados = pd.concat(dfs, ignore_index=True)
        col_nombres = next((c for c in df_aliados.columns if 'NOMBRES' in str(c).upper()), None)
        col_apellidos = next((c for c in df_aliados.columns if 'APELLIDOS' in str(c).upper()), None)
        if col_nombres and col_apellidos:
            df_aliados['key'] = df_aliados.apply(lambda r: norm(str(r.get(col_nombres,'')) + ' ' + str(r.get(col_apellidos,''))), axis=1)
        else:
            df_aliados['key'] = ''
        return df_aliados
    return pd.DataFrame(columns=['key', 'STATUS', 'OBSERVACIONES', 'Origen'])

def main():
    df_pasted = load_pasted()
    df_pasted['key'] = df_pasted['NombreCompleto'].apply(norm)
    
    print(f"Total registros cargados del texto: {len(df_pasted)}")
    
    df_dj = df_pasted[df_pasted['UsuarioSeg'].isin(['dmoscoso', 'jmarin'])].copy()
    print(f"Registros de Diana y Joyce: {len(df_dj)}")
    
    blacklist = load_blacklists()
    df_aliados = load_aliados()
    
    aptos = []
    descartados = []
    
    for _, row in df_dj.iterrows():
        key = row['key']
        motivo = ""
        
        # Blacklist
        if key in blacklist:
            motivo = "Lista Negra (Devolución/Desertor C1)"
            
        # Aliados C1 y C2
        aliado_match = df_aliados[df_aliados['key'] == key]
        if not aliado_match.empty:
            for idx, al_row in aliado_match.iterrows():
                status = str(al_row.get('STATUS', '')).upper()
                obs = str(al_row.get('OBSERVACIONES', '')).upper()
                origen = al_row.get('Origen', '')
                
                cond_negativas = ['SENTO EN C2', 'SENTO C2', 'ABONO', 'ACUERDO', 'PARCIAL', 'NO INTERESADO', 'NO LE INTERESA', 'DEVOLUCION', 'PASO A']
                for cond in cond_negativas:
                    if cond in status or cond in obs:
                        motivo = f"Aliados {origen}: STATUS={status} | OBS={obs}"
                        break
                        
                # Si es desertor, solo lo descartamos si es de C1 o general, NO si es de C2
                if 'DESERTOR' in status or 'DESERTOR' in obs:
                    if origen != 'C2':
                        motivo = f"Aliados {origen}: STATUS={status} | OBS={obs} (Desertor)"
                
                if motivo:
                    break
        
        if motivo:
            row['MotivoDescarte'] = motivo
            descartados.append(row)
        else:
            row['MotivoDescarte'] = "APTO"
            aptos.append(row)
            
    df_aptos = pd.DataFrame(aptos)
    df_descartados = pd.DataFrame(descartados)
    
    print(f"\nAptos finales para C2: {len(df_aptos)}")
    print(f"Descartados: {len(df_descartados)}")
    
    if len(df_descartados) > 0:
        print("\nEjemplos de descartes:")
        for _, r in df_descartados.head(10).iterrows():
            print(f"- {r['NombreCompleto']} -> {r['MotivoDescarte']}")
            
    md_lines = ["# Revisión de Asignaciones C2 (Diana y Joyce)"]
    md_lines.append(f"\nSe revisaron **{len(df_dj)}** registros de Diana y Joyce.")
    md_lines.append(f"Quedaron **{len(df_aptos)}** participantes APTOS para C2.")
    md_lines.append(f"Se descartaron **{len(df_descartados)}** participantes (por abono de C2, ya se sentaron en C2, no interesados, devoluciones).\n")
    md_lines.append("*Nota: Los Desertores de C2 han sido considerados APTOS (rezagados que retoman).*")
    
    md_lines.append("\n## Participantes APTOS")
    md_lines.append("| Equipo | DNI | Nombre Completo | Teléfono | Correo |")
    md_lines.append("|---|---|---|---|---|")
    for _, r in df_aptos.iterrows():
        md_lines.append(f"| {r['Equipo']} | {r['DNI']} | {r['NombreCompleto']} | {r['Tel']} | {r['Correo']} |")
        
    md_lines.append("\n## Participantes DESCARTADOS")
    md_lines.append("| Equipo | DNI | Nombre Completo | Motivo |")
    md_lines.append("|---|---|---|---|")
    for _, r in df_descartados.iterrows():
        md_lines.append(f"| {r['Equipo']} | {r['DNI']} | {r['NombreCompleto']} | {r['MotivoDescarte']} |")
        
    with open(r'c:\Users\josem\Downloads\bot-cpsl-review\reporte_aptos_c2.md', 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))
        
    print("\nReporte generado: reporte_aptos_c2.md")

if __name__ == "__main__":
    main()
