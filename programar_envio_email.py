"""
LANZADOR DE CAMPAÑA PROGRAMADA — CPSL Lima
=============================================
Dejar corriendo en segundo plano. Esperará hasta las
8:00 AM del domingo 10 de mayo y ejecutará el envío.

IMPORTANTE: Antes de lanzar, asegurar que:
1. .env tenga GMAIL_APP_PASS correcta
2. campana_email_programada.json exista (ejecutar --preparar primero)

Uso:
  python programar_envio_email.py
  
Para lanzar oculto (sin ventana):
  pythonw programar_envio_email.py
"""
import os
import sys
import time
import json
from datetime import datetime
from zoneinfo import ZoneInfo

sys.stdout.reconfigure(encoding='utf-8')
TZ = ZoneInfo("America/Lima")

# Log rotativo
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log_programador.txt")

def log(msg):
    ts = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_PATH, 'a', encoding='utf-8') as f:
        f.write(line + "\n")

def main():
    log("=" * 50)
    log("PROGRAMADOR DE CAMPAÑA EMAIL — CPSL LIMA")
    log("=" * 50)
    
    # Verificar que la campaña existe
    campana_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campana_email_programada.json")
    if not os.path.exists(campana_path):
        log("❌ ERROR: No existe campana_email_programada.json")
        log("   Ejecute: python campana_email_c1e28.py --preparar")
        return
    
    with open(campana_path, 'r', encoding='utf-8') as f:
        campana = json.load(f)
    
    total = campana['total_correos_px'] + campana['total_correos_imo']
    log(f"📧 Campaña cargada: {total} correos ({campana['total_correos_px']} PX + {campana['total_correos_imo']} IMO)")
    
    # Hora objetivo: 8:00 AM Lima del día siguiente (o de hoy si aún no son las 8)
    ahora = datetime.now(TZ)
    target = ahora.replace(hour=8, minute=0, second=0, microsecond=0)
    if ahora.hour >= 8:
        from datetime import timedelta
        target += timedelta(days=1)
    
    delta_sec = (target - ahora).total_seconds()
    delta_hrs = delta_sec / 3600
    
    log(f"⏰ Hora actual Lima: {ahora.strftime('%Y-%m-%d %H:%M')}")
    log(f"⏰ Envío programado: {target.strftime('%Y-%m-%d %H:%M')}")
    log(f"⏰ Faltan: {delta_hrs:.1f} horas ({delta_sec:.0f} segundos)")
    log(f"🔄 Entrando en modo espera...")
    
    # Loop de espera con heartbeat cada 30 minutos
    while True:
        ahora = datetime.now(TZ)
        if ahora >= target:
            break
        
        restante = (target - ahora).total_seconds()
        if restante <= 0:
            break
        
        # Heartbeat cada 30 min
        hrs_rest = restante / 3600
        log(f"  💤 Faltan {hrs_rest:.1f}h para el envío ({ahora.strftime('%H:%M')})")
        
        # Dormir 30 min o lo que quede
        time.sleep(min(1800, restante))
    
    # ¡HORA DE ENVIAR!
    log("=" * 50)
    log("🚀 ¡EJECUTANDO ENVÍO DE CAMPAÑA!")
    log("=" * 50)
    
    # Importar y ejecutar
    from campana_email_c1e28 import ejecutar_envio
    estado = ejecutar_envio()
    
    if estado:
        enviados = len(estado.get('enviados_px', [])) + len(estado.get('enviados_imo', []))
        errores = len(estado.get('errores', []))
        log(f"\n✅ CAMPAÑA FINALIZADA: {enviados} enviados, {errores} errores")
    else:
        log("❌ La campaña terminó con problemas")
    
    log("=" * 50)

if __name__ == "__main__":
    main()
