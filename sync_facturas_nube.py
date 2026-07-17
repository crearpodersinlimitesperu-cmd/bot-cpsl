import json
import requests
import datetime
import unicodedata
import re

API_URL = "https://script.google.com/macros/s/AKfycbySw3nJ0gmOqPtLURGrJeH7ja51MbkLjEDO2exqZTUAzW3-p35s4cU7uKSUUz4fEhGD/exec"
DATA_JSON = r"C:\Users\josem\Downloads\bot-cpsl-review\entrenadores_data.json"

def normalize_name(name):
    if not name:
        return ""
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii').upper()
    name = re.sub(r'[^A-Z]', '', name)
    return name

def sync_flights_to_backend():
    print("Obteniendo eventos del backend...")
    res = requests.get(API_URL + "?action=getEventos")
    events = res.json()
    
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        db = json.load(f)
        
    entrenadores = db.get("entrenadores", [])
    updates = []
    
    for ent in entrenadores:
        vuelo_llegada = ent.get("vuelo_llegada")
        vuelo_salida = ent.get("vuelo_salida")
        nombre_ent = normalize_name(ent.get("nombre", ""))
        
        if not vuelo_llegada and not vuelo_salida:
            continue
            
        print(f"\nBuscando eventos para: {ent['nombre']} ({nombre_ent})")
        
        # Buscar el evento más cercano.
        # Por ahora buscaremos todos los eventos de este trainer
        matched_events = []
        for ev in events:
            ev_trainer = normalize_name(ev.get("trainer", ""))
            if ev_trainer and ev_trainer == nombre_ent:
                matched_events.append(ev)
                
        # Si no encontramos exacto, intentamos parcial
        if not matched_events:
            for ev in events:
                ev_trainer_raw = unicodedata.normalize('NFKD', ev.get("trainer", "")).encode('ascii', 'ignore').decode('ascii').upper()
                # Split by / or spaces to match parts
                parts = re.split(r'[/_,\s]+', ev_trainer_raw)
                for part in parts:
                    part = re.sub(r'[^A-Z]', '', part)
                    if part and len(part) >= 4 and part in nombre_ent:
                        matched_events.append(ev)
                        break
                    
        if matched_events:
            # Asignar el vuelo al primer evento coincidente (o a todos los que estén cerca en fecha)
            asignado = False
            for ev in matched_events:
                # Parsear fecha de vuelo
                fecha_vuelo_str = vuelo_llegada.get("fecha") if vuelo_llegada else None
                if not fecha_vuelo_str or fecha_vuelo_str == "Por confirmar":
                    continue
                try:
                    # formato DD/MM/YY
                    d, m, y = map(int, fecha_vuelo_str.split('/'))
                    if y < 100: y += 2000
                    fecha_vuelo = datetime.date(y, m, d)
                    
                    # Parsear fecha de evento
                    # formato 2026-04-17T00:00:00Z
                    ev_date_str = ev.get("fecha_inicio", "")[:10]
                    ev_y, ev_m, ev_d = map(int, ev_date_str.split('-'))
                    fecha_evento = datetime.date(ev_y, ev_m, ev_d)
                    
                    diff = abs((fecha_vuelo - fecha_evento).days)
                    if diff <= 5: # El vuelo es para este evento
                        date_part = ev_date_str.replace('-', '')
                        sede_part = ev.get("sede", "LIM")[:3].upper()
                        equipo = ev.get("equipo", "")
                        evento_id = f"{sede_part}_E{equipo}_{date_part}"

                        updates.append({
                            "id": evento_id,
                            "eventoId": evento_id,
                            "ticket": "purchased",
                            "trainer_arrival": vuelo_llegada.get("fecha") + " " + vuelo_llegada.get("hora"),
                            "hotel": "booked"
                        })
                        print(f" -> Asignado al evento: {evento_id} (Fecha: {ev_date_str})")
                        asignado = True
                except Exception as e:
                    pass
            if not asignado:
                print(" -> Se encontró al entrenador, pero las fechas de los vuelos no coinciden con sus eventos.")
        else:
            print(" -> NO SE ENCONTRÓ EVENTO PARA ESTE ENTRENADOR")
            
    print(f"\nPreparando {len(updates)} actualizaciones para enviar...")
    
    # Enviar al backend
    if updates:
        chunk_size = 50
        for i in range(0, len(updates), chunk_size):
            chunk = updates[i:i + chunk_size]
            payload = {
                "action": "batchUpdate",
                "updates": chunk
            }
            res = requests.post(API_URL, json=payload)
            print(f"Respuesta lote {i//chunk_size + 1}:", res.text[:100])

if __name__ == "__main__":
    sync_flights_to_backend()
