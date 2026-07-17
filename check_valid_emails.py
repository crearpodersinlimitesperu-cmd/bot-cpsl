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
    invalid_format = []
    bounced = []
    missing_email = []
    
    for idx, row in df_aptos.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        
        if not correo or correo == 'nan' or correo == 'no tiene' or correo == '':
            missing_email.append(row)
            continue
            
        if not email_regex.match(correo):
            invalid_format.append(row)
            continue
            
        if correo in bounced_emails:
            bounced.append(row)
            continue
            
        valid_emails.append(row)

    print(f"--- Análisis de Correos de los {total_aptos} Aptos ---")
    print(f"Correos válidos y listos: {len(valid_emails)}")
    print(f"Sin correo registrado o vacío: {len(missing_email)}")
    print(f"Formato de correo inválido: {len(invalid_format)}")
    print(f"Correos en lista negra (rebotes comprobados): {len(bounced)}")

if __name__ == "__main__":
    main()
