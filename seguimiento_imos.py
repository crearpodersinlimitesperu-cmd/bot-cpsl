"""
seguimiento_imos.py — Seguimiento automatico de IMOs para px NC
================================================================
- Lee GESTION_LLAMADAS cada 30 min
- Identifica px que NO CONTESTAN
- Genera mensajes para IMOs con lista de px NC + datos CC
- Registra respuestas IMO en pestaña RESPUESTAS_IMO
"""
import logging, re
from datetime import datetime
from zoneinfo import ZoneInfo

log = logging.getLogger("CPSL.IMO")
TZ = ZoneInfo("America/Lima")

# Contacto de cada CC para que el IMO pueda llamar directo
CC_CONTACTO = {
    "DIANA": {"nombre": "Diana Moscoso", "tel": "51XXXXXXXXX"},
    "JOYCE": {"nombre": "Joyce Marin", "tel": "51XXXXXXXXX"},
    "ZULEY": {"nombre": "Zuley Urteaga", "tel": "51XXXXXXXXX"},
}

def ahora():
    return datetime.now(TZ)

def en_horario():
    """Solo entre 9am y 5pm Lima."""
    h = ahora().hour
    return 9 <= h < 17

def obtener_nc_por_imo(sheets_client, sheet_id):
    """
    Lee GESTION_LLAMADAS y agrupa los NC por IMO.
    Retorna: {imo_tel: {nombre_imo, cc_alias, participantes: [{nombre, equipo}]}}
    """
    try:
        sh = sheets_client.open_by_key(sheet_id)
        ws = sh.worksheet("GESTION_LLAMADAS")
        rows = ws.get_all_records()
    except Exception as e:
        log.error(f"IMO: Error leyendo GESTION_LLAMADAS: {e}")
        return {}

    nc_por_imo = {}
    for r in rows:
        primera = str(r.get("Primera_Llamada", "")).upper().strip()
        if primera != "NO CONTESTAN":
            continue

        cc = str(r.get("CC_Alias", "")).upper().strip()
        nombres = str(r.get("Nombres", "")).strip()
        apellidos = str(r.get("Apellidos", "")).strip()
        equipo = str(r.get("Equipo", "")).strip()
        # El IMO se infiere del coordinador asignado
        coordinador = str(r.get("Coordinador", "")).strip()

        if not nombres:
            continue

        px_nombre = f"{nombres} {apellidos}".strip()

        # Agrupar por CC (cada CC tiene sus NC)
        if cc not in nc_por_imo:
            nc_por_imo[cc] = {"participantes": [], "equipo": equipo}
        nc_por_imo[cc]["participantes"].append({
            "nombre": px_nombre,
            "equipo": equipo,
        })

    return nc_por_imo


def generar_mensaje_imo(imo_nombre, participantes_nc, cc_alias, es_primera_vez=False):
    """
    Genera el mensaje para enviar al IMO.
    - Primera vez: formato template
    - Siguientes: mensaje libre conversacional
    """
    cc_info = CC_CONTACTO.get(cc_alias, {})
    cc_nombre = cc_info.get("nombre", cc_alias)
    cc_tel = cc_info.get("tel", "")

    px_list = "\n".join(f"  {i+1}. {p['nombre']}" for i, p in enumerate(participantes_nc[:15]))
    n = len(participantes_nc)
    if n > 15:
        px_list += f"\n  ... y {n-15} mas"

    if es_primera_vez:
        # Template formal
        msg = (
            f"Hola {imo_nombre},\n\n"
            f"Somos del equipo CREAR Lima. Te contactamos porque los siguientes "
            f"enrolados tuyos *no contestan* nuestras llamadas para el C1 E27:\n\n"
            f"{px_list}\n\n"
            f"Total: *{n} participantes*\n\n"
            f"Tu coordinadora es *{cc_nombre}*.\n"
            f"Contactala directamente: {cc_tel}\n\n"
            f"Por favor, responde con el nombre del participante y su situacion. "
            f"Ejemplo: _\"Juan Perez - ya confirmo, asistira\"_\n\n"
            f"Gracias por tu apoyo.\n"
            f"-- Equipo CREAR Lima"
        )
    else:
        # Mensaje libre conversacional
        msg = (
            f"Hola {imo_nombre}, buen dia.\n\n"
            f"Seguimos sin contactar a estos enrolados tuyos:\n\n"
            f"{px_list}\n\n"
            f"Necesitamos tu ayuda para confirmarlos.\n"
            f"CC: *{cc_nombre}* ({cc_tel})\n\n"
            f"Responde con el nombre y estado de cada uno."
        )

    return msg


def parsear_respuesta_imo(texto, participantes_nc):
    """
    Usa patrones para detectar sobre cual px responde el IMO.
    Retorna lista de {px_nombre, respuesta, detectado}
    """
    resultados = []
    lineas = texto.strip().split("\n")

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        mejor_match = None
        mejor_score = 0

        for px in participantes_nc:
            nombre_parts = px["nombre"].upper().split()
            score = sum(1 for part in nombre_parts if part in linea.upper())
            if score > mejor_score and score >= 1:
                mejor_score = score
                mejor_match = px

        if mejor_match:
            # Extraer la parte de respuesta (despues del nombre)
            respuesta = linea
            for part in mejor_match["nombre"].split():
                respuesta = re.sub(re.escape(part), "", respuesta, flags=re.IGNORECASE)
            respuesta = re.sub(r'^[\s\-:,]+', '', respuesta).strip()

            resultados.append({
                "px_nombre": mejor_match["nombre"],
                "respuesta": respuesta or linea,
                "detectado": True,
            })
        else:
            resultados.append({
                "px_nombre": "NO_DETECTADO",
                "respuesta": linea,
                "detectado": False,
            })

    return resultados


def guardar_respuesta_imo(sheets_client, sheet_id, imo_nombre, imo_tel,
                          px_nombre, respuesta, cc_alias):
    """Guarda la respuesta del IMO en pestaña RESPUESTAS_IMO."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        tabs = [w.title for w in sh.worksheets()]
        if "RESPUESTAS_IMO" not in tabs:
            ws = sh.add_worksheet(title="RESPUESTAS_IMO", rows=2000, cols=8)
            ws.update("A1:G1", [["Fecha", "IMO", "Tel_IMO", "Participante",
                                  "Respuesta", "CC", "Estado"]])
        else:
            ws = sh.worksheet("RESPUESTAS_IMO")

        fila = [
            ahora().strftime("%d/%m/%Y %H:%M"),
            imo_nombre,
            imo_tel,
            px_nombre,
            respuesta[:200],
            cc_alias,
            "PENDIENTE_CC",
        ]
        ws.append_row(fila, value_input_option="RAW")
        log.info(f"IMO: Respuesta guardada - {imo_nombre} sobre {px_nombre}")
        return True
    except Exception as e:
        log.error(f"IMO: Error guardando respuesta: {e}")
        return False


def obtener_respuestas_pendientes_cc(sheets_client, sheet_id, cc_alias):
    """Lee respuestas IMO pendientes para una CC especifica."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        ws = sh.worksheet("RESPUESTAS_IMO")
        rows = ws.get_all_records()
        pendientes = [r for r in rows
                      if r.get("CC", "").upper() == cc_alias.upper()
                      and r.get("Estado", "").upper() == "PENDIENTE_CC"]
        return pendientes
    except:
        return []
