"""
seguimiento_imos.py — Seguimiento automatico de IMOs para px NC
================================================================
Envia mensajes WhatsApp a IMOs sobre px que no contestan.
Registra respuestas. Rutea a CCs.
"""
import os, csv, logging, re, json
from datetime import datetime
from zoneinfo import ZoneInfo
import requests as req_lib

log = logging.getLogger("CPSL.IMO")
TZ = ZoneInfo("America/Lima")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

# ── Contactos CCs (extraidos de E27_participantes_limpio.csv) ──
CC_CONTACTO = {
    "DIANA": {"nombre": "Diana Moscoso", "tel": "51912379744", "user": "dmoscoso"},
    "JOYCE": {"nombre": "Joyce Marin", "tel": "51933599903", "user": "jmarin"},
    "ZULEY": {"nombre": "Zuley Urteaga", "tel": "51933599864", "user": "zurteaga"},
}

# WhatsApp API config (misma del bot)
WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_API = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"

# Template config
TEMPLATE_IMO_NAME = os.environ.get("WA_TEMPLATE_IMO", "seguimiento_imo_nc")
TEMPLATE_APROBADA = os.environ.get("TEMPLATE_IMO_APROBADA", "false").lower() == "true"

# Estado de envios (persistente)
ENVIO_LOG = os.path.join(DATA_DIR, "imo_envios.json")

def ahora():
    return datetime.now(TZ)

def en_horario():
    h = ahora().hour
    return 9 <= h < 17

def _cargar_envios():
    try:
        if os.path.exists(ENVIO_LOG):
            with open(ENVIO_LOG) as f:
                return json.load(f)
    except: pass
    return {}

def _guardar_envios(data):
    try:
        with open(ENVIO_LOG, "w") as f:
            json.dump(data, f, indent=2)
    except: pass


