import os, json, csv
from datetime import datetime, timedelta

# Configuración simplificada para el script
DATA_DIR = "/data" if os.path.exists("/data") else "."
HIST_PATH = os.path.join(DATA_DIR, "historial_chat.json") # Ajustar según Cfg

def analizar_silencios(horas=24):
    if not os.path.exists(HIST_PATH):
        print(f"❌ No se encontró el historial en {HIST_PATH}")
        return
    
    with open(HIST_PATH, "r", encoding="utf-8") as f:
        hist = json.load(f)
    
    # Agrupar por teléfono
    por_tel = {}
    ahora = datetime.now()
    limite = ahora - timedelta(hours=horas)
    
    for m in hist:
        tel = m.get("telefono")
        if not tel: continue
        ts = datetime.strptime(m.get("hora"), "%d/%m/%Y %H:%M:%S")
        if ts < limite: continue
        
        if tel not in por_tel: por_tel[tel] = []
        por_tel[tel].append(m)
    
    silencios = []
    for tel, msgs in por_tel.items():
        # Ordenar por tiempo
        msgs.sort(key=lambda x: x["hora"])
        ultimo = msgs[-1]
        
        # Si el último mensaje es "in" (del usuario) y no hay un "out" (del bot) después
        if ultimo.get("dir") == "in":
            # Verificar si hubo algún "out" después de este "in"
            ha_respondido = False
            for m in reversed(msgs):
                if m.get("dir") == "out":
                    ha_respondido = True
                    break
                if m == ultimo: break
            
            if not ha_respondido:
                silencios.append({
                    "tel": tel,
                    "nombre": ultimo.get("nombre", "Desconocido"),
                    "texto": ultimo.get("texto"),
                    "hora": ultimo.get("hora")
                })
    
    return silencios

if __name__ == "__main__":
    print(f"🔍 Analizando silencios en las últimas 24 horas...")
    resultados = analizar_silencios()
    if resultados:
        print(f"⚠️ Se detectaron {len(resultados)} usuarios sin respuesta:")
        for r in resultados:
            print(f"  • {r['tel']} ({r['nombre']}): '{r['texto'][:30]}...' a las {r['hora']}")
        print("\n🚀 Para reprocesar, usa el endpoint /api/debug/reprocesar (se implementará en bot_whatsapp.py)")
    else:
        print("✅ No se detectaron silencios recientes.")
