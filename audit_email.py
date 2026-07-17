import json
import os

def audit_campaign():
    path = r'C:\Users\josem\Downloads\bot-cpsl-review\campana_email_programada.json'
    estado_path = r'C:\Users\josem\Downloads\bot-cpsl-review\campana_email_estado.json'
    
    print("--- AUDITORÍA DE COMUNICACIONES (EMAIL) ---")
    
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            px = data.get("correos_px", [])
            imo = data.get("correos_imo", [])
            print(f"Total Emails Alumnos (PX) programados: {len(px)}")
            print(f"Total Emails IMOs programados: {len(imo)}")
            print(f"Fecha programada: {data.get('programada_para')}")
            
            # Verificar duplicidad en la programación
            emails_px = [p['email'] for p in px]
            emails_imo = [i['email'] for i in imo]
            dups_px = len(emails_px) - len(set(emails_px))
            dups_imo = len(emails_imo) - len(set(emails_imo))
            print(f"Emails duplicados en lista PX: {dups_px}")
            print(f"Emails duplicados en lista IMO: {dups_imo}")
    else:
        print("Error: campana_email_programada.json no encontrado.")

    if os.path.exists(estado_path):
        with open(estado_path, 'r', encoding='utf-8') as f:
            estado = json.load(f)
            enviados_px = len(estado.get("enviados_px", []))
            enviados_imo = len(estado.get("enviados_imo", []))
            errores = len(estado.get("errores", []))
            print(f"\nEstado Histórico (Domingo 10):")
            print(f"Enviados PX: {enviados_px}")
            print(f"Enviados IMO: {enviados_imo}")
            print(f"Errores: {errores}")
    
if __name__ == "__main__":
    audit_campaign()
