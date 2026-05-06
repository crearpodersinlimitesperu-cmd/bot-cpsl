import os
import logging
import time
import requests
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import FastAPI, Request, HTTPException, Depends, BackgroundTasks
from pydantic_settings import BaseSettings
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal, engine, init_db, get_db, LogEnvio, Usuario, Campana, Caso, Derivacion

# ── Configuración de Entorno ─────────────────────────────────────────────
class Settings(BaseSettings):
    WA_TOKEN: str = os.environ.get("WA_TOKEN", "")
    WA_PHONE_ID: str = os.environ.get("WA_PHONE_ID", "1085205258006361")
    WA_VERIFY_TOKEN: str = os.environ.get("WA_VERIFY_TOKEN", "cpsl2026")
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./bot_cpsl.db")
    
    class Config:
        env_file = ".env"

settings = Settings()

# ── Logging ──────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("CPSL_PRO")

# ── Inicialización ───────────────────────────────────────────────────────
init_db()
app = FastAPI(title="Bot CPSL Pro")

# ── Utilidades de WhatsApp ───────────────────────────────────────────────
def send_whatsapp(to: str, message: str, db: Session) -> Optional[int]:
    """
    Envía un mensaje de texto usando WhatsApp Cloud API con reintentos y logging.
    La 'Caja Negra' registra cada intento.
    """
    url = f"https://graph.facebook.com/v19.0/{settings.WA_PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {settings.WA_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    
    status = 0
    error_msg = None
    
    try:
        # Reintento simple para errores 5xx o 429
        for attempt in range(2):
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            status = r.status_code
            if status == 200:
                break
            if status < 500 and status != 429:
                error_msg = r.text
                break
            time.sleep(1)
    except Exception as e:
        status = 999
        error_msg = str(e)
        logger.error(f"Error enviando WA a {to}: {e}")

    # REGISTRO EN LA CAJA NEGRA
    log = LogEnvio(
        telefono=to,
        tipo="OUT",
        mensaje=message,
        status_code=status,
        error=error_msg
    )
    db.add(log)
    db.commit()
    
    return status

