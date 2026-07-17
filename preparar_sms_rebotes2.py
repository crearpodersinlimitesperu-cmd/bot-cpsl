import sqlite3
import pandas as pd
import json

conn = sqlite3.connect('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\torre_control.db')

query = "SELECT id, nombre, apellido, telefono, email, imo FROM participantes WHERE email LIKE '%lluribellrodriguez%' OR email LIKE '%atlanticcity%'"
df = pd.read_sql_query(query, conn)

sms_messages = []
print("--- PREPARANDO SMS PARA REBOTES ---")
for index, row in df.iterrows():
    print(f"\nParticipante Encontrado: {row['nombre']} {row['apellido']}")
    print(f"Email Rebotado: {row['email']}")
    print(f"Telefono: {row['telefono']}")
    
    msg_px = f"Hola {row['nombre']}, te saludamos de CREAR. Intentamos enviarte la informacion de tu C1 a {row['email']} pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
    sms_messages.append({"telefono": row['telefono'], "mensaje": msg_px})
    
    # Buscar el IMO
    imo_id = str(row['imo']).strip()
    if imo_id and imo_id != 'None':
        imo_df = pd.read_sql_query("SELECT nombre, apellido, telefono FROM participantes WHERE identificacion = ?", conn, params=(imo_id,))
        if not imo_df.empty:
            imo = imo_df.iloc[0]
            print(f"IMO Encontrado: {imo['nombre']} {imo['apellido']} - Telefono: {imo['telefono']}")
            msg_imo = f"Hola {imo['nombre']}, como IMO de {row['nombre']} {row['apellido']}, te informamos que su correo {row['email']} rebotó. Apoyanos solicitandole su correo actual. Gracias!"
            sms_messages.append({"telefono": imo['telefono'], "mensaje": msg_imo})

with open('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\sms_rebotes_pendientes.json', 'w', encoding='utf-8') as f:
    json.dump(sms_messages, f, ensure_ascii=False, indent=4)

print(f"\nMensajes preparados: {len(sms_messages)}")
conn.close()
