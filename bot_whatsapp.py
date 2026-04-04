"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
v3 — Respuestas enroladoras mejoradas (sin IA externa)
"""

import os, re, json, threading
from flask import Flask, request, jsonify
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock

app = Flask(__name__)

# ══════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS (HTTP puro + JWT)
# ══════════════════════════════════════════════════════════════════════════
import base64, time as _time

def _make_jwt(creds_dict):
    now = int(_time.time())
    header  = base64.urlsafe_b64encode(
        json.dumps({"alg":"RS256","typ":"JWT"}).encode()).rstrip(b"=")
    payload = base64.urlsafe_b64encode(json.dumps({
        "iss": creds_dict["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now, "exp": now + 3600,
    }).encode()).rstrip(b"=")
    msg = header + b"." + payload
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        pk  = serialization.load_pem_private_key(
            creds_dict["private_key"].encode(), password=None)
        sig = pk.sign(msg, padding.PKCS1v15(), hashes.SHA256())
        return (msg + b"." + base64.urlsafe_b64encode(sig).rstrip(b"=")).decode()
    except Exception as e:
        print(f"[JWT ERROR] {e}"); return None

_sheets_token_cache = {"token": None, "exp": 0}

def get_sheets_token():
    global _sheets_token_cache
    now = int(_time.time())
    if _sheets_token_cache["token"] and now < _sheets_token_cache["exp"] - 60:
        return _sheets_token_cache["token"]
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json: return None
        creds = json.loads(creds_json)
        jwt   = _make_jwt(creds)
        if not jwt: return None
        r = req_lib.post("https://oauth2.googleapis.com/token",
            data={"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                  "assertion": jwt}, timeout=10)
        if r.status_code == 200:
            d = r.json()
            _sheets_token_cache = {"token": d["access_token"],
                                   "exp": now + d.get("expires_in", 3600)}
            return d["access_token"]
        print(f"[SHEETS TOKEN ERROR] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[SHEETS TOKEN EXCEPTION] {e}")
    return None

def registrar_en_sheets(telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return
    try:
        token = get_sheets_token()
        if not token: return
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        url   = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
                 f"/values/Hoja%201!A:H:append")
        r = req_lib.post(url,
            params={"valueInputOption": "RAW", "insertDataOption": "INSERT_ROWS"},
            json={"values": [[ahora, str(telefono), imo_nombre, mensaje,
                              respuesta_bot, estado, "", ""]]},
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"}, timeout=10)
        if r.status_code not in (200, 201):
            print(f"[SHEETS WRITE ERROR] {r.status_code}: {r.text[:200]}")
    except Exception as e:
        print(f"[SHEETS WRITE EXCEPTION] {e}")

def leer_sheet():
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return []
    try:
        token = get_sheets_token()
        if not token: return []
        url = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
               f"/values/Hoja%201!A:H")
        r = req_lib.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if r.status_code == 200:
            return r.json().get("values", [])
    except Exception as e:
        print(f"[SHEETS READ ERROR] {e}")
    return []

def actualizar_celda_sheet(fila, columna, valor):
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return
    try:
        token = get_sheets_token()
        if not token: return
        rango = f"Hoja%201!{chr(64+columna)}{fila}"
        url   = (f"https://sheets.googleapis.com/v4/spreadsheets/{sheet_id}"
                 f"/values/{rango}")
        req_lib.put(url, params={"valueInputOption": "RAW"},
            json={"values": [[valor]]},
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"}, timeout=10)
    except Exception as e:
        print(f"[SHEETS UPDATE ERROR] {e}")

# ══════════════════════════════════════════════════════════════════════════
# CONFIGURACION
# ══════════════════════════════════════════════════════════════════════════

def get_config():
    return {
        "token":         os.environ.get("WA_TOKEN", ""),
        "phone_id":      os.environ.get("WA_PHONE_ID", ""),
        "verify_token":  os.environ.get("WA_VERIFY_TOKEN", "cpsl2026"),
        "excel_path":    os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx"),
        "jose_tel":      os.environ.get("JOSE_LUIS_TEL", ""),
        "sessions_path": os.environ.get("SESSIONS_PATH", "sesiones.json"),
    }

def api_url():
    return f"https://graph.facebook.com/v19.0/{get_config()['phone_id']}/messages"

_excel_lock = threading.Lock()

# ══════════════════════════════════════════════════════════════════════════
# TEXTOS BASE
# ══════════════════════════════════════════════════════════════════════════

INFO_C1 = """Capítulo 1 — Equipo 27

Hotel José Antonio Deluxe
Calle Bellavista 133, Miraflores, Lima

