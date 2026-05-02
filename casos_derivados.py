"""
GESTOR DE CASOS DERIVADOS — CPSL Lima
Persiste en /data/casos_derivados.json
Cada caso tiene: tel_px, nombre, cc, asunto, estado, historial, ts_apertura, ts_cierre
Estados: ABIERTO | EN_GESTION | CERRADO | URGENTE
"""
import os, json, threading, logging, re
from datetime import datetime, timedelta, timezone

log = logging.getLogger("Casos")
TZ  = timezone(timedelta(hours=-5))
def ahora(): return datetime.now(TZ)

DATA_DIR = "/data" if os.path.exists("/data") else os.path.dirname(os.path.abspath(__file__))
CASOS_PATH = os.path.join(DATA_DIR, "casos_derivados.json")
_lk = threading.Lock()

STAFF = {
    "dmoscoso": {"nombre":"Diana Moscoso",  "tel":"51912379744"},
    "jmarin":   {"nombre":"Joyce Marín",    "tel":"51933599903"},
}

def _cargar():
    try:
        if os.path.exists(CASOS_PATH):
            with open(CASOS_PATH, encoding="utf-8") as f:
                casos = json.load(f)
                migrados = False
                for k, c in casos.items():
                    if c.get("cc_key") == "zurteaga":
                        try:
                            # Migración equitativa y consistente por hash del teléfono
                            nuevo_cc = "dmoscoso" if int(hash(str(k))) % 2 == 0 else "jmarin"
                        except: nuevo_cc = "dmoscoso"
                        c["cc_key"] = nuevo_cc
                        c["cc_nombre"] = "Diana Moscoso" if nuevo_cc == "dmoscoso" else "Joyce Marín"
                        migrados = True
                if migrados: _guardar_sin_lock(casos)
                return casos
    except: pass
    return {}

def _guardar_sin_lock(casos):
    try:
        with open(CASOS_PATH, "w", encoding="utf-8") as f:
            json.dump(casos, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.error(f"guardar_casos (sin_lock): {e}")

def _guardar(casos):
    _guardar_sin_lock(casos)

def abrir_caso(tel_px, nombre, cc_key, asunto, urgente=False):
    """Abre o actualiza un caso derivado."""
    with _lk:
        casos = _cargar()
        if tel_px in casos and casos[tel_px]["estado"] not in ("CERRADO",):
            # Ya existe — agregar nota
            casos[tel_px]["historial"].append({
                "ts": ahora().isoformat(), "nota": f"Rederivado: {asunto}"
            })
        else:
            casos[tel_px] = {
                "tel_px":     tel_px,
                "nombre":     nombre,
                "cc_key":     cc_key,
                "cc_nombre":  STAFF.get(cc_key, {}).get("nombre", cc_key),
                "asunto":          asunto,
                "asunto_original": asunto,  # inmutable
                "estado":          "URGENTE" if urgente else "ABIERTO",
                "ts_apertura":ahora().isoformat(),
                "ts_cierre":  None,
                "ultima_notif":None,
                "historial":  [{"ts":ahora().isoformat(),"nota":f"Apertura: {asunto}"}],
            }
        _guardar(casos)
    return casos[tel_px]

def cerrar_caso(tel_px, nota=""):
    """Cierra un caso."""
    with _lk:
        casos = _cargar()
        if tel_px in casos:
            casos[tel_px]["estado"]    = "CERRADO"
            casos[tel_px]["ts_cierre"] = ahora().isoformat()
            if nota:
                casos[tel_px]["historial"].append({"ts":ahora().isoformat(),"nota":nota})
            _guardar(casos)
            return True
    return False

def actualizar_caso(tel_px, nuevo_estado, nota=""):
    """Actualiza el estado de un caso."""
    with _lk:
        casos = _cargar()
        if tel_px in casos:
            casos[tel_px]["estado"] = nuevo_estado
            if nota:
                casos[tel_px]["historial"].append({"ts":ahora().isoformat(),"nota":nota})
            _guardar(casos)
            return True
    return False

def casos_abiertos(cc_key=None):
    """Retorna casos abiertos, opcionalmente filtrado por CC."""
    with _lk:
        casos = _cargar()
    activos = [c for c in casos.values() 
               if c["estado"] in ("ABIERTO","EN_GESTION","URGENTE")]
    if cc_key:
        activos = [c for c in activos if c["cc_key"] == cc_key]
    return sorted(activos, key=lambda x: (x["estado"]!="URGENTE", x["ts_apertura"]))

def casos_para_followup(horas=12):
    """Casos que llevan más de N horas sin notificación a la CC."""
    ahora_dt = ahora()
    resultado = []
    with _lk:
        casos = _cargar()
    for c in casos.values():
        if c["estado"] not in ("ABIERTO","EN_GESTION","URGENTE"):
            continue
        ultima = c.get("ultima_notif")
        if not ultima:
            resultado.append(c)
            continue
        try:
            dt_ultima = datetime.fromisoformat(ultima)
            if (ahora_dt - dt_ultima).total_seconds() / 3600 >= horas:
                resultado.append(c)
        except: resultado.append(c)
    return resultado

def marcar_notificado(tel_px):
    with _lk:
        casos = _cargar()
        if tel_px in casos:
            casos[tel_px]["ultima_notif"] = ahora().isoformat()
            _guardar(casos)

def resumen_casos():
    with _lk:
        casos = _cargar()
    total    = len(casos)
    urgentes = sum(1 for c in casos.values() if c["estado"]=="URGENTE")
    abiertos = sum(1 for c in casos.values() if c["estado"]=="ABIERTO")
    gestion  = sum(1 for c in casos.values() if c["estado"]=="EN_GESTION")
    cerrados = sum(1 for c in casos.values() if c["estado"]=="CERRADO")
    por_cc   = {}
    for c in casos.values():
        if c["estado"] not in ("CERRADO",):
            k = c["cc_key"]
            por_cc[k] = por_cc.get(k, 0) + 1
    return {
        "total":total, "urgentes":urgentes, "abiertos":abiertos,
        "en_gestion":gestion, "cerrados":cerrados, "por_cc":por_cc
    }

def casos_cerrados(cc_key=None, limite=15):
    """Retorna los ultimos casos cerrados (archivados), opcionalmente filtrado por CC."""
    with _lk:
        casos = _cargar()
    cerrados = [c for c in casos.values() if c["estado"] == "CERRADO"]
    if cc_key:
        cerrados = [c for c in cerrados if c["cc_key"] == cc_key]
    return sorted(cerrados, key=lambda x: x.get("ts_cierre") or "", reverse=True)[:limite]
