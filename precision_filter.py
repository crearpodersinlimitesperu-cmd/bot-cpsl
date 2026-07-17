import pandas as pd
import os
import re
import dns.resolver

def check_mx(domain):
    # Common domains we trust blindly to save time
    trusted = ['gmail.com', 'hotmail.com', 'yahoo.com', 'yahoo.es', 'outlook.com', 'outlook.es', 'live.com', 'icloud.com']
    if domain in trusted:
        return True
    
    try:
        answers = dns.resolver.resolve(domain, 'MX')
        return len(answers) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
        return False
    except Exception:
        # If any other error occurs, maybe assume it's true to avoid false positive quarantine, 
        # but since we want hyper-precision, let's log it or assume false? Let's assume false to be 100% safe.
        return False

def fix_typos(email):
    email = email.strip().lower()
    
    # Common mistakes
    email = email.replace('@gmil.com', '@gmail.com')
    email = email.replace('@gamil.com', '@gmail.com')
    email = email.replace('@gmail.con', '@gmail.com')
    email = email.replace('@gmail.com.com', '@gmail.com')
    email = email.replace('@hitmail.com', '@hotmail.com')
    email = email.replace('@hotmai.com', '@hotmail.com')
    email = email.replace('@homail.com', '@hotmail.com')
    
    return email

def main():
    aptos_path = r"c:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv"
    if not os.path.exists(aptos_path):
        print("Falta archivo de aptos principal.")
        return

    df = pd.read_csv(aptos_path, encoding='utf-8-sig')
    
    # Filter E26 & E27
    df_filtered = df[df['NombreEquipo'].isin(['EQUIPO 26', 'EQUIPO 27'])].copy()
    initial_e26_27 = len(df_filtered)
    
    valid_rows = []
    cuarentena = []
    
    email_regex = re.compile(r'^\S+@\S+\.\S+$')
    
    print(f"Total Participantes E26 y E27 a procesar: {initial_e26_27}")
    
    for idx, row in df_filtered.iterrows():
        correo_orig = str(row.get('Correo', '')).strip().lower()
        if not correo_orig or correo_orig == 'nan':
            continue
            
        correo_fixed = fix_typos(correo_orig)
        row['Correo'] = correo_fixed
        
        if not email_regex.match(correo_fixed):
            row['Motivo_Cuarentena'] = 'Sintaxis inválida'
            cuarentena.append(row)
            continue
            
        domain = correo_fixed.split('@')[1]
        
        if check_mx(domain):
            valid_rows.append(row)
        else:
            row['Motivo_Cuarentena'] = f'Dominio muerto/inactivo ({domain})'
            cuarentena.append(row)

    df_validos = pd.DataFrame(valid_rows)
    df_cuarentena = pd.DataFrame(cuarentena)
    
    out_valid = r"c:\Users\josem\Downloads\bot-cpsl-review\Aptos_E26_E27_ZeroBounces.csv"
    out_cuarentena = r"c:\Users\josem\Downloads\bot-cpsl-review\Cuarentena_Dominios_Invalidos.csv"
    
    df_validos.to_csv(out_valid, index=False, encoding='utf-8-sig')
    if len(df_cuarentena) > 0:
        df_cuarentena.to_csv(out_cuarentena, index=False, encoding='utf-8-sig')
        
    print(f"--- PROTOCOLO DE PRECISIÓN TERMINADO ---")
    print(f"Total E26/E27 inicial: {initial_e26_27}")
    print(f"Correos reparados y validados DNS: {len(df_validos)}")
    print(f"Dominios en cuarentena (inexistentes): {len(df_cuarentena)}")

if __name__ == "__main__":
    main()
