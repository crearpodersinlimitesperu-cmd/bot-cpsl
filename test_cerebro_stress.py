import requests
import json
import random
import time
import pandas as pd
from sync_cloud import load_master_cloud

# Configuración
BOT_URL = "http://localhost:10000/api/chat"

def run_stress_test(num_tests=100):
    import sys
    import io
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        
    print(f"--- Iniciando Stress Test del Cerebro: {num_tests} preguntas ---")
    
    # Cargar datos vía CSV local (más rápido para el test)
    CSV_PATH = "Prospectos_Pendientes_C1_Depurado_Campana.csv"
    
    try:
        df = pd.read_csv(CSV_PATH).fillna("—")
        if df.empty:
            print("❌ No se pudieron cargar los datos del CRM.")
            return
    except Exception as e:
        print(f"❌ Error cargando datos: {e}")
        return
    
    # Preparar campos
    cols = {c.strip().upper(): c for c in df.columns}
    c_nom = cols.get('NOMBRES', cols.get('NOMBRE', 'Nombres'))
    c_ape = cols.get('APELLIDOS', cols.get('APELLIDO', 'Apellidos'))
    c_dni = cols.get('DNI', 'DNI')
    c_coo = cols.get('COORDINADOR', 'Coordinador')
    c_eq = cols.get('ORIGEN/EQUIPO', cols.get('EQUIPO', 'Origen/Equipo'))
    
    nombres = df[c_nom].astype(str).tolist() if c_nom in df.columns else []
    dnis = df[c_dni].astype(str).tolist() if c_dni in df.columns else []
    coords = [c for c in df[c_coo].unique().tolist() if c and c != "—"] if c_coo in df.columns else []
    equipos = [e for e in df[c_eq].unique().tolist() if e and e != "—"] if c_eq in df.columns else []
    
    plantillas = [
        "¿Quién es el coordinador de {pax}?",
        "¿Cuál es el DNI de {pax}?",
        "¿{pax} ya se sentó en C1?",
        "Busca a {pax}",
        "Estado de {dni}",
        "¿Cuántos graduados hay en total?",
        "¿Cómo va la meta?",
        "¿Qué coordinadoras tenemos?",
        "Genera un resumen de {coord}",
        "¿Quiénes son del equipo {eq}?",
    ]
    
    resultados = []
    
    for i in range(num_tests):
        # Generar pregunta aleatoria
        pax = random.choice(nombres)
        dni = random.choice(dnis)
        coord = random.choice(coords) if coords else "DIANA"
        eq = random.choice(equipos) if equipos else "EQUIPO 27"
        
        pregunta = random.choice(plantillas).format(pax=pax, dni=dni, coord=coord, eq=eq)
        
        print(f"[{i+1}/{num_tests}] Enviando: {pregunta}")
        
        try:
            # Llamada real al bot en Render
            res = requests.post(BOT_URL, json={"message": pregunta, "source": "stress_test"}, timeout=20)
            if res.status_code == 200:
                reply = res.json().get("reply")
                print(f"   OK Respuesta: {reply[:100]}...")
                resultados.append({"pregunta": pregunta, "respuesta": reply, "ok": True})
            else:
                print(f"   ERROR API: {res.status_code}")
                resultados.append({"pregunta": pregunta, "error": res.text, "ok": False})
        except Exception as e:
            print(f"   ERROR: {str(e)}")
            resultados.append({"pregunta": pregunta, "error": str(e), "ok": False})
        
        # Pequeña pausa para no saturar
        time.sleep(0.5)
            
    # Guardar resultados
    with open("resultados_estres.json", "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
        
    print(f"\nTEST COMPLETADO. {len([r for r in resultados if r['ok']])}/{num_tests} exitosos.")
    print("Resultados guardados en resultados_estres.json")

if __name__ == "__main__":
    # Por defecto corremos 10 para no tardar demasiado en esta respuesta, 
    # pero el usuario puede subirlo a 100 o 1000.
    run_stress_test(20)
