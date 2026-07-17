import sqlite3
import pandas as pd
import os
import re
import unicodedata

def normalize_name(name):
    if not isinstance(name, str): return ""
    name = unicodedata.normalize('NFD', name).encode('ascii', 'ignore').decode("utf-8").lower()
    return re.sub(r'[^a-z0-9]', '', name)

def main():
    aptos_path = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana_Final.csv"
    if not os.path.exists(aptos_path):
        print("Falta archivo de aptos principal.")
        return

    df_aptos = pd.read_csv(aptos_path, encoding='utf-8-sig')
    initial_len = len(df_aptos)
    
    blacklisted_emails = set()
    blacklisted_phones = set()
    blacklisted_names = set()

    # 1. TORRE CONTROL DB
    db_torre = r"c:\Users\josem\Downloads\bot-cpsl-review\torre_control.db"
    if os.path.exists(db_torre):
        conn = sqlite3.connect(db_torre)
        # Buscar en desertores
        try:
            df_des = pd.read_sql("SELECT nombre FROM desertores", conn)
            for n in df_des['nombre'].dropna():
                blacklisted_names.add(normalize_name(n))
        except: pass
        
        # Buscar en historial_interacciones
        try:
            df_hi = pd.read_sql("SELECT email, tipo_interaccion FROM historial_interacciones", conn)
            for _, row in df_hi.iterrows():
                tipo = str(row.get('tipo_interaccion', '')).upper()
                if 'REBOTE' in tipo or 'FALLO' in tipo or 'ERROR' in tipo:
                    e = str(row.get('email', '')).strip().lower()
                    if '@' in e: blacklisted_emails.add(e)
        except: pass
        conn.close()

    # 2. PATRONES FORENSES V3 DB
    db_patrones = r"c:\Users\josem\Downloads\bot-cpsl-review\patrones_forenses_v3.db"
    if os.path.exists(db_patrones):
        conn = sqlite3.connect(db_patrones)
        try:
            df_hi2 = pd.read_sql("SELECT email, tipo_interaccion FROM historial_interacciones", conn)
            for _, row in df_hi2.iterrows():
                tipo = str(row.get('tipo_interaccion', '')).upper()
                if 'REBOTE' in tipo or 'FALLO' in tipo or 'ERROR' in tipo:
                    e = str(row.get('email', '')).strip().lower()
                    if '@' in e: blacklisted_emails.add(e)
        except: pass
        conn.close()

    # 3. EXTRA CSVs
    csvs = [
        r"c:\Users\josem\Downloads\bot-cpsl-review\REPORTE_REBOTES_SISTEMA_CREAR.xlsx",
        r"c:\Users\josem\Downloads\bot-cpsl-review\alertas_inconsistencias.csv",
        r"c:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\BLACK_LIST_REBOTES.csv",
        r"c:\Users\josem\Downloads\bot-cpsl-review\auditoria_desertores_total.csv"
    ]
    for c in csvs:
        if os.path.exists(c):
            try:
                if c.endswith('.csv'): df_c = pd.read_csv(c, on_bad_lines='skip')
                else: df_c = pd.read_excel(c)
                
                # Check email
                for e_col in [col for col in df_c.columns if 'mail' in col.lower() or 'correo' in col.lower()]:
                    for e in df_c[e_col].dropna():
                        e_str = str(e).strip().lower()
                        if '@' in e_str: blacklisted_emails.add(e_str)
                        
                # Check phone
                for t_col in [col for col in df_c.columns if 'tel' in col.lower() or 'cel' in col.lower()]:
                    for t in df_c[t_col].dropna():
                        v_norm = re.sub(r'[^\d]', '', str(t))
                        if v_norm.startswith('51') and len(v_norm)>9: v_norm = v_norm[2:]
                        if len(v_norm)>5: blacklisted_phones.add(v_norm)

                # Check name
                for n_col in [col for col in df_c.columns if 'nombre' in col.lower()]:
                    for _, row in df_c.iterrows():
                        nombre_val = str(row.get(n_col, ''))
                        apellido_val = ""
                        # try find apellido
                        for a_col in [col for col in df_c.columns if 'apellido' in col.lower()]:
                            apellido_val = str(row.get(a_col, ''))
                            break
                        full_name = (nombre_val + " " + apellido_val).strip()
                        blacklisted_names.add(normalize_name(full_name))
            except: pass

    # --- FILTER FINAL LIST ---
    excluidos_deep = []
    valid_rows = []
    
    for idx, row in df_aptos.iterrows():
        correo = str(row.get('Correo', '')).strip().lower()
        
        telefono = ""
        for key in row.keys():
            if 'telefon' in key.lower() or 'celular' in key.lower():
                telefono = str(row[key])
                break
                
        phone_norm = re.sub(r'[^\d]', '', telefono)
        if phone_norm.startswith('51') and len(phone_norm) > 9: phone_norm = phone_norm[2:]
        
        nombre = str(row.get('NombreCompleto', ''))
        apellido = str(row.get('ApellidoCompleto', ''))
        
        # O combinar ambos si no hay ApellidoCompleto
        if not nombre and 'Nombre' in row: nombre = str(row['Nombre'])
        
        n_norm = normalize_name(nombre + " " + apellido)
        if not n_norm: n_norm = normalize_name(nombre)
        
        is_blacklisted = False
        reason = []
        
        if correo and correo in blacklisted_emails:
            is_blacklisted = True; reason.append('correo')
        if phone_norm and phone_norm in blacklisted_phones:
            is_blacklisted = True; reason.append('telefono')
        if n_norm and n_norm in blacklisted_names:
            is_blacklisted = True; reason.append('nombre')
                    
        if is_blacklisted:
            row['Deep_Reason'] = ", ".join(reason)
            excluidos_deep.append(row)
        else:
            valid_rows.append(row)

    df_validos = pd.DataFrame(valid_rows)
    df_excluidos = pd.DataFrame(excluidos_deep)
    
    out_file = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana_Final.csv"
    
    # Save but drop Deep_Reason if it got there
    df_v_save = df_validos.drop(columns=['Deep_Reason'], errors='ignore')
    df_v_save.to_csv(out_file, index=False, encoding='utf-8-sig')
    
    if len(df_excluidos) > 0:
        df_excluidos.to_csv(r"c:\Users\josem\Downloads\Excluidos_Profundos.csv", index=False, encoding='utf-8-sig')
    
    print(f"--- RESULTADOS AUDITORÍA PROFUNDA ---")
    print(f"Listas Negras -> Correos: {len(blacklisted_emails)} | Telefonos: {len(blacklisted_phones)} | Nombres: {len(blacklisted_names)}")
    print(f"Total en lista final antes: {initial_len}")
    print(f"Excluidos en este barrido: {len(excluidos_deep)}")
    print(f"Total lista final definitiva: {len(df_validos)}")

if __name__ == "__main__":
    main()
