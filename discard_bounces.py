import pandas as pd
import os
import re

def main():
    aptos_path = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana.csv"
    if not os.path.exists(aptos_path):
        print(f"Error: {aptos_path} not found.")
        return
        
    df_aptos = pd.read_csv(aptos_path, encoding='utf-8-sig')
    total_aptos = len(df_aptos)
    
    # 1. Check valid format and not empty
    email_regex = re.compile(r'^\S+@\S+\.\S+$')
    
    # Gather blacklisted emails
    bounced_emails = set()
    
    file_sonic = r"c:\Users\josem\Downloads\bot-cpsl-review\BLACK_LIST_REBOTES_SONIC.csv"
    if os.path.exists(file_sonic):
        try:
            df_sonic = pd.read_csv(file_sonic, on_bad_lines='skip')
            if 'Email' in df_sonic.columns:
                for e in df_sonic['Email'].dropna():
                    bounced_emails.add(str(e).strip().lower())
        except:
            pass

    file_total = r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv"
    if os.path.exists(file_total):
        try:
            df_total = pd.read_csv(file_total, on_bad_lines='skip')
            if 'email' in df_total.columns:
                for e in df_total['email'].dropna():
                    bounced_emails.add(str(e).strip().lower())
        except:
            pass

    valid_emails = []
    
    for idx, row in df_aptos.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        
        if not correo or correo == 'nan' or correo == 'no tiene' or correo == '':
            continue
            
        if not email_regex.match(correo):
            continue
            
        if correo in bounced_emails:
            continue
            
        valid_emails.append(row)

    df_validos = pd.DataFrame(valid_emails)
    out_file = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana_Final.csv"
    df_validos.to_csv(out_file, index=False, encoding='utf-8-sig')
    
    print(f"Descarte completado.")
    print(f"Total originales: {total_aptos}")
    print(f"Total filtrados (solo aptos con correos válidos): {len(df_validos)}")
    print(f"Archivo guardado en: {out_file}")

if __name__ == "__main__":
    main()
