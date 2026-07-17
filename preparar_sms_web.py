import pandas as pd
import json

df = pd.read_excel('C:\\Users\\josem\\Downloads\\CONTROL_SISTEMA_CREARLIMA\\Asignaciones_Web.xlsx')
bounces = df[df['Email'].str.contains('lluribell|atlanticcity', na=False, case=False)]

sms_messages = []
print("--- PREPARANDO SMS PARA REBOTES DESDE ASIGNACIONES WEB ---")
for index, row in bounces.iterrows():
    print(f"\nParticipante Encontrado: {row['NombreCompleto']} {row['ApellidoCompleto']}")
    print(f"Email Rebotado: {row['Email']}")
    print(f"Telefono: {row['Telefono']}")
    
    msg_px = f"Hola {row['NombreCompleto']}, te saludamos de CREAR. Intentamos enviarte la informacion de tu C1 a {row['Email']} pero rebotó. Por favor brindanos tu correo actual por este medio. Saludos!"
    sms_messages.append({"telefono": str(row['Telefono']), "mensaje": msg_px})
    
    # Buscar el IMO en el mismo excel
    imo_dni = str(row['IMO_DNI']).strip().replace('.0', '')
    if imo_dni and imo_dni != 'nan':
        imo_df = df[df['ClienteId'].astype(str).str.replace('.0', '', regex=False) == imo_dni]
        if not imo_df.empty:
            imo = imo_df.iloc[0]
            print(f"IMO Encontrado: {imo['NombreCompleto']} {imo['ApellidoCompleto']} - Telefono: {imo['Telefono']}")
            msg_imo = f"Hola {imo['NombreCompleto']}, como IMO de {row['NombreCompleto']}, te informamos que su correo {row['Email']} rebotó. Apoyanos solicitandole su correo actual. Gracias!"
            sms_messages.append({"telefono": str(imo['Telefono']), "mensaje": msg_imo})
        else:
            print(f"IMO {imo_dni} no encontrado en este excel.")

with open('C:\\Users\\josem\\Downloads\\bot-cpsl-review\\sms_rebotes_pendientes.json', 'w', encoding='utf-8') as f:
    json.dump(sms_messages, f, ensure_ascii=False, indent=4)

print(f"\nMensajes preparados: {len(sms_messages)}")