def _enviar_whatsapp_template(tel, imo_nombre, px_lista_txt, total, cc_nombre, cc_tel):
    """Envia mensaje WhatsApp usando TEMPLATE aprobada por Meta (primer contacto)."""
    if not WA_TOKEN or not WA_PHONE_ID:
        log.warning("[IMO-WA] Sin WA_TOKEN o WA_PHONE_ID")
        return False
    tel = re.sub(r'[^\d]', '', str(tel))
    if not tel.startswith("51"): tel = "51" + tel

    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "template",
        "template": {
            "name": TEMPLATE_IMO_NAME,
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": imo_nombre},
                    {"type": "text", "text": px_lista_txt},
                    {"type": "text", "text": str(total)},
                    {"type": "text", "text": cc_nombre},
                    {"type": "text", "text": cc_tel},
                ]
            }]
        }
    }
    try:
        r = req_lib.post(WA_API, json=payload, timeout=15,
                         headers={"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"})
        if r.status_code in (200, 201):
            log.info(f"[IMO-WA] Template enviado a {tel[:6]}***")
            return True
        log.error(f"[IMO-WA] Template error {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log.error(f"[IMO-WA] Template error: {e}")
        return False


def _enviar_whatsapp(tel, mensaje):
    """Envia mensaje WhatsApp texto libre (follow-up dentro de ventana 24h)."""
    if not WA_TOKEN or not WA_PHONE_ID:
        log.warning("[IMO-WA] Sin WA_TOKEN o WA_PHONE_ID configurado")
        return False
    tel = re.sub(r'[^\d]', '', str(tel))
    if not tel.startswith("51"): tel = "51" + tel
    headers = {"Authorization": f"Bearer {WA_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": tel, "type": "text", "text": {"body": mensaje}}
    try:
        r = req_lib.post(WA_API, headers=headers, json=payload, timeout=15)
        if r.status_code in (200, 201):
            log.info(f"[IMO-WA] Texto enviado a {tel[:6]}***")
            return True
        log.error(f"[IMO-WA] Error {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        log.error(f"[IMO-WA] Error: {e}")
        return False


def cargar_imos_con_telefono():
    """Carga mapa IMO->telefono desde E27_participantes_limpio.csv"""
    imos = {}
    csv_path = os.path.join(BASE_DIR, "E27_participantes_limpio.csv")
    if not os.path.exists(csv_path):
        log.warning(f"[IMO] CSV no encontrado: {csv_path}")
        return imos
    try:
        with open(csv_path, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                imo = r.get("Nombre_IMO", "").strip()
                tel = r.get("Telefono_IMO", "").strip()
                cc = r.get("CC_Asignada", "").upper().strip()
                if imo and tel:
                    imos[imo] = {"tel": tel, "cc": cc}
    except Exception as e:
        log.error(f"[IMO] Error leyendo CSV: {e}")
    return imos


def obtener_nc_por_imo(sheets_client, sheet_id):
    """
    Lee GESTION_LLAMADAS y agrupa NC por CC+IMO.
    Retorna: {cc_alias: {imo_nombre: [px_nombres]}}
    """
    try:
        sh = sheets_client.open_by_key(sheet_id)
        ws = sh.worksheet("GESTION_LLAMADAS")
        rows = ws.get_all_records()
    except Exception as e:
        log.error(f"[IMO] Error leyendo Sheets: {e}")
        return {}

    resultado = {}
    for r in rows:
        primera = str(r.get("Primera_Llamada", "")).upper().strip()
        if primera != "NO CONTESTAN":
            continue
        cc = str(r.get("CC_Alias", "")).upper().strip()
        nombres = str(r.get("Nombres", "")).strip()
        apellidos = str(r.get("Apellidos", "")).strip()
        if not nombres:
            continue
        px = f"{nombres} {apellidos}".strip()
        coord = str(r.get("Coordinador", "")).strip()

        if cc not in resultado:
            resultado[cc] = {}
        # Agrupamos por coordinador como proxy de IMO asignado
        if coord not in resultado[cc]:
            resultado[cc][coord] = []
        resultado[cc][coord].append(px)

    return resultado


def generar_mensaje_imo(imo_nombre, px_nc_list, cc_alias, es_primera_vez=False):
    """Genera mensaje para IMO con lista de px NC + datos CC."""
    cc = CC_CONTACTO.get(cc_alias, {})
    cc_nom = cc.get("nombre", cc_alias)
    cc_tel = cc.get("tel", "")

    px_txt = "\n".join(f"  {i+1}. {p}" for i, p in enumerate(px_nc_list[:15]))
    n = len(px_nc_list)
    if n > 15:
        px_txt += f"\n  ... y {n-15} mas"

    if es_primera_vez:
        return (
            f"Hola {imo_nombre},\n\n"
            f"Somos del equipo CREAR Lima. Los siguientes enrolados tuyos "
            f"*no contestan* las llamadas para el C1 E27:\n\n"
            f"{px_txt}\n\n"
            f"Total: *{n} participantes*\n\n"
            f"Tu coordinadora: *{cc_nom}*\n"
            f"WhatsApp CC: wa.me/{cc_tel}\n\n"
            f"Responde con el nombre y situacion de cada uno.\n"
            f"Ej: _\"Juan Perez - ya confirmo\"_\n\n"
            f"Gracias! -- CREAR Lima"
        )
    else:
        hora = ahora().strftime("%H:%M")
        saludos = ["Buen dia", "Hola", "Saludos"]
        saludo = saludos[ahora().day % len(saludos)]
        return (
            f"{saludo} {imo_nombre},\n\n"
            f"Seguimos sin contactar a {n} enrolados tuyos:\n\n"
            f"{px_txt}\n\n"
            f"Ayudanos a confirmarlos.\n"
            f"CC: *{cc_nom}* (wa.me/{cc_tel})\n\n"
            f"Responde con nombre + estado de cada uno."
        )


def enviar_seguimiento_diario(sheets_client, sheet_id):
    """
    Funcion principal: lee NC, cruza con IMOs, envia mensajes.
    Se ejecuta 1x al dia a las 10am.
    """
    if not en_horario():
        log.info("[IMO] Fuera de horario")
        return 0

    nc_data = obtener_nc_por_imo(sheets_client, sheet_id)
    if not nc_data:
        log.info("[IMO] Sin NC pendientes")
        return 0

    imos_tel = cargar_imos_con_telefono()
    envios = _cargar_envios()
    hoy = ahora().strftime("%Y-%m-%d")
    enviados = 0

    # Recorrer NC agrupados por CC
    for cc_alias, imos_dict in nc_data.items():
        cc_info = CC_CONTACTO.get(cc_alias, {})
        if not cc_info:
            continue

        # Para cada grupo de px NC
        for coord_name, px_list in imos_dict.items():
            if not px_list:
                continue

            # Buscar IMOs que tengan esos px
            for imo_nombre, imo_data in imos_tel.items():
                # Verificar que el IMO corresponde a esta CC
                imo_cc = imo_data.get("cc", "").upper()
                # Mapear user -> alias
                cc_alias_map = {"JMARIN": "JOYCE", "DMOSCOSO": "DIANA", "ZURTEAGA": "ZULEY"}
                imo_cc_alias = cc_alias_map.get(imo_cc, imo_cc)
                if imo_cc_alias != cc_alias:
                    continue

                tel = imo_data.get("tel", "")
                if not tel:
                    continue

                # Determinar cuando fue el ultimo envio
                last_sent_str = envios.get(f"{imo_nombre}_last_sent")
                if last_sent_str:
                    from datetime import datetime
                    last_sent = datetime.strptime(last_sent_str, "%Y-%m-%dT%H:%M:%S")
                    hours_passed = (ahora() - last_sent).total_seconds() / 3600
                    if hours_passed < 23:
                        continue  # No han pasado 23 horas
                
                count = envios.get(f"{imo_nombre}_count", 0)
                px_txt = "\n".join(f"{i+1}. {p}" for i, p in enumerate(px_list[:10]))
                
                # 1ra vez -> Plantilla 1 (seguimiento_imo)
                if count == 0:
                    if TEMPLATE_APROBADA:
                        ok = _enviar_whatsapp_template(tel, imo_nombre.split()[-1], px_txt, len(px_list), cc_info["nombre"], cc_info["tel"])
                    else:
                        msg = generar_mensaje_imo(imo_nombre.split()[-1], px_list, cc_alias, True)
                        ok = _enviar_whatsapp(tel, msg)
                
                # 2da vez -> Plantilla 2 (seguimiento_imo_nc) - Pendiente de aprobación, usamos la 1 o free text
                elif count == 1:
                    # Idealmente usar _enviar_whatsapp_template_nc() aquí, por ahora reusamos la 1 si se fuerza plantilla
                    # Asumimos que la API permite seguimiento_imo o usamos texto libre
                    msg = generar_mensaje_imo(imo_nombre.split()[-1], px_list, cc_alias, False)
                    ok = _enviar_whatsapp(tel, msg)
                
                # 3ra+ vez -> Texto Libre en ventana de 24h
                else:
                    msg = generar_mensaje_imo(imo_nombre.split()[-1], px_list, cc_alias, False)
                    ok = _enviar_whatsapp(tel, msg)

                if ok:
                    envios[f"{imo_nombre}_last_sent"] = ahora().strftime("%Y-%m-%dT%H:%M:%S")
                    envios[f"{imo_nombre}_count"] = count + 1
                    enviados += 1
                    try:
                        guardar_envio_sheets(sheets_client, sheet_id, imo_nombre, tel, cc_alias, len(px_list))
                    except: pass

                # Pausa anti-spam Meta (25s entre mensajes)
                import time; time.sleep(25)

    _guardar_envios(envios)
    log.info(f"[IMO] {enviados} mensajes enviados")
    return enviados


def guardar_envio_sheets(sheets_client, sheet_id, imo, tel, cc, n_px):
    """Registra envio en pestaña SEGUIMIENTO_ENVIOS."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        tabs = [w.title for w in sh.worksheets()]
        if "SEGUIMIENTO_ENVIOS" not in tabs:
            ws = sh.add_worksheet(title="SEGUIMIENTO_ENVIOS", rows=2000, cols=6)
            ws.update("A1:F1", [["Fecha", "IMO", "Tel", "CC", "Px_NC", "Estado"]])
        else:
            ws = sh.worksheet("SEGUIMIENTO_ENVIOS")
        ws.append_row([ahora().strftime("%d/%m/%Y %H:%M"), imo, tel, cc, n_px, "ENVIADO"])
    except Exception as e:
        log.error(f"[IMO] Error guardando envio: {e}")


def parsear_respuesta_imo(texto, participantes_nc):
    """Detecta sobre cual px responde el IMO."""
    resultados = []
    for linea in texto.strip().split("\n"):
        linea = linea.strip()
        if not linea: continue
        mejor, score_max = None, 0
        for px in participantes_nc:
            parts = px.upper().split()
            score = sum(1 for p in parts if p in linea.upper())
            if score > score_max and score >= 1:
                score_max, mejor = score, px
        if mejor:
            resp = linea
            for p in mejor.split():
                resp = re.sub(re.escape(p), "", resp, flags=re.IGNORECASE)
            resp = re.sub(r'^[\s\-:,]+', '', resp).strip()
            resultados.append({"px": mejor, "respuesta": resp or linea, "ok": True})
        else:
            resultados.append({"px": "?", "respuesta": linea, "ok": False})
    return resultados


def guardar_respuesta_imo(sheets_client, sheet_id, imo, imo_tel, px, respuesta, cc):
    """Guarda respuesta IMO en pestaña RESPUESTAS_IMO."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        tabs = [w.title for w in sh.worksheets()]
        if "RESPUESTAS_IMO" not in tabs:
            ws = sh.add_worksheet(title="RESPUESTAS_IMO", rows=2000, cols=7)
            ws.update("A1:G1", [["Fecha","IMO","Tel_IMO","Participante","Respuesta","CC","Estado"]])
        else:
            ws = sh.worksheet("RESPUESTAS_IMO")
        ws.append_row([ahora().strftime("%d/%m/%Y %H:%M"), imo, imo_tel, px, respuesta[:200], cc, "PENDIENTE_CC"])
        return True
    except Exception as e:
        log.error(f"[IMO] Error: {e}")
        return False


def obtener_respuestas_pendientes_cc(sheets_client, sheet_id, cc):
    """Lee respuestas pendientes para una CC."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        ws = sh.worksheet("RESPUESTAS_IMO")
        rows = ws.get_all_records()
        return [r for r in rows if r.get("CC","").upper()==cc and r.get("Estado","").upper()=="PENDIENTE_CC"]
    except:
        return []
