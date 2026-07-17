import imaplib
import email
from email.header import decode_header
import re
import os
import sys
import pandas as pd
import unicodedata

sys.stdout.reconfigure(encoding='utf-8')

EMAIL_USER = "crearpodersinlimitesperu@gmail.com"
EMAIL_PASS = "bgsl xjus xsmn pzqd"

def normalize_name(name):
    if not isinstance(name, str): return ""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8").lower()
    return re.sub(r'[^a-z0-9]', '', name)

def extract_emails(text):
    return re.findall(r'[\w\.-]+@[\w\.-]+', str(text).lower())

def buscar_correos_criticos():
    print("--- CONECTANDO A GMAIL PARA BUSCAR DEVOLUCIONES Y REBOTES ---")
    
    blacklisted_emails = set()
    blacklisted_names = set()
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select('"[Gmail]/Todos"')
        
        keywords = ["devolucion", "reembolso", "cancelar", "desistir", "estafa", "denuncia", "profeco", "indecopi"]
        
        casos_encontrados = 0
        for kw in keywords:
            # We will search the body/subject
            status, messages = mail.search(None, f'(OR SUBJECT "{kw}" BODY "{kw}")')
            if status == "OK" and messages[0]:
                ids = messages[0].split()
                casos_encontrados += len(ids)
                for num in ids:
                    try:
                        res, data = mail.fetch(num, "(RFC822)")
                        if res != "OK": continue
                        
                        msg = email.message_from_bytes(data[0][1])
                        
                        # Extract FROM
                        from_header = str(msg.get("From", ""))
                        extracted = extract_emails(from_header)
                        for e in extracted:
                            if "crearpodersinlimites" not in e:
                                blacklisted_emails.add(e)
                                
                        # Extract Name from FROM
                        name_match = re.match(r'^(.*?)\s*<', from_header)
                        if name_match:
                            n = name_match.group(1).replace('"', '').strip()
                            if len(n) > 5:
                                blacklisted_names.add(normalize_name(n))
                                
                        # Body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain":
                                    body += part.get_payload(decode=True).decode(errors='ignore')
                        else:
                            body = msg.get_payload(decode=True).decode(errors='ignore')
                            
                        # Extract any emails mentioned in the body of a refund request
                        body_emails = extract_emails(body)
                        for be in body_emails:
                            if "crearpodersinlimites" not in be:
                                blacklisted_emails.add(be)
                    except Exception:
                        pass

        print(f"Búsqueda finalizada. Emails únicos bloqueados: {len(blacklisted_emails)}")
        print(f"Nombres únicos bloqueados por devoluciones: {len(blacklisted_names)}")
        mail.logout()
        return blacklisted_emails, blacklisted_names
    except Exception as e:
        print(f"Error IMAP: {e}")
        return set(), set()

def main():
    b_emails, b_names = buscar_correos_criticos()
    
    if not b_emails and not b_names:
        print("No se encontraron registros de exclusión en los correos.")
        return
        
    aptos_path = r"c:\Users\josem\Downloads\bot-cpsl-review\Aptos_E26_E27_ZeroBounces.csv"
    if not os.path.exists(aptos_path):
        print("Archivo aptos no encontrado.")
        return
        
    df_aptos = pd.read_csv(aptos_path, encoding='utf-8-sig')
    initial_len = len(df_aptos)
    
    valid_rows = []
    excluidos = []
    
    for idx, row in df_aptos.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        nombre = str(row.get('NombreCompleto', '')).strip()
        apellido = str(row.get('ApellidoCompleto', '')).strip()
        
        n_norm1 = normalize_name(nombre + " " + apellido)
        n_norm2 = normalize_name(nombre)
        n_norm3 = normalize_name(apellido)
        
        is_bad = False
        if correo in b_emails: is_bad = True
        if n_norm1 and n_norm1 in b_names: is_bad = True
        
        if is_bad:
            excluidos.append(row)
        else:
            valid_rows.append(row)
            
    df_v = pd.DataFrame(valid_rows)
    df_v.to_csv(aptos_path, index=False, encoding='utf-8-sig')
    
    print("--- RESULTADO CRUCE CON DEVOLUCIONES ---")
    print(f"Total antes: {initial_len}")
    print(f"Excluidos por devolucion/rebote en inbox: {len(excluidos)}")
    print(f"Lista definitiva actual: {len(df_v)}")
    
    if excluidos:
        print("\nExcluidos:")
        for r in excluidos:
            print(f"- {r.get('NombreCompleto')} {r.get('ApellidoCompleto')} ({r.get('Correo')})")

if __name__ == "__main__":
    main()
