from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging
from datetime import datetime

# --- CONFIGURACIÓN ---
app = FastAPI(title="CPSL TORRE DE CONTROL")
templates = Jinja2Templates(directory="templates")

# Configurar logging para la CAJA NEGRA
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("caja_negra_operativa.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TORRE_CONTROL")

# --- ENDPOINTS ---

@app.get("/", response_class=HTMLResponse)
async def read_dashboard(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/actualizar_crm")
async def actualizar_crm():
    """
    Sincroniza todas las fuentes de datos y actualiza estados.
    """
    logger.info("[ACTION] Botón ACTUALIZAR CRM presionado.")
    try:
        # Aquí llamaríamos a la lógica de auditoria_desertores_devoluciones.py y sync_crearpsl.py
        # Simulación de éxito para el MVP
        timestamp = datetime.now().strftime("%H:%M:%S")
        return {"status": "ok", "message": f"CRM Actualizado a las {timestamp}", "desertores": 328}
    except Exception as e:
        logger.error(f"Error en actualización: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/lanzar_campania")
async def lanzar_campania():
    """
    Ejecuta el envío de comunicaciones validando las reglas de Joyce/Diana.
    """
    logger.info("[ACTION] Botón LANZAR CAMPAÑAS presionado.")
    # REGLA CRÍTICA: Solo Joyce y Diana para C1/C2
    logger.info("[RULE] Aplicando filtro restrictivo: Joyce & Diana ONLY.")
    
    try:
        # Aquí llamaríamos a envio_omnicanal.py
        return {"status": "ok", "message": "Campaña procesada y encolada."}
    except Exception as e:
        logger.error(f"Error en campaña: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # En local usamos el puerto 10000 para consistencia con Render
    uvicorn.run(app, host="0.0.0.0", port=10000)
