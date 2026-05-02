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
}

# WhatsApp API config (misma del bot)
WA_TOKEN = os.environ.get("WA_TOKEN", "")
WA_PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")
WA_API = f"https://graph.facebook.com/v19.0/{WA_PHONE_ID}/messages"

# Template config
TEMPLATE_IMO_NAME = os.environ.get("WA_TEMPLATE_IMO", "seguimiento_imo_nc")
TEMPLATE_APROBADA = os.environ.get("TEMPLATE_IMO_APROBADA", "true").lower() == "true"

# Estado de envios (persistente)
ENVIO_LOG = os.path.join(DATA_DIR, "imo_envios.json")

def ahora():
    return datetime.now(TZ)

def formatear_nombre_peruano(texto, solo_nombre=False):
    """
    Normaliza nombres peruanos de 'APELLIDO APELLIDO NOMBRE' a 'Nombre Apellido'.
    """
    if not texto: return ""
    texto = str(texto).strip()
    if "," in texto:
        partes = [p.strip() for p in texto.split(",")]
        if len(partes) >= 2:
            nom, ape = partes[1], partes[0]
            if solo_nombre: return nom.split()[0].title()
            return f"{nom.title()} {ape.title()}"
    tokens = [t for t in texto.split() if len(t) > 1]
    if not tokens: return texto.title()
    if len(tokens) >= 3:
        nombres = " ".join(tokens[2:])
        apellidos = " ".join(tokens[:2])
        if solo_nombre: return tokens[2].title()
        return f"{nombres.title()} {apellidos.title()}"
    if len(tokens) == 2:
        if solo_nombre: return tokens[1].title()
        return f"{tokens[1].title()} {tokens[0].title()}"
    return tokens[0].title()

