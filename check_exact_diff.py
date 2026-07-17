import pandas as pd
import os
import re

def main():
    aptos_path = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana.csv"
    rebotes_path = r"c:\Users\josem\Downloads\Rebotes_12_Meses.csv"
    
    if not os.path.exists(aptos_path):
        print("Falta archivo de aptos principal.")
        return
        
    df_aptos = pd.read_csv(aptos_path, encoding='utf-8-sig')
    
    # Check what 539 were first valid
    email_regex = re.compile(r'^\S+@\S+\.\S+$')
    bounced_emails_local = set()
    
    file_sonic = r"c:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_SONIC.csv"
    if os.path.exists(file_sonic):
        try:
            df_sonic = pd.read_csv(file_sonic, on_bad_lines='skip')
            if 'Email' in df_sonic.columns:
                for e in df_sonic['Email'].dropna():
                    bounced_emails_local.add(str(e).strip().lower())
        except: pass

    file_total = r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv"
    if os.path.exists(file_total):
        try:
            df_total = pd.read_csv(file_total, on_bad_lines='skip')
            if 'email' in df_total.columns:
                for e in df_total['email'].dropna():
                    bounced_emails_local.add(str(e).strip().lower())
        except: pass

    valid_emails = []
    for idx, row in df_aptos.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        if not correo or correo == 'nan' or correo == 'no tiene' or correo == '':
            continue
        if not email_regex.match(correo):
            continue
        if correo in bounced_emails_local:
            continue
        valid_emails.append(row)
        
    df_539 = pd.DataFrame(valid_emails)
    
    # Load 12 month bounces
    bounced_12m = set()
    if os.path.exists(rebotes_path):
        df_r = pd.read_csv(rebotes_path)
        for e in df_r['Email'].dropna():
            bounced_12m.add(str(e).strip().lower())
            
    excluidos_exactos = []
    
    for idx, row in df_539.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        if correo in bounced_12m:
            excluidos_exactos.append({
                "Nombre": str(row.get('NombreCompleto', '')) + " " + str(row.get('ApellidoCompleto', '')),
                "Correo": correo,
                "Coordinador": row.get('Usuario Actual', row.get('Usuario Registro', ''))
            })
            
    print(f"Total Exactos Encontrados que fueron excluidos: {len(excluidos_exactos)}")
    for e in excluidos_exactos:
        print(f"- {e['Nombre'].strip()} | Correo: {e['Correo']} | Coord: {e['Coordinador']}")

if __name__ == "__main__":
    main()
