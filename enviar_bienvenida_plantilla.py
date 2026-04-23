import os, csv, json, logging, time, threading, requests
from datetime import datetime, timezone, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("MasivoPlantilla")
TZ  = timezone(timedelta(hours=-5))
def ahora(): return datetime.now(TZ)

# =========================================================
# CONFIGURACIÓN DE LA PLANTILLA
# =========================================================
TEMPLATE_NAME = "bienvenida_c1_e27"  # <- CAMBIAR SI LA PLANTILLA TIENE OTRO NOMBRE
TEMPLATE_LANG = "es"

CSV_PATH   = "Prospectos_Pendientes_C1_Depurado_Campana.csv"
DATA_DIR   = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
ESTADO_PATH = os.path.join(DATA_DIR, "estado_masivo_plantilla.json")

PHONE_ID  = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_TOKEN  = os.environ.get("WA_TOKEN", "")
PAUSA      = 25   # Segundos entre mensajes para cuidar la cuenta

def cargar_px():
    if not os.path.exists(CSV_PATH):
        log.error(f"CSV no encontrado: {CSV_PATH}")
        return []
    with open(CSV_PATH, encoding="utf-8") as f:
        return list(csv.DictReader(f))

def cargar_estado():
    if os.path.exists(ESTADO_PATH):
        with open(ESTADO_PATH) as f: return json.load(f)
    return {}

def guardar_estado(d):
    with open(ESTADO_PATH, "w") as f: json.dump(d, f, ensure_ascii=False, indent=2)

def _wa_template(tel, nombre):
    if not WA_TOKEN: 
        log.error("No hay WA_TOKEN")
        return False
        
    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": nombre}]
                }
            ]
        }
    }
    
    try:
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages",
            json=payload,
            headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"},
            timeout=15
        )
        if r.status_code == 200: return True
        log.error(f"WA error {tel}: {r.text[:200]}")
        return False
    except Exception as e:
        log.error(f"WA exc {tel}: {e}")
        return False

def ejecutar_masivo(limite=50):
    pxs = cargar_px()
    estado = cargar_estado()
    
    # Filtrar solo pendientes que tengan teléfono y no hayan sido enviados
    pendientes = [p for p in pxs if p.get("Estado") == "Pendiente" and p.get("Telefono")]
    a_enviar = [p for p in pendientes if p.get("Telefono") not in estado]
    
    log.info(f"Total Pendientes: {len(pendientes)} | Falta Enviar: {len(a_enviar)}")
    
    if not a_enviar:
        log.info("No hay PX pendientes por enviar.")
        return
        
    lote = a_enviar[:limite]
    log.info(f"Iniciando envío de {len(lote)} mensajes con plantilla '{TEMPLATE_NAME}'...")
    
    exitos = 0
    for px in lote:
        tel = px.get("Telefono")
        nombre_pila = (px.get("Nombre","") or px.get("Apellido","Amigo")).split()[0].title()
        
        log.info(f"Enviando a {nombre_pila} ({tel})...")
        ok = _wa_template(tel, nombre_pila)
        
        estado[tel] = {
            "ts": ahora().isoformat(),
            "ok": ok,
            "nombre": nombre_pila
        }
        guardar_estado(estado)
        
        if ok: exitos += 1
        time.sleep(PAUSA)
        
    log.info(f"Lote finalizado. {exitos}/{len(lote)} exitosos.")

if __name__ == "__main__":
    ejecutar_masivo(limite=5) # Probar con 5 primero
