import sqlite3
import pandas as pd
import json
import os
import re

def preparar_sms_rebotes():
    rebotes_path = r'C:\Users\josem\Downloads\bot-cpsl-review\auditoria_rebotes_total.csv'
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    contacts_path = r"C:\Users\josem\OneDrive\Documentos\campana-cpsl\excel c1e27 nw\contacts.csv"
    
    if not os.path.exists(rebotes_path):
        print("No se encontró auditoria_rebotes_total.csv")
        return

    df_rebotes = pd.read_csv(rebotes_path)
    bounced_emails = df_rebotes['email'].tolist()
    
    conn = sqlite3.connect(db_path)
    
    contacts_df = pd.DataFrame()
    if os.path.exists(contacts_path):
        try:
            contacts_df = pd.read_csv(contacts_path, dtype=str)
        except: pass

    sms_messages = []
    print(f"--- PREPARANDO SMS PARA {len(bounced_emails)} REBOTES ---")
    
    for email in bounced_emails:
        px = pd.read_sql_query("SELECT id, nombre, apellido, telefono, email, imo FROM participantes WHERE email = ?", conn, params=(email,))
        
        nombre_saludo = ""
        full_name = ""
        telefono = ""
        imo_id = ""
        
        if not px.empty:
            nombre_saludo = f"{px.iloc[0]['nombre']}".split()[0].title()
            full_name = f"{px.iloc[0]['nombre']} {px.iloc[0]['apellido']}"
            telefono = px.iloc[0]['telefono']
            imo_id = str(px.iloc[0]['imo']).strip()
        else:
            if not contacts_df.empty:
                c_row = contacts_df[contacts_df['E-mail 1 - Value'].str.lower() == email.lower()]
                if c_row.empty:
                    c_row = contacts_df[contacts_df['E-mail 2 - Value'].str.lower() == email.lower()]
                
                if not c_row.empty:
                    fname = str(c_row.iloc[0].get('First Name', '')).strip()
                    lname = str(c_row.iloc[0].get('Last Name', '')).strip()
                    nombre_saludo = fname.split()[0].title() if fname else "Participante"
                    full_name = f"{fname} {lname}".strip()
                    
                    phone = str(c_row.iloc[0].get('Phone 1 - Value', '')).strip()
                    phone = re.sub(r'[^\d]', '', phone)
                    if phone.startswith('51') and len(phone) > 9: phone = phone[2:]
                    telefono = phone
        
        if telefono and len(telefono) >= 9:
            msg_px = f"Hola {nombre_saludo}, te saludamos de CREAR. Intentamos enviarte la informacion de tu C1 a {email} pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
            sms_messages.append({"telefono": telefono, "mensaje": msg_px, "tipo": "PX", "nombre": full_name, "email": email})
            
            if imo_id and imo_id != 'None' and imo_id != 'nan':
                imo_df = pd.read_sql_query("SELECT nombre, apellido, telefono FROM participantes WHERE identificacion = ?", conn, params=(imo_id,))
                if not imo_df.empty:
                    imo = imo_df.iloc[0]
                    imo_nombre = str(imo['nombre']).split()[0].title()
                    msg_imo = f"Hola {imo_nombre}, como IMO de {full_name}, te informamos que su correo {email} rebotó. Apoyanos solicitandole su correo actual. Gracias!"
                    sms_messages.append({"telefono": imo['telefono'], "mensaje": msg_imo, "tipo": "IMO", "referencia": full_name, "email": email})

    output_json = r'C:\Users\josem\Downloads\bot-cpsl-review\sms_rebotes_pendientes.json'
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(sms_messages, f, ensure_ascii=False, indent=4)

    print(f"\n{len(sms_messages)} mensajes preparados en sms_rebotes_pendientes.json")
    conn.close()

if __name__ == "__main__":
    preparar_sms_rebotes()
