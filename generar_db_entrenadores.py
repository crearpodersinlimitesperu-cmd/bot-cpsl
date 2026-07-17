import os
import glob
import json
from extractor_vuelos import extraer_datos_factura_latam

FACTURAS_DIR = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\FACTURAS"
DATA_JSON = r"C:\Users\josem\Downloads\bot-cpsl-review\entrenadores_data.json"

def integrar_facturas_a_db():
    print("Iniciando escaneo de facturas LATAM...")
    # Buscar todos los PDF de LATAM
    archivos = glob.glob(os.path.join(FACTURAS_DIR, "LA*-cuv-bill.pdf"))
    
    # Cargar DB actual
    if os.path.exists(DATA_JSON):
        with open(DATA_JSON, "r", encoding="utf-8") as f:
            db = json.load(f)
    else:
        db = {"contactos_crear_lima": {}, "venues": {}, "entrenadores": []}
    
    entrenadores = db.get("entrenadores", [])
    
    for archivo in archivos:
        print(f"Procesando: {os.path.basename(archivo)}")
        datos_vuelo = extraer_datos_factura_latam(archivo)
        
        if not datos_vuelo or not datos_vuelo.get("nombre"):
            continue
            
        nombre = datos_vuelo["nombre"]
        
        # Buscar si el entrenador ya existe en la DB
        entrenador_existente = next((e for e in entrenadores if e["nombre"] == nombre), None)
        
        if entrenador_existente:
            print(f"  -> Actualizando vuelos para: {nombre}")
            if "vuelo_llegada" in datos_vuelo:
                entrenador_existente["vuelo_llegada"] = datos_vuelo["vuelo_llegada"]
            if "vuelo_salida" in datos_vuelo:
                entrenador_existente["vuelo_salida"] = datos_vuelo["vuelo_salida"]
        else:
            print(f"  -> Nuevo entrenador detectado: {nombre}")
            nuevo_ent = {
                "nombre": nombre,
                "email": "POR DEFINIR", # TODO: Agregar email de contacto
                "programa": "POR ASIGNAR", # TODO: Asignar programa (EJ: MAESTRIA DEL JUEGO)
                "equipo": "POR ASIGNAR", # TODO: Asignar equipo (EJ: E27)
                "hotel": "jose_antonio_deluxe",
                "fechas_entrenamiento": ["Viernes", "Sábado", "Domingo"]
            }
            if "vuelo_llegada" in datos_vuelo:
                nuevo_ent["vuelo_llegada"] = datos_vuelo["vuelo_llegada"]
            if "vuelo_salida" in datos_vuelo:
                nuevo_ent["vuelo_salida"] = datos_vuelo["vuelo_salida"]
            
            entrenadores.append(nuevo_ent)

    # Guardar cambios
    db["entrenadores"] = entrenadores
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
        
    print(f"\nProceso finalizado. Total entrenadores en DB: {len(entrenadores)}")
    print("Por favor, revise entrenadores_data.json para completar emails y equipos asignados.")

if __name__ == "__main__":
    integrar_facturas_a_db()