# ── Webhook ─────────────────────────────────────────────────────────────
@app.get("/webhook")
def verify_webhook(request: Request):
    """Verificación del webhook por Meta."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.WA_VERIFY_TOKEN:
        logger.info("Webhook verificado ✅")
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_webhook(request: Request, bg_tasks: BackgroundTasks):
    """Recepción de mensajes entrantes."""
    data = await request.json()
    
    # Validar que sea un mensaje de WhatsApp
    if not data.get("entry"):
        return {"status": "ignored"}
        
    for entry in data["entry"]:
        for change in entry.get("changes", []):
            value = change.get("value", {})
            if "messages" in value:
                for msg in value["messages"]:
                    tel = msg.get("from")
                    if msg.get("type") == "text":
                        text = msg["text"].get("body", "")
                        logger.info(f"Mensaje de {tel}: {text}")
                        
                        # Guardar en Caja Negra (IN)
                        db = SessionLocal()
                        try:
                            log = LogEnvio(telefono=tel, tipo="IN", mensaje=text, status_code=0)
                            db.add(log)
                            db.commit()
                            
                            # Procesar en background para no bloquear el webhook
                            bg_tasks.add_task(procesar_flujo, tel, text)
                        finally:
                            db.close()
                            
    return {"status": "ok"}

# ── Integración con Lógica Existente ─────────────────────────────────────
try:
    import bot_whatsapp as bw
    
    # Inyectamos nuestra función wa que guarda en DB en el módulo original
    def wa_caja_negra(tel, txt, log="BOT"):
        db = SessionLocal()
        try:
            return send_whatsapp(str(tel), txt, db)
        finally:
            db.close()
    
    # Inyectamos persistencia de sesión en DB para evitar pérdida en reinicios de Render
    def get_s_db(tel):
        db = SessionLocal()
        try:
            import json
            u = db.query(Usuario).filter(Usuario.telefono == str(tel)).first()
            return json.loads(u.state_json) if u and u.state_json else {}
        finally:
            db.close()

    def set_s_db(tel, data):
        db = SessionLocal()
        try:
            import json
            u = db.query(Usuario).filter(Usuario.telefono == str(tel)).first()
            if not u:
                u = Usuario(telefono=str(tel))
                db.add(u)
            u.state_json = json.dumps(data)
            db.commit()
        finally:
            db.close()

    bw.wa = wa_caja_negra
    bw.get_s = get_s_db
    bw.set_s = set_s_db
    logger.info("Lógica de bot_whatsapp.py vinculada a la Caja Negra y Persistencia DB ✅")
except Exception as e:
    logger.error(f"Error vinculando bot_whatsapp: {e}")
    bw = None

# ── Endpoints de Administración ──────────────────────────────────────────
@app.post("/admin/set_campaign")
def set_campaign(data: dict, db: Session = Depends(get_db)):
    """Cambia la campaña activa en la base de datos."""
    nombre = data.get("nombre")
    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre de campaña requerido")
    
    # Desactivar otras campañas
    db.query(Campana).update({Campana.activo: False})
    
    # Buscar o crear la nueva
    camp = db.query(Campana).filter(Campana.nombre == nombre).first()
    if not camp:
        camp = Campana(nombre=nombre, activo=True, fecha_inicio=datetime.utcnow(), fecha_fin=datetime.utcnow() + timedelta(days=30))
        db.add(camp)
    else:
        camp.activo = True
    
    db.commit()
    logger.info(f"Campaña cambiada a: {nombre}")
    return {"status": "ok", "campaña": nombre}

@app.post("/admin/close_cases")
def close_cases(db: Session = Depends(get_db)):
    """Cierra todos los casos abiertos (útil para limpiezas manuales)."""
    db.query(Caso).filter(Caso.estado != "cerrado").update({
        Caso.estado: "cerrado",
        Caso.closed_at: datetime.utcnow()
    })
    db.commit()
    return {"status": "ok", "message": "Todos los casos han sido cerrados"}

def procesar_flujo(tel: str, text: str):
    """
    Llama a la lógica de flujo original pero con la Caja Negra activa.
    """
    if bw:
        try:
            bw.flujo(tel, text)
        except Exception as e:
            logger.error(f"Error en flujo de bot_whatsapp: {e}")
            db = SessionLocal()
            try:
                send_whatsapp(tel, "🙏 Tuvimos un inconveniente, pero ya estamos aquí. ¿En qué podemos ayudarte?", db)
            finally:
                db.close()
    else:
        logger.warning("bot_whatsapp no disponible")

# ── Tareas de Fondo (Scheduler) ─────────────────────────────────────────
def reprocesar_silencios():
    """
    Busca mensajes IN sin respuesta OUT en los últimos 2 minutos.
    """
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=2)
        # Buscar teléfonos que enviaron mensaje hace poco
        pendientes = db.query(LogEnvio.telefono).filter(
            LogEnvio.tipo == "IN",
            LogEnvio.timestamp >= cutoff
        ).distinct().all()
        
        for (tel,) in pendientes:
            # ¿Tienen un OUT después de su último IN?
            ultimo_in = db.query(LogEnvio.timestamp).filter(LogEnvio.telefono == tel, LogEnvio.tipo == "IN").order_by(LogEnvio.timestamp.desc()).first()
            ultimo_out = db.query(LogEnvio.timestamp).filter(LogEnvio.telefono == tel, LogEnvio.tipo == "OUT").order_by(LogEnvio.timestamp.desc()).first()
            
            if not ultimo_out or ultimo_out.timestamp < ultimo_in.timestamp:
                logger.warning(f"Silencio detectado para {tel}. Enviando fallback.")
                send_whatsapp(tel, "⚠️ *Aviso:* Tuvimos un pequeño retraso, pero ya te atendemos. ¿En qué podemos ayudarte?", db)
    except Exception as e:
        logger.error(f"Error en reprocesar_silencios: {e}")
    finally:
        db.close()

def sync_cron():
    """Llamada al sincronizador externo."""
    try:
        from sync_crearpsl import correr_una_vez
        correr_una_vez()
    except Exception as e:
        logger.error(f"Error en sync_cron: {e}")

def cerrar_campanas_antiguas():
    """
    Busca campañas que ya pasaron su fecha_fin y marca sus casos como cerrados.
    """
    db = SessionLocal()
    try:
        ahora = datetime.utcnow()
        campanas_viejas = db.query(Campana).filter(Campana.fecha_fin < ahora, Campana.activo == True).all()
        for camp in campanas_viejas:
            logger.info(f"Cerrando campaña expirada: {camp.nombre}")
            db.query(Caso).filter(Caso.campana_id == camp.id, Caso.estado != "cerrado").update({
                "estado": "cerrado",
                "closed_at": ahora
            })
            camp.activo = False
        db.commit()
    except Exception as e:
        logger.error(f"Error en cerrar_campanas_antiguas: {e}")
    finally:
        db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(reprocesar_silencios, 'interval', minutes=1)
scheduler.add_job(sync_cron, 'interval', minutes=30)
scheduler.add_job(cerrar_campanas_antiguas, 'cron', hour=0) # Una vez al día a medianoche
scheduler.start()

# ── Health Check ────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