def en_horario():
    h = ahora().hour
    return 7 <= h <= 21

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

    # Sanitizar parámetros: Meta rechaza caracteres especiales y strings muy largos
    def _sanitize(txt, max_len=1024):
        txt = str(txt).strip()
        txt = re.sub(r'[^\w\s.,;:!?¡¿\-()/@#\n]', '', txt)  # Quitar chars raros
        return txt[:max_len] if len(txt) > max_len else txt

    imo_nombre = _sanitize(imo_nombre, 100)
    px_lista_txt = _sanitize(px_lista_txt, 900)
    cc_nombre = _sanitize(cc_nombre, 100)
    cc_tel = _sanitize(str(cc_tel), 20)

    payload = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "template",
        "template": {
            "name": TEMPLATE_IMO_NAME,
            "language": {"code": "es_PE"},
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
    Lee PRODUCTIVIDAD, filtra los que NO CONTESTAN en la última gestión 
    y que NO SE HAN SENTADO en C1 (ni desertaron).
    Retorna: {cc_alias: {imo_nombre: [px_nombres]}}
    """
    try:
        sh = sheets_client.open_by_key(sheet_id)
        ws = sh.worksheet("PRODUCTIVIDAD")
        rows = ws.get_all_records(default_blank="")
    except Exception as e:
        log.error(f"[IMO] Error leyendo Sheets PRODUCTIVIDAD: {e}")
        return {}
        
    # Deduplicar por participante quedándonos con su gestión más reciente (última fila)
    px_dict = {}
    for r in rows:
        nombres = str(r.get("NombreCompleto", "")).strip()
        apellidos = str(r.get("ApellidoCompleto", "")).strip()
        cliente_id = str(r.get("ClienteId", "")).strip()
        
        if not nombres:
            continue
            
        px_key = cliente_id if cliente_id else f"{nombres.upper()} {apellidos.upper()}"
        if px_key not in px_dict:
            px_dict[px_key] = r
        
    rows_unicos = list(px_dict.values())

    resultado = {}
    for r in rows_unicos:
        # 1. Filtro: Resultado de la Gestión = NO CONTESTA
        resultado_gestion = str(r.get("Resultado Gestión", "")).upper().strip()
        if resultado_gestion != "NO CONTESTA" and "NO CONTEST" not in resultado_gestion:
            continue
            
        # 2. Filtro: Asistencia (no sentados). Excluimos desertores y sentados
        asistencia = str(r.get("Asistencia", "")).upper().strip()
        
        # Si ya se sentó (SI, CONFIRMADO) o desertó (DESERTOR), no notificar
        if asistencia in ['SI', 'CONFIRMADO', 'SENTADO', '✓', '✔', 'ASISTIRA', 'DESERTOR']:
            continue
        if 'SENTADO' in asistencia or 'CONFIRMADO' in asistencia or 'DESERTOR' in asistencia:
            continue
            
        cc = str(r.get("Coordinador", "")).upper().strip()
        # Normalizar nombres de CC a las alias (ZULEY, DIANA, JOYCE)
        cc_alias = cc
        for alias, data in CC_CONTACTO.items():
            if data["nombre"].upper() in cc or alias in cc:
                cc_alias = alias
                break
                
        nombres = str(r.get("NombreCompleto", "")).strip()
        apellidos = str(r.get("ApellidoCompleto", "")).strip()
        if not nombres:
            continue
            
        px = f"{nombres} {apellidos}".strip()
        imo_real = str(r.get("Nombre IMO", "")).strip()
        
        if not imo_real or imo_real.lower() == "nan" or imo_real == "—":
            continue

        if cc_alias not in resultado:
            resultado[cc_alias] = {}
        if imo_real not in resultado[cc_alias]:
            resultado[cc_alias][imo_real] = []
        if px not in resultado[cc_alias][imo_real]:
            resultado[cc_alias][imo_real].append(px)

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
        dia_semana = ahora().weekday() # 0 = Lunes, 6 = Domingo
        
        if dia_semana == 0:
            return (
                f"Excelente inicio de semana {imo_nombre} 🙌\n\n"
                f"Tenemos a {n} de tus enrolados que aún no logramos contactar:\n\n"
                f"{px_txt}\n\n"
                f"¿Podrías darnos una mano revisando su estatus?\n"
                f"Comunícate con *{cc_nom}* al wa.me/{cc_tel} o responde aquí mismo con el detalle.\n"
                f"¡Vamos con todo por ese C1!"
            )
        elif dia_semana == 1:
            return (
                f"Hola {imo_nombre}, esperando que tengas un excelente día.\n\n"
                f"Seguimos en la búsqueda de estos {n} participantes de tu equipo que no contestan:\n\n"
                f"{px_txt}\n\n"
                f"Por favor, ayúdanos a ubicarlos. Tu apoyo es clave para que no se queden fuera.\n"
                f"Cualquier duda, escribe a tu CC: *{cc_nom}* (wa.me/{cc_tel}).\n"
                f"Quedo atento a tus respuestas sobre cada uno."
            )
        elif dia_semana == 2:
            return (
                f"¡Buen día {imo_nombre}! Mitad de semana y seguimos a full. 🚀\n\n"
                f"Te escribo porque hay {n} personas tuyas pendientes que no logramos ubicar:\n\n"
                f"{px_txt}\n\n"
                f"Danos una alerta rápida si ya confirmaron contigo o si necesitan apoyo extra.\n"
                f"CC asignada: *{cc_nom}* (wa.me/{cc_tel}).\n"
                f"¡Gracias por el seguimiento!"
            )
        elif dia_semana == 3:
            return (
                f"Hola {imo_nombre}, ¡el tiempo vuela y el C1 está cada vez más cerca! ⏳\n\n"
                f"Tenemos {n} de tus enrolados en estado 'No Contesta':\n\n"
                f"{px_txt}\n\n"
                f"Necesitamos tu intervención urgente para asegurar su asistencia.\n"
                f"Comunícate con ellos y dinos qué pasó, o escribe directo a *{cc_nom}* (wa.me/{cc_tel}).\n"
                f"Respondeme indicando el estatus de cada uno por favor."
            )
        elif dia_semana == 4:
            return (
                f"¡Viernes de cierre {imo_nombre}! Aún estamos a tiempo de sentar a todos. 🔥\n\n"
                f"Estos {n} participantes siguen sin responder a las llamadas:\n\n"
                f"{px_txt}\n\n"
                f"¿Lograste hablar con ellos? Por favor envíanos su estatus actualizado para sacarlos de esta lista de alertas.\n"
                f"Tu CC: *{cc_nom}* (wa.me/{cc_tel})."
            )
        elif dia_semana == 5:
            return (
                f"Hola {imo_nombre}, feliz fin de semana. No paramos hasta verlos en la sala. 💪\n\n"
                f"Aún quedan {n} enrolados tuyos sin confirmar asistencia:\n\n"
                f"{px_txt}\n\n"
                f"Apóyanos contactándolos en estos días clave. \n"
                f"Avisale a tu coordinadora *{cc_nom}* al wa.me/{cc_tel} o respóndeme por aquí la situación de cada participante."
            )
        else:
            return (
                f"¡Buen domingo {imo_nombre}! Disculpa la interrupción hoy, pero estamos afinando los últimos detalles. 🌟\n\n"
                f"Nos figuran {n} personas de tu equipo que no han contestado:\n\n"
                f"{px_txt}\n\n"
                f"Cuando tengas un momento, revísalo y déjanos un mensaje con su estado para actualizar el sistema.\n"
                f"CC: *{cc_nom}* (wa.me/{cc_tel}).\n"
                f"¡Un abrazo!"
            )


def enviar_seguimiento_diario(sheets_client, sheet_id):
    """
    Funcion principal: lee NC, cruza con IMOs, envia mensajes.
    Se ejecuta 1x al dia a las 10am.
    """
    # Límite de campaña: 9 PM del día anterior al C1 (E27 empieza el 1 de mayo)
    from datetime import datetime
    limite_campana = datetime.strptime("2026-04-30T21:00:00", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=TZ)
    if ahora() > limite_campana:
        log.info("[IMO] Campaña C1 finalizada (pasó límite 9pm día anterior). No más seguimientos automáticos.")
        return 0

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
    log.info(f"[IMO] Iniciando proceso para {len(nc_data)} CCs")
    log_to_sheets(sheets_client, sheet_id, f"Iniciando seguimiento para {len(nc_data)} coordinaciones")
    enviados = 0

    # Recorrer NC agrupados por CC
    for cc_alias, imos_dict in nc_data.items():
        cc_info = CC_CONTACTO.get(cc_alias, {})
        if not cc_info:
            continue

        # Para cada IMO con px NC en esta CC
        for imo_nc_nombre, px_list in imos_dict.items():
            if not px_list:
                continue

            # Buscar el teléfono de ESTE IMO específico en la base general
            imo_data_encontrada = None
            for i_nom, i_data in imos_tel.items():
                if i_nom.strip().upper() == imo_nc_nombre.strip().upper():
                    imo_data_encontrada = i_data
                    break
            
            if not imo_data_encontrada:
                log.warning(f"[IMO] Teléfono no encontrado para IMO: {imo_nc_nombre}")
                continue
                
            imo_nombre = imo_nc_nombre
            imo_data = imo_data_encontrada

            tel = imo_data.get("tel", "")
            if not tel:
                continue

            # Determinar cuando fue el ultimo envio
            last_sent_str = envios.get(f"{imo_nombre}_last_sent")
            if last_sent_str:
                from datetime import datetime
                last_sent = datetime.strptime(last_sent_str, "%Y-%m-%dT%H:%M:%S")
                last_sent = last_sent.replace(tzinfo=TZ)  # Fix: hacer timezone-aware
                hours_passed = (ahora() - last_sent).total_seconds() / 3600
                if hours_passed < 23:
                    continue  # No han pasado 23 horas
            
            count = envios.get(f"{imo_nombre}_count", 0)
            px_txt = "\n".join(f"{i+1}. {p}" for i, p in enumerate(px_list[:10]))
            
            # 1ra vez -> Plantilla 1 (seguimiento_imo)
            if count == 0:
                if TEMPLATE_APROBADA:
                    ok = _enviar_whatsapp_template(tel, formatear_nombre_peruano(imo_nombre), px_txt, len(px_list), cc_info["nombre"], cc_info["tel"])
                    if not ok:
                        log_to_sheets(sheets_client, sheet_id, f"Error enviando template {TEMPLATE_IMO_NAME} a {imo_nombre} ({tel})")
                else:
                    msg = generar_mensaje_imo(formatear_nombre_peruano(imo_nombre), px_list, cc_alias, True)
                    ok = _enviar_whatsapp(tel, msg)
            
            # 2da vez -> Plantilla 2 (seguimiento_imo_nc) - Pendiente de aprobación, usamos la 1 o free text
            elif count == 1:
                # Idealmente usar _enviar_whatsapp_template_nc() aquí, por ahora reusamos la 1 si se fuerza plantilla
                # Asumimos que la API permite seguimiento_imo o usamos texto libre
                msg = generar_mensaje_imo(formatear_nombre_peruano(imo_nombre), px_list, cc_alias, False)
                ok = _enviar_whatsapp(tel, msg)
            
            # 3ra+ vez -> Texto Libre en ventana de 24h
            else:
                msg = generar_mensaje_imo(formatear_nombre_peruano(imo_nombre), px_list, cc_alias, False)
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


def log_to_sheets(sheets_client, sheet_id, msg):
    """Escribe un log en la pestaña LOGS_BOT."""
    try:
        sh = sheets_client.open_by_key(sheet_id)
        tabs = [w.title for w in sh.worksheets()]
        if "LOGS_BOT" not in tabs:
            ws = sh.add_worksheet(title="LOGS_BOT", rows=1000, cols=2)
            ws.update("A1:B1", [["Fecha", "Mensaje"]])
        else:
            ws = sh.worksheet("LOGS_BOT")
        ws.append_row([ahora().strftime("%d/%m/%Y %H:%M:%S"), msg])
    except: pass

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

def enviar_recordatorios_imos(sheets_client, sheet_id):
    """
    Envia un texto libre de recordatorio a los IMOs que aun tienen NC.
    (Para uso dentro de la ventana de 24h).
    """
    from datetime import datetime
    limite_campana = datetime.strptime("2026-04-30T21:00:00", "%Y-%m-%dT%H:%M:%S").replace(tzinfo=TZ)
    if ahora() > limite_campana:
        return 0

    if not en_horario(): return 0
    nc_data = obtener_nc_por_imo(sheets_client, sheet_id)
    if not nc_data: return 0
    
    imos_tel = cargar_imos_con_telefono()
    enviados = 0
    
    for cc_alias, imos_dict in nc_data.items():
        cc_info = CC_CONTACTO.get(cc_alias, {})
        if not cc_info: continue
        for imo_nc_nombre, px_list in imos_dict.items():
            if not px_list: continue
            
            imo_data_encontrada = None
            for i_nom, i_data in imos_tel.items():
                if i_nom.strip().upper() == imo_nc_nombre.strip().upper():
                    imo_data_encontrada = i_data
                    break
            
            if not imo_data_encontrada: continue
            tel = imo_data_encontrada.get("tel", "")
            if not tel: continue
            
            msg = (
                f"⏳ *Recordatorio Rápido*\n\n"
                f"Hola {formatear_nombre_peruano(imo_nc_nombre, True)}, aún quedan {len(px_list)} enrolados tuyos que no contestan:\n"
                + "\n".join(f" - {p}" for p in px_list[:10])
                + ("\n - ... y otros más" if len(px_list) > 10 else "")
                + f"\n\nPor favor ayúdanos a contactarlos. Responde con su estado a *{cc_info['nombre']}* o por aquí."
            )
            
            ok = _enviar_whatsapp(tel, msg)
            if ok: enviados += 1
            import time; time.sleep(10)
            
    log.info(f"[IMO-RECORDATORIO] {enviados} recordatorios enviados")
    return enviados
