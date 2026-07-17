import json
import requests

API_URL = "https://script.google.com/macros/s/AKfycbySw3nJ0gmOqPtLURGrJeH7ja51MbkLjEDO2exqZTUAzW3-p35s4cU7uKSUUz4fEhGD/exec"

def migrate_logistics():
    try:
        with open(r"C:\Users\josem\Downloads\cpsl-web-ecosystem\events_data.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("events_data.json not found")
        return

    updates = []
    for sede, events in data.items():
        for ev in events:
            if "logistics" in ev and ev["logistics"]:
                # Generar el ID compatible
                equipo_str = str(ev.get("equipo", "")).strip()
                start = ev.get("start", "")
                if not start:
                    continue
                date_part = start.split("T")[0].replace("-", "")
                evento_id = f"EVENTO_{sede}_{equipo_str}_{date_part}".replace(" ", "_")
                
                # Construir logistica
                l = ev["logistics"]
                if isinstance(l, list):
                    if not l: continue
                    l = l[0]
                updates.append({
                    "id": evento_id,
                    "ticket": l.get("ticket", "pending"),
                    "hotel": l.get("hotel", "pending"),
                    "trainer_notified": l.get("trainer_notified", False),
                    "trainer_arrival": l.get("trainer_arrival", ""),
                    "ticket_url": l.get("ticket_url", "")
                })

    if updates:
        print(f"Migrando {len(updates)} registros de logistica...")
        chunk_size = 50
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i + chunk_size]
            payload = {
                "action": "batchUpdate",
                "updates": chunk
            }
            print(f"Enviando lote {i//chunk_size + 1}...")
            res = requests.post(API_URL, json=payload)
            print(f"Respuesta lote {i//chunk_size + 1}:", res.text[:100])
    else:
        print("No logistics data found to migrate.")

if __name__ == "__main__":
    migrate_logistics()
