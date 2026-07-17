import sqlite3
import json
import os
import pandas as pd

def find_fe_de_erratas_recipients():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    estado_path = r'C:\Users\josem\Downloads\bot-cpsl-review\campana_email_estado.json'
    prog_path = r'C:\Users\josem\Downloads\bot-cpsl-review\campana_email_programada.json'
    
    if not os.path.exists(estado_path) or not os.path.exists(prog_path):
        print("No se encontraron los archivos de campaña.")
        return

    with open(estado_path, 'r', encoding='utf-8') as f:
        estado = json.load(f)
        enviados_emails = set(estado.get("enviados_px", []))

    with open(prog_path, 'r', encoding='utf-8') as f:
        prog = json.load(f)
        todos_px = prog.get("correos_px", [])

    # Mapear email -> ID de los que fueron realmente enviados
    email_to_id = {p['email']: p['id'] for p in todos_px if p['email'] in enviados_emails}
    sent_ids = list(email_to_id.values())

    if not sent_ids:
        print("No se encontraron IDs enviados.")
        return

    conn = sqlite3.connect(db_path)
    
    # 1. Graduados que recibieron el correo
    graduados_sent = pd.read_sql_query("""
        SELECT id, nombre, apellido FROM participantes 
        WHERE estado = 'GRADUADO_COMPLETO' 
        AND id IN ({})
    """.format(','.join(['?']*len(sent_ids))), conn, params=sent_ids)
    
    # 2. Reasignados de Zuley (que ahora tienen Diana/Joyce) que recibieron el correo
    # Buscamos a Diana/Joyce en la BD que están en sent_ids
    reasignados_sent = pd.read_sql_query("""
        SELECT id, nombre, apellido, cc_nombre FROM participantes 
        WHERE cc_nombre IN ('Diana Moscoso', 'Joyce Marín') 
        AND id IN ({})
    """.format(','.join(['?']*len(sent_ids))), conn, params=sent_ids)
    
    # 3. Todos los que recibieron el correo hoy (para la fe de erratas general de nombres)
    # El usuario dijo "los px con errares". Como no sabemos exactamente quiénes,
    # enviaremos una fe de erratas general a todos los 624 enviados hoy.
    
    # Consolidar
    recipients = []
    # Inversa del mapeo para tener el email
    id_to_email = {v: k for k, v in email_to_id.items()}
    
    # Agregar graduados
    for _, row in graduados_sent.iterrows():
        recipients.append({
            "id": row['id'],
            "nombre": f"{row['nombre']} {row['apellido']}",
            "email": id_to_email[row['id']],
            "tipo": "GRADUADO"
        })
        
    # Agregar reasignados (si no están ya)
    seen_ids = set([r['id'] for r in recipients])
    for _, row in reasignados_sent.iterrows():
        if row['id'] not in seen_ids:
            recipients.append({
                "id": row['id'],
                "nombre": f"{row['nombre']} {row['apellido']}",
                "email": id_to_email[row['id']],
                "tipo": "REASIGNADO"
            })
            
    # Agregar el resto como "GENERAL" (errores de nombres)
    for eid, pid in email_to_id.items():
        if pid not in seen_ids:
            recipients.append({
                "id": pid,
                "nombre": "Participante", # No usamos el nombre de la BD por si estaba mal en el email
                "email": eid,
                "tipo": "GENERAL"
            })

    df_final = pd.DataFrame(recipients)
    print(f"Total destinatarios para Fe de Erratas: {len(df_final)}")
    df_final.to_csv(r'C:\Users\josem\Downloads\bot-cpsl-review\recipientes_fe_de_erratas.csv', index=False)
    conn.close()

if __name__ == "__main__":
    find_fe_de_erratas_recipients()
