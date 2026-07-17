import pandas as pd
import sqlite3
import unicodedata
import os
from datetime import datetime

# Configuracion
DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
CAJA_NEGRA_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
CSV_WEB = r'C:\Users\josem\Downloads\participantes_2026-05-11.csv'
CSV_CONTACTS = r'C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv'

def log_blackbox(conn_cn, evento, detalle, estado):
    try:
        cursor = conn_cn.cursor()
        cursor.execute("INSERT INTO logs (categoria, evento, detalle, estado) VALUES (?, ?, ?, ?)",
                       ('IDENTIDAD', evento, detalle, estado))
        conn_cn.commit()
    except:
        pass

def clean_text(text):
    if pd.isna(text): return ""
    text = str(text).strip().upper()
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return " ".join(text.split())

def clean_phone(phone):
    if pd.isna(phone): return ""
    s = str(phone).strip()
    if s.endswith(".0"): s = s[:-2]
    p = "".join(c for c in s if c.isdigit())
    if len(p) >= 9: return p[-9:]
    return ""

def ingestar_data():
    conn = sqlite3.connect(DB_PATH)
    conn_cn = sqlite3.connect(CAJA_NEGRA_PATH)
    cursor = conn.cursor()
    
    log_blackbox(conn_cn, 'INGESTA_INICIO', 'Iniciando sincronización MODO DIOS (Web + Contacts)', 'EN_CURSO')
    
    # 1. Cargar CSV Web
    try:
        df_web = pd.read_csv(CSV_WEB, on_bad_lines='skip', sep=None, engine='python')
    except Exception as e:
        log_blackbox(conn_cn, 'ERROR_WEB_CSV', str(e), 'ERROR')
        return
    
    # Limpiar CSV Web
    df_web['Nombre_Clean'] = df_web['Nombre'].apply(clean_text)
    df_web['Apellido_Clean'] = df_web['Apellido'].apply(clean_text)
    df_web['Full_Name'] = df_web['Nombre_Clean'] + ' ' + df_web['Apellido_Clean']
    df_web['Phone_Clean'] = df_web['Teléfono'].apply(clean_phone)
    
    # 2. Cargar CSV Contacts
    df_contacts = None
    if os.path.exists(CSV_CONTACTS):
        df_contacts = pd.read_csv(CSV_CONTACTS)
        if 'First Name' in df_contacts.columns and 'Last Name' in df_contacts.columns and 'E-mail 1 - Value' in df_contacts.columns:
            df_contacts['First Name Clean'] = df_contacts['First Name'].apply(clean_text)
            df_contacts['Last Name Clean'] = df_contacts['Last Name'].apply(clean_text)
            df_contacts['Full_Name_Contact'] = df_contacts['First Name Clean'] + ' ' + df_contacts['Last Name Clean']
            # Quitar filas sin email
            df_contacts = df_contacts[df_contacts['E-mail 1 - Value'].notna()]
    
    # Actualizaciones
    updates_imo = 0
    updates_email = 0
    
    # Vamos a procesar cada registro de la DB local y actualizarlo
    df_db = pd.read_sql("SELECT id, nombre, apellido, telefono, identificacion FROM participantes", conn)
    
    for idx, row in df_db.iterrows():
        db_id = row['id']
        db_nom = clean_text(row['nombre'])
        db_ape = clean_text(row['apellido'])
        db_full = db_nom + ' ' + db_ape
        db_tel = clean_phone(row['telefono'])
        
        # --- MATCH CON WEB (IMOs, Identificacion, C1, C2) ---
        match_web = None
        match_by_name = df_web[df_web['Full_Name'] == db_full]
        if not match_by_name.empty:
            match_web = match_by_name
        elif db_tel:
            from rapidfuzz import fuzz
            match_by_phone = df_web[df_web['Phone_Clean'] == db_tel]
            if not match_by_phone.empty:
                similar_matches = []
                for _, web_row in match_by_phone.iterrows():
                    sim = fuzz.token_set_ratio(db_full, web_row['Full_Name'])
                    if sim >= 80:
                        similar_matches.append((sim, web_row))
                if similar_matches:
                    similar_matches.sort(key=lambda x: x[0], reverse=True)
                    match_web = pd.DataFrame([similar_matches[0][1]])
        
        if match_web is not None and not match_web.empty:
            best_web = match_web.iloc[0]
            cursor.execute('''
                UPDATE participantes 
                SET identificacion = ?, c1 = ?, c2 = ?, maestria = ?, tipo = ?, equipo = ?, imo = ?, tel_imo = ?, fecha_actualizacion = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                str(best_web.get('Identificación', '')),
                str(best_web.get('C1', 'NO')),
                str(best_web.get('C2', 'NO')),
                str(best_web.get('Maestría', 'NO')),
                str(best_web.get('Tipo', '')),
                str(best_web.get('Equipo', '')),
                str(best_web.get('IMO', '')),
                clean_phone(best_web.get('Tel. IMO', '')),
                db_id
            ))
            updates_imo += 1
            
        # --- MATCH CON CONTACTS (Emails) ---
        if df_contacts is not None:
            match_contact = df_contacts[df_contacts['Full_Name_Contact'] == db_full]
            if not match_contact.empty:
                email = str(match_contact.iloc[0]['E-mail 1 - Value']).strip()
                cursor.execute("UPDATE participantes SET email = ? WHERE id = ?", (email, db_id))
                updates_email += 1

    conn.commit()
    conn.close()
    
    log_msg = f"Sincronización completada. Actualizados {updates_imo} registros web (IMO/DNI) y {updates_email} emails estrictos."
    print(log_msg)
    log_blackbox(conn_cn, 'INGESTA_FIN', log_msg, 'COMPLETADO')
    conn_cn.close()

if __name__ == "__main__":
    ingestar_data()