*Viernes 1 de mayo*
- 09:00 am Mesa de registro (obligatorio)
- 10:00 am Inicio

*Sábado 2 de mayo*
- 09:00 am Ingreso
- 10:00 am Inicio

*Domingo 3 de mayo*
- 09:00 am Inicio
- 09:00 pm Cierre y celebración

Ropa cómoda, botella de agua.
No se permiten alimentos ni bebidas externas al salón."""

COORDINADORAS = """Coordinadoras C1 y C2:

Diana Moscoso: +51 912 379 744
Joyce Marin: +51 933 599 903
Leyla Pasquel: +51 919 502 385
Zuley Urteaga: +51 933 599 864"""

STOP_CLAUSULA = "\n\n_Si no deseas recibir mas mensajes de este numero, responde STOP._"
FIRMA = "\n\n*Comunicaciones Crear Poder Sin Limites Peru*"

# ══════════════════════════════════════════════════════════════════════════
# KEYWORDS
# ══════════════════════════════════════════════════════════════════════════

KEYWORDS = {
    "STOP": ["stop","baja","no mas mensajes","no quiero mensajes","desuscribir",
             "alto","detener","no me escriban","no escriban","no les escriban"],
    "QUIEN_ERES": ["con quien hablo","con quien tengo el gusto","quien me escribe",
                   "quien eres","de donde me escriben","que numero es este",
                   "de donde","con quien","quién"],
    "CAMBIO": ["cambio de nombre","cambiar nombre","traspaso","cambio de participante",
               "a cambio de","quiero cambiar","cambiar a","en lugar de",
               "deseo cambiar","cambiar por","sustituir","reemplazar"],
    "INFO_C1": ["horario","donde es","dónde es","direccion","dirección","fecha",
                "cuando es","cuándo es","hotel","miraflores","proximo c1",
                "próximo c1","c1 de mayo","informacion del c1","info del c1"],
    "YA_SE_SENTO": ["ya se sento","ya se sentó","ya asistio","ya asistió",
                    "ya fue","ya estuvo","ya participo","ya participó",
                    "se sento","se sentó","ya vino","ya vinieron",
                    "fue cambiada","fue cambiado","ya se sentaron",
                    "si se sento","sí se sentó","si asistió","si fue"],
    "NO_RECUERDA": ["no recuerdo","no se quien","no conozco",
                    "quien es esta persona","no tengo informacion"],
    "FALLECIO_ENFERMO": ["fallecio","falleció","murio","murió","hospitalizado",
                         "grave","accidente","gestando","embarazada","en duelo"],
    "DEVOLUCION": ["devolucion","devolución","devolver dinero","reembolso",
                   "quiero mi dinero","devuelvan","quiere su dinero"],
    "NO_INTERESADO": ["no quiere","ya no quiere","no le interesa","no interesa",
                      "desistio","desistió","no va a continuar","no continua",
                      "no continúa","no desea","se retira","no va a ir",
                      "no piensa ir","no va a asistir","no quiere.",
                      "no tiene intencion","desinteresada","desinteresado",
                      "no le gusto","no le gustó","se retiró","no quiere continuar"],
    "NO_CONTESTA": ["no contesta","no me contesta","no responde","no me responde",
                    "sin respuesta","no lo ubico","no la ubico","bloqueo",
                    "bloqueó","me bloqueo","me bloqueó","perdí el rastro",
                    "ya no tengo contacto","ya no responde","no atiende"],
    "PENDIENTE": ["pendiente","aun no se","todavia no","esta pensando",
                  "evaluando","en proceso","provincias","de viaje","fuera de lima",
                  "regresa","para esa fecha si","si estaran","sí estarán"],
    "SIGUIENTE": ["siguiente equipo","otro equipo","proximo equipo","siguiente c1",
                  "otro c1","en el proximo","en mayo","siguiente oportunidad"],
    "CONFIRMADO": ["confirma","confirmado","confirmada","confirmo","si va","sí va",
                   "va a venir","va a asistir","va al c1","se sienta",
                   "van todos","vienen todos","se sento","se sentó",
                   "si se van a sentar","tiene vuelos","vuelos comprados"],
    "VOLANTE": ["volante","flyer","invitacion","invitación","afiche","imagen del c1",
               "informacion del entrenamiento","info del entrenamiento",
               "comparte la info","comparte la informacion","mandame la info",
               "mandame el flyer","mandame el volante","compartir la informacion"],
    "CONSULTA_PX": ["ya confirmo","ya confirmó","ya confirma","confirmo ella",
                    "confirmo el","se inscribio","se inscribió","ya pago","ya pagó",
                    "esta inscrita","esta inscrito","ya esta","ya está",
                    "ya confirmas","ya lo confirma","ya la confirma",
                    "tiene lugar","tiene espacio","aparece en el sistema"],
    "GESTIONANDO": ["lo estoy gestionando","me muevo","me comunicare","voy a hablar",
                    "voy a contactar","tratare de","voy a preguntar",
                    "para darle una respuesta","estare informando",
                    "cuenten con mi acompanamiento","ahora me muevo",
                    "si estare atento","le voy a recordar","estoy en conversaciones",
                    "estoy contactandolo","seguimiento"],
}

def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t

def detectar_intencion(texto):
    t = normalizar(texto)
    orden = ["STOP","QUIEN_ERES","CAMBIO","VOLANTE","CONSULTA_PX","INFO_C1","YA_SE_SENTO","NO_RECUERDA",
             "FALLECIO_ENFERMO","DEVOLUCION","NO_INTERESADO","NO_CONTESTA",
             "PENDIENTE","SIGUIENTE","CONFIRMADO","GESTIONANDO"]
    for intent in orden:
        for kw in KEYWORDS[intent]:
            kw_n = normalizar(kw)
            patron = r'(?<![a-z])' + re.escape(kw_n) + r'(?![a-z])'
            if re.search(patron, t):
                return intent
    return None

def buscar_px_en_texto(texto, px_list):
    resultados = []
    t_norm = normalizar(texto)
    if len(px_list) == 1:
        intencion = detectar_intencion(texto)
        if intencion and intencion not in ("STOP","CAMBIO","INFO_C1","NO_RECUERDA",
                                           "FALLECIO_ENFERMO","QUIEN_ERES","DEVOLUCION",
                                           "VOLANTE","CONSULTA_PX"):
            resultados.append({"px": px_list[0], "estatus": intencion})
        return resultados
    for px in px_list:
        tokens = [p for p in px.split() if len(p) > 3]
        for token in tokens:
            token_n = normalizar(token)
            patron  = r'(?<![a-z])' + re.escape(token_n) + r'(?![a-z])'
            match   = re.search(patron, t_norm)
            if match:
                inicio    = max(0, match.start() - 15)
                fin       = min(len(texto), match.end() + 100)
                fragmento = texto[inicio:fin]
                intencion = detectar_intencion(fragmento) or detectar_intencion(texto)
                if intencion and intencion not in ("STOP","CAMBIO","INFO_C1",
                                                   "NO_RECUERDA","FALLECIO_ENFERMO",
                                                   "QUIEN_ERES","DEVOLUCION"):
                    resultados.append({"px": px, "estatus": intencion})
                break
    vistos, dedup = set(), []
    for r in resultados:
        if r["px"] not in vistos:
            vistos.add(r["px"]); dedup.append(r)
    return dedup

# ══════════════════════════════════════════════════════════════════════════
# SESIONES
# ══════════════════════════════════════════════════════════════════════════

def _sf(): return get_config()["sessions_path"]
def cargar_sesiones():
    try:
        with open(_sf(), "r", encoding="utf-8") as f: return json.load(f)
    except: return {}
def guardar_sesiones(s):
    with open(_sf(), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
def get_sesion(tel):    return cargar_sesiones().get(str(tel), {})
def set_sesion(tel, d): s = cargar_sesiones(); s[str(tel)] = d; guardar_sesiones(s)
def borrar_sesion(tel): s = cargar_sesiones(); s.pop(str(tel), None); guardar_sesiones(s)

# ══════════════════════════════════════════════════════════════════════════
# EXCEL
# ══════════════════════════════════════════════════════════════════════════

def norm_tel(tel):
    t = str(tel).strip().replace("+","").replace(" ","").replace("-","")
    if t.startswith("51") and len(t) == 11: t = t[2:]
    elif t.startswith("0") and len(t) == 10: t = t[1:]
    elif len(t) > 10 and not t.startswith("9"): t = t[-9:]
    return t

def ep(): return get_config()["excel_path"]

def cargar_px_del_imo(telefono):
    lock = FileLock(ep() + ".lock")
    with lock:
        try:
            wb = load_workbook(ep(), data_only=True, read_only=True)
            ws = wb["DATA"]
            px_list, imo_nombre = [], ""
            tel_n = norm_tel(telefono)
            for row in ws.iter_rows(min_row=2, values_only=True):
                if not row or len(row) < 7: continue
                imo_n  = str(row[0] or "").strip()
                imo_t  = norm_tel(str(row[3] or ""))
                px_n   = str(row[4] or "").strip()
                estado = str(row[6] or "").strip().upper()
                if imo_t == tel_n:
                    if not imo_nombre: imo_nombre = imo_n
                    if estado in ("PENDIENTE","ENVIADO","") and px_n:
                        px_list.append(px_n)
            wb.close()
            return imo_nombre, px_list
        except Exception as e:
            print(f"[ERROR] cargar_px: {e}"); return "", []

def actualizar_excel(resultados, telefono):
    hoy = datetime.now().strftime("%d/%m/%Y %H:%M")
    tel_n = norm_tel(telefono)
    with _excel_lock, FileLock(ep() + ".lock"):
        try:
            wb = load_workbook(ep())
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                imo_t = norm_tel(str(row[3].value or ""))
                px_c  = str(row[4].value or "").strip()
                if imo_t != tel_n: continue
                for r in resultados:
                    pa_r = normalizar(r["px"].split()[0]) if r["px"].split() else ""
                    pa_c = normalizar(px_c.split()[0]) if px_c.split() else ""
                    if normalizar(r["px"]) == normalizar(px_c) or (pa_r == pa_c and len(pa_r) > 3):
                        row[6].value = r["estatus"]
                        row[7].value = hoy; break
            wb.save(ep()); wb.close()
        except Exception as e:
            print(f"[ERROR] actualizar_excel: {e}")

def marcar_stop(telefono):
    tel_n = norm_tel(telefono)
    hoy   = datetime.now().strftime("%d/%m/%Y %H:%M")
    with _excel_lock, FileLock(ep() + ".lock"):
        try:
            wb = load_workbook(ep())
            ws = wb["DATA"]
            for row in ws.iter_rows(min_row=2):
                if not row or len(row) < 7: continue
                if norm_tel(str(row[3].value or "")) == tel_n:
                    row[6].value = "STOP"; row[7].value = hoy
                    if len(row) > 8: row[8].value = "Opt-out solicitado"
            wb.save(ep()); wb.close()
        except Exception as e:
            print(f"[ERROR] marcar_stop: {e}")

# ══════════════════════════════════════════════════════════════════════════
# WHATSAPP
# ══════════════════════════════════════════════════════════════════════════

_respuestas_enviadas = {}

def enviar_mensaje(telefono, texto):
    cfg = get_config()
    try:
        r = req_lib.post(api_url(),
            json={"messaging_product":"whatsapp","to":str(telefono),
                  "type":"text","text":{"body":texto,"preview_url":False}},
            headers={"Authorization":f"Bearer {cfg['token']}",
                     "Content-Type":"application/json"}, timeout=10)
        if r.status_code != 200:
            print(f"[WA ERROR] {r.status_code}: {r.text[:200]}")
        else:
            _respuestas_enviadas[str(telefono)] = texto
        return r.status_code == 200
    except Exception as e:
        print(f"[WA EXCEPTION] {e}"); return False

def nombre_pila(s):
    partes = re.split(r'\s+', s.strip())
    if len(partes) >= 3: return partes[2].title()
    if len(partes) >= 2: return partes[1].title()
    return partes[0].title() if partes else s

def formatear_resumen(extraidos):
    iconos = {"CONFIRMADO":"✅","SIGUIENTE":"➡️","NO_INTERESADO":"❌",
              "NO_CONTESTA":"📵","PENDIENTE":"⏳","GESTIONANDO":"🔄"}
    return "\n".join(
        f"{iconos.get(e['estatus'],'•')} {e['px']} — *{e['estatus']}*"
        for e in extraidos)

def notificar_jose_luis(imo_nombre, confirmados):
    jose = get_config()["jose_tel"]
    if not jose or not confirmados: return
    nombres = "\n".join(f"• {c['px']}" for c in confirmados)
    enviar_mensaje(jose,
        f"✅ *Nueva confirmacion C1 E27*\n\nIMO: {imo_nombre}\n\nConfirmados:\n{nombres}")

def es_confirmacion(texto):
    t = normalizar(texto)
    tokens = re.findall(r'[a-z]+', t)
    if not tokens: return False
    ok  = {"ok","dale","correcto","exacto","perfecto","listo","claro",
           "afirmativo","confirmado","confirmo","si","yes","asi"}
    neg = {"no","pero","aunque","contesta","puede","podria",
           "quiero","deseo","cambiar","espera"}
    if all(tok in ok for tok in tokens): return True
    if any(neg in t for neg in neg): return False
    if tokens[0] in ok and len(tokens) <= 3: return True
    return False

# ══════════════════════════════════════════════════════════════════════════
# RESPUESTAS ENROLADORAS
# ══════════════════════════════════════════════════════════════════════════

def r_quien_eres(pila=""):
    s = f"Hola {pila},\n\n" if pila else "Hola,\n\n"
    return (s +
        "Te contactamos de *Crear Poder Sin Limites Peru*.\n\n"
        "Somos el area de comunicaciones y estamos en seguimiento "
        "del *Capitulo 1 — Equipo 27*, que se realiza los dias "
        "*1, 2 y 3 de mayo* en el Hotel Jose Antonio Deluxe, Miraflores.\n\n"
        "Como IMO, tienes participantes con una inscripcion activa "
        "para ese entrenamiento. Queremos saber como vas con cada uno de ellos."
        + FIRMA)

def r_cambio(pila):
    return (
        f"Hola {pila},\n\n"
        "Los cambios de nombre se gestionan directamente con tu coordinadora. "
        "El *plazo limite es el miercoles previo al entrenamiento hasta las 6:00 pm* "
        "y el nuevo participante debe completar su llamada de bienvenida antes de ingresar.\n\n"
        "Comunicate con tu coordinadora para iniciar el proceso:\n\n"
        + COORDINADORAS + FIRMA)

def r_devolucion(pila):
    return (
        f"Hola {pila},\n\n"
        "En Crear Poder Sin Limites *no realizamos devoluciones* "
        "una vez efectuado el pago. El espacio esta reservado "
        "desde el momento del compromiso.\n\n"
        "Lo que aplica es que la inversion queda *activa para el siguiente "
        "equipo inmediato*. El participante tiene una nueva oportunidad "
        "de honrar su compromiso y vivir el entrenamiento.\n\n"
        "Para coordinar esto con tu coordinadora:\n\n"
        + COORDINADORAS + FIRMA)

def r_info_c1(pila):
    return (
        f"Hola {pila}, aqui tienes la informacion completa:\n\n"
        + INFO_C1 + "\n\n"
        "Para cualquier consulta adicional:\n\n"
        + COORDINADORAS + FIRMA)

def r_ya_sento(pila):
    return (
        f"Hola {pila},\n\n"
        "Gracias por informarnos. Actualizamos el registro "
        "de inmediato.\n\n"
        "Cada persona que toma la decision de sentarse "
        "da un paso que transforma su vida. Bien hecho."
        + FIRMA)

def r_no_recuerda(pila):
    return (
        f"Hola {pila},\n\n"
        "Sin problema. Si tienes alguna consulta sobre las personas "
        "de tu equipo o sobre el proceso, escribenos.\n\n"
        "Tambien puedes comunicarte directamente con tu coordinadora:\n\n"
        + COORDINADORAS + FIRMA)

def r_fallecio_enfermo(pila):
    return (
        f"Hola {pila},\n\n"
        "Recibimos tu mensaje. Lamentamos la situacion. 🙏\n\n"
        "Por favor comunicate con tu coordinadora para que "
        "puedan orientarte sobre los siguientes pasos:\n\n"
        + COORDINADORAS + FIRMA)

def r_no_interesado(pila, px_list):
    extra = ""
    if len(px_list) > 1:
        extra = ("\n\n¿Como estan tus otras personas? "
                 "Cuentanos para tener el registro completo de tu equipo.")
    return (
        f"Hola {pila},\n\n"
        "Recibido. Cada persona elige en que momento toma accion. "
        "Mientras tanto, su inscripcion sigue activa hasta el *3 de mayo*."
        + extra + FIRMA)

def r_no_contesta(pila, px_list):
    extra = ""
    if len(px_list) > 1:
        extra = ("\n\n¿Como estan tus otras personas? "
                 "Cuentanos para tener el registro completo.")
    return (
        f"Hola {pila},\n\n"
        "Entendido. Te recomendamos intentar por via telefonica directa "
        "o a traves de alguien cercano a esa persona. "
        "La inscripcion sigue activa hasta el *1 de mayo*."
        + extra + FIRMA)

def r_pendiente(pila, px_list):
    if px_list:
        lista = "\n".join(f"{i+1}. {px}" for i, px in enumerate(px_list))
        return (
            f"Hola {pila},\n\n"
            "Recibido. El C1 E27 es el *1, 2 y 3 de mayo*. "
            "Las inscripciones siguen activas.\n\n"
            "Personas pendientes de confirmar en tu equipo:\n\n"
            + lista +
            "\n\nCuando tengas una actualizacion, escribenos."
            + FIRMA)
    return (
        f"Hola {pila}, recibido.\n\n"
        "El C1 es el *1, 2 y 3 de mayo*. "
        "Cualquier novedad, escribenos de inmediato."
        + FIRMA)

def r_gestionando(pila, px_list):
    if px_list:
        lista = "\n".join(f"{i+1}. {px}" for i, px in enumerate(px_list))
        return (
            f"Hola {pila},\n\n"
            "Gracias por el seguimiento. Tu gestion como IMO "
            "es clave para que cada persona pueda tomar su decision.\n\n"
            "Personas pendientes de confirmar en tu equipo:\n\n"
            + lista +
            "\n\nEscribenos cuando tengas una actualizacion."
            + FIRMA)
    return (
        f"Hola {pila},\n\n"
        "Gracias por el seguimiento. Quedamos atentos a tu reporte."
        + FIRMA)

def r_volante(pila):
    return (
        f"Hola {pila},\n\n"
        "Aqui tienes toda la informacion del entrenamiento:\n\n"
        + INFO_C1 + "\n\n"
        "Para cualquier coordinacion adicional, comunicate "
        "directamente con tu coordinadora:\n\n"
        + COORDINADORAS + FIRMA)

def r_consulta_px(pila):
    return (
        f"Hola {pila},\n\n"
        "Este canal no tiene acceso al sistema de registros.\n\n"
        "Para confirmar la asistencia de tu participante, "
        "comunicate directamente con ella y pide que te confirme "
        "su decision de asistir al *C1 E27 — 1, 2 y 3 de mayo*.\n\n"
        "Cuando tengas esa confirmacion, escribenos y lo registramos."
        + FIRMA)

def r_no_campaña():
    return (
        "Hola,\n\n"
        "Te contactamos de *Crear Poder Sin Limites Peru*.\n\n"
        "Este canal esta destinado al seguimiento del "
        "*Capitulo 1 — Equipo 27* (1, 2 y 3 de mayo).\n\n"
        "Si deseas informacion sobre nuestros entrenamientos "
        "de transformacion personal, comunicate con nuestras coordinadoras:\n\n"
        + COORDINADORAS
        + FIRMA + STOP_CLAUSULA)

def r_pedir_fecha(pila, px_confirmados):
    nombres = "\n".join(f"• {px}" for px in px_confirmados)
    return (
        f"Hola {pila},\n\n"
        "Confirmacion registrada para:\n\n"
        + nombres +
        "\n\n¿En que dia estaran presentes?\n"
        "*(Viernes 1, Sabado 2, Domingo 3 de mayo — o los tres dias)*\n\n"
        "Recuerdales presentarse a las *9:00 am* en mesa de registro."
        + FIRMA)

def r_sin_info(pila, px_list):
    lista = "\n".join(f"{i+1}. {px}" for i, px in enumerate(px_list))
    return (
        f"Hola {pila},\n\n"
        "Estas personas de tu equipo tienen inscripcion activa "
        "para el *C1 E27 — 1, 2 y 3 de mayo*:\n\n"
        + lista +
        "\n\nIndicanos el estatus de cada una:\n\n"
        "✅ *confirma* — asistira el 1-3 de mayo\n"
        "➡️ *siguiente equipo* — asistira en otra edicion\n"
        "❌ *no quiere* — no va a continuar\n"
        "📵 *no contesta* — sin respuesta\n"
        "⏳ *pendiente* — en conversacion\n\n"
        "_Ejemplo: Jorge confirma, Maria no contesta, Pedro pendiente_"
        + STOP_CLAUSULA)

# ══════════════════════════════════════════════════════════════════════════
# LOGICA PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def procesar_mensaje(telefono, texto):
    sesion    = get_sesion(telefono)
    intencion = detectar_intencion(texto)

    # STOP
    if intencion == "STOP":
        marcar_stop(telefono)
        borrar_sesion(telefono)
        enviar_mensaje(telefono,
            "Listo. Has sido dado de baja de este canal de comunicaciones. "
            "No recibiras mas mensajes de este numero."
            + FIRMA)
        return

    # Esperando fecha
    if sesion.get("estado") == "esperando_fecha":
        fecha      = texto.strip()
        imo_nombre = sesion.get("imo_nombre", "")
        px_confirm = sesion.get("px_confirmados", [])
        with _excel_lock, FileLock(ep() + ".lock"):
            try:
                wb = load_workbook(ep())
                ws = wb["DATA"]
                tel_n = norm_tel(telefono)
                for row in ws.iter_rows(min_row=2):
                    if not row or len(row) < 9: continue
                    if norm_tel(str(row[3].value or "")) != tel_n: continue
                    px_c = str(row[4].value or "").strip()
                    for px in px_confirm:
                        if normalizar(px.split()[0]) == normalizar(px_c.split()[0]):
                            row[8].value = f"Fecha: {fecha}"
                wb.save(ep()); wb.close()
            except Exception as e:
                print(f"[ERROR] guardar fecha: {e}")
        borrar_sesion(telefono)
        notificar_jose_luis(imo_nombre, [{"px": p} for p in px_confirm])
        pila = nombre_pila(imo_nombre) if imo_nombre else ""
        enviar_mensaje(telefono,
            f"Hola {pila},\n\n"
            "Confirmacion registrada.\n\n"
            "Los esperamos en:\n"
            "*Hotel Jose Antonio Deluxe*\n"
            "Calle Bellavista 133, Miraflores\n\n"
            "Mesa de registro a las *9:00 am*. "
            "Ropa comoda y botella de agua."
            + FIRMA)
        return

    # Esperando confirmacion del resumen
    if sesion.get("estado") == "esperando_confirmacion":
        if es_confirmacion(texto):
            extraidos  = sesion.get("extraidos", [])
            imo_nombre = sesion.get("imo_nombre", "")
            actualizar_excel(extraidos, telefono)
            confirmados = [e for e in extraidos if e["estatus"] == "CONFIRMADO"]
            borrar_sesion(telefono)
            if confirmados:
                px_nombres = [e["px"] for e in confirmados]
                set_sesion(telefono, {
                    "estado": "esperando_fecha",
                    "imo_nombre": imo_nombre,
                    "px_confirmados": px_nombres,
                })
                enviar_mensaje(telefono, r_pedir_fecha(nombre_pila(imo_nombre), px_nombres))
            else:
                pila = nombre_pila(imo_nombre) if imo_nombre else ""
                enviar_mensaje(telefono,
                    f"Gracias {pila}, todo quedo registrado.\n\n"
                    "Las inscripciones siguen activas hasta el *1 de mayo*. "
                    "Si hay algun cambio en el estatus de tus personas, escribenos."
                    + FIRMA)
        else:
            borrar_sesion(telefono)
            enviar_mensaje(telefono,
                "Entendido. Por favor vuelvenos a enviar el estatus de "
                "tus personas y lo registramos correctamente."
                + STOP_CLAUSULA)
        return

    # Cargar IMO
    imo_nombre, px_list = cargar_px_del_imo(telefono)
    pila = nombre_pila(imo_nombre) if imo_nombre else ""

    if not imo_nombre:
        enviar_mensaje(telefono, r_no_campaña())
        return

    if intencion == "QUIEN_ERES":
        enviar_mensaje(telefono, r_quien_eres(pila)); return
    if intencion == "CAMBIO":
        enviar_mensaje(telefono, r_cambio(pila)); return
    if intencion == "DEVOLUCION":
        enviar_mensaje(telefono, r_devolucion(pila)); return
    if intencion == "INFO_C1":
        enviar_mensaje(telefono, r_info_c1(pila)); return
    if intencion == "YA_SE_SENTO":
        enviar_mensaje(telefono, r_ya_sento(pila)); return
    if intencion == "NO_RECUERDA":
        enviar_mensaje(telefono, r_no_recuerda(pila)); return
    if intencion == "FALLECIO_ENFERMO":
        enviar_mensaje(telefono, r_fallecio_enfermo(pila)); return
    if intencion == "VOLANTE":
        enviar_mensaje(telefono, r_volante(pila)); return

    if intencion == "CONSULTA_PX":
        enviar_mensaje(telefono, r_consulta_px(pila)); return

    if intencion == "GESTIONANDO":
        enviar_mensaje(telefono, r_gestionando(pila, px_list)); return

    if not px_list:
        enviar_mensaje(telefono,
            f"Hola {pila},\n\n"
            "Ya tienes el estatus registrado para todas tus personas.\n\n"
            "Si hay algun cambio en el estatus antes del *1 de mayo*, "
            "escribenos y lo actualizamos."
            + FIRMA)
        return

    extraidos = buscar_px_en_texto(texto, px_list)

    if not extraidos:
        if intencion == "NO_INTERESADO":
            enviar_mensaje(telefono, r_no_interesado(pila, px_list)); return
        if intencion == "NO_CONTESTA":
            enviar_mensaje(telefono, r_no_contesta(pila, px_list)); return
        if intencion == "PENDIENTE":
            enviar_mensaje(telefono, r_pendiente(pila, px_list)); return
        if intencion == "SIGUIENTE":
            enviar_mensaje(telefono,
                f"Hola {pila},\n\n"
                "Recibido. Las inscripciones siguen activas para el siguiente equipo. "  
                "Si alguna persona de tu equipo puede asistir el "
                "*1, 2 o 3 de mayo*, aun hay lugar.\n\n"
                "Escribenos cuando tengas una actualizacion."
                + FIRMA); return
        enviar_mensaje(telefono, r_sin_info(pila, px_list))
        return

    set_sesion(telefono, {
        "estado": "esperando_confirmacion",
        "imo_nombre": imo_nombre,
        "px_list": px_list,
        "extraidos": extraidos,
    })
    no_mencionados = [
        px for px in px_list
        if not any(
            normalizar(px.split()[0]) == normalizar(e["px"].split()[0])
            for e in extraidos if px.split() and e["px"].split())
    ]
    msg = f"Perfecto {pila}, registre lo siguiente:\n\n{formatear_resumen(extraidos)}"
    if no_mencionados:
        faltantes = "\n".join(f"• {px}" for px in no_mencionados)
        msg += f"\n\n⚠️ Faltaron:\n{faltantes}\nPuedes incluirlas en tu siguiente mensaje."
    msg += "\n\n¿Esta correcto? Responde *SI* para confirmar o indícanos los cambios."
    enviar_mensaje(telefono, msg)

# ══════════════════════════════════════════════════════════════════════════
# RESPUESTAS MANUALES
# ══════════════════════════════════════════════════════════════════════════

def enviar_respuestas_manuales():
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id: return
    try:
        rows = leer_sheet()
        for i, row in enumerate(rows[1:], start=2):
            if len(row) < 7: continue
            telefono = str(row[1]).strip()
            resp_man = str(row[6]).strip()
            enviado  = str(row[7]).strip() if len(row) > 7 else ""
            if not telefono or not resp_man or enviado == "ENVIADO": continue
            ok = enviar_mensaje(telefono, resp_man)
            if ok:
                actualizar_celda_sheet(i, 8, "ENVIADO")
                print(f"[MANUAL SENT] {telefono}: {resp_man[:50]}")
    except Exception as e:
        print(f"[MANUAL ERROR] {e}")

def hilo_respuestas_manuales():
    import time
    while True:
        try: enviar_respuestas_manuales()
        except Exception as e: print(f"[HILO ERROR] {e}")
        time.sleep(120)

_hilo = threading.Thread(target=hilo_respuestas_manuales, daemon=True)
_hilo.start()
print("✅ Hilo de respuestas manuales iniciados")

# ══════════════════════════════════════════════════════════════════════════
# ENDPOINTS FLASK
# ══════════════════════════════════════════════════════════════════════════

@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode, token, challenge = (request.args.get(k) for k in
        ["hub.mode","hub.verify_token","hub.challenge"])
    if mode == "subscribe" and token == get_config()["verify_token"]:
        return challenge, 200
    return "Token invalido", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json(silent=True)
    if not data: return jsonify({"status":"ok"}), 200
    try:
        changes  = data["entry"][0]["changes"][0]["value"]
        if "messages" not in changes: return jsonify({"status":"ok"}), 200
        msg      = changes["messages"][0]
        telefono = msg["from"]
        tipo     = msg.get("type","")
        if tipo == "text":
            texto = msg["text"]["body"]
            print(f"[IN] {telefono}: {texto[:100]}")
            imo_nombre_sheet, _ = cargar_px_del_imo(telefono)
            procesar_mensaje(telefono, texto)
            respuesta_enviada = _respuestas_enviadas.pop(str(telefono), "")
            threading.Thread(
                target=registrar_en_sheets,
                args=(telefono, imo_nombre_sheet, texto,
                      respuesta_enviada[:500] if respuesta_enviada else "", ""),
                daemon=True).start()
        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono,
                "Por favor responde con texto para que podamos "
                "registrar correctamente tu reporte. " + ("No procesamos mensajes de voz."
                if tipo=="audio" else "No procesamos archivos multimedia."))
    except (KeyError, IndexError, TypeError) as e:
        print(f"[ERROR] Webhook: {e}")
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status():
    cfg = get_config()
    return jsonify({
        "status": "activo", "version": "v3",
        "sesiones_activas": len(cargar_sesiones()),
        "excel_existe": os.path.exists(cfg["excel_path"]),
        "token_ok": bool(cfg["token"]),
        "hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }), 200

@app.route("/sesiones", methods=["GET"])
def ver_sesiones():
    return jsonify(cargar_sesiones()), 200

@app.route("/sesiones/<telefono>", methods=["DELETE"])
def borrar_sesion_endpoint(telefono):
    borrar_sesion(telefono)
    return jsonify({"borrado": telefono}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cfg  = get_config()
    print(f"Bot CPSL v3 — puerto {port}")
    print(f"Excel   : {cfg['excel_path']}")
    print(f"PhoneID : {cfg['phone_id'] or 'NO CONFIGURADO'}")
    print(f"Token   : {'OK' if cfg['token'] else 'NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=port, debug=False)
