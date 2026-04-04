"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú
"""

import os, re, json, threading
from flask import Flask, request, jsonify
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock

app = Flask(__name__)

# ── Google Sheets ──────────────────────────────────────────────────────────
def get_sheets_client():
    """Crea cliente gspread usando las credenciales del entorno."""
    try:
        import gspread
        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json:
            return None
        creds_dict = json.loads(creds_json)
        gc = gspread.service_account_from_dict(creds_dict)
        return gc
    except Exception as e:
        print(f"[SHEETS ERROR] {e}")
        return None

def registrar_en_sheets(telefono, imo_nombre, mensaje, respuesta_bot, estado=""):
    """Agrega una fila al Google Sheet."""
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id:
        return
    try:
        gc = get_sheets_client()
        if not gc:
            return
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M")
        ws.append_row([ahora, str(telefono), imo_nombre, mensaje,
                       respuesta_bot, estado, "", ""])
    except Exception as e:
        print(f"[SHEETS WRITE ERROR] {e}")

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

# ── Datos de la campaña ────────────────────────────────────────────────────
INFO_C1 = """📅 *Capítulo 1 — Equipo 27*

📍 Hotel José Antonio Deluxe
Calle Bellavista 133, Miraflores, Lima

🗓 *Viernes 1 de mayo*
• 09:00 am — Mesa de registro (obligatorio)
• 10:00 am — Inicio
• 10:00 pm — Cierre aproximado

🗓 *Sábado 2 de mayo*
• 09:00 am — Ingreso
• 10:00 am — Inicio
• 10:00 pm — Cierre aproximado

🗓 *Domingo 3 de mayo*
• 09:00 am — Inicio
• 09:00 pm — Cierre y celebración

👕 Ropa cómoda y abrigo ligero
💧 Trae tu botella de agua
🚫 No se permiten alimentos ni bebidas externas al salón"""

POLITICA_CAMBIO = """🔄 *Política de cambio de nombre*

Los cambios de titularidad son excepcionales y aplican solo en casos de fuerza mayor autorizados por gerencia.

*Condiciones:*
• Solo aplica si el participante no está "en juego" (no ha iniciado proceso)
• El cambio debe gestionarse a través del IMO ante la coordinación
• *Deadline: miércoles previo al entrenamiento hasta las 6:00 pm*
• No se aceptan cambios en la puerta del hotel el día viernes
• El nuevo participante debe pasar por su llamada de bienvenida obligatoria

Para gestionar un cambio, comunícate con tu coordinadora:"""

POLITICA_DEVOLUCION = """💼 *Política de inversión*

En Crear Poder Sin Límites no realizamos devoluciones bajo ninguna circunstancia una vez efectuado el pago. El espacio en el salón está asegurado desde el momento del pago.

Si el participante no puede asistir a su equipo inscrito, su inversión queda congelada para el siguiente equipo inmediato. Si tampoco asiste en esa siguiente edición, pierde la inversión definitivamente.

Para consultas comunícate con tu coordinadora:"""

COORDINADORAS = """👩‍💼 *Coordinadoras Capítulo 1 y 2:*

• Diana Moscoso: +51 912 379 744
• Joyce Marín: +51 933 599 903
• Leyla Pasquel: +51 919 502 385
• Zuley Urteaga: +51 933 599 864"""

STOP_CLAUSULA = "\n\nSi no deseas recibir más mensajes de este número, responde STOP."

# ── Normalización de teléfonos ─────────────────────────────────────────────
def norm_tel(tel):
    t = str(tel).strip().replace("+","").replace(" ","").replace("-","")
    if t.startswith("51") and len(t) == 11:
        t = t[2:]
    elif t.startswith("0") and len(t) == 10:
        t = t[1:]
    elif len(t) > 10 and not t.startswith("9"):
        t = t[-9:]
    return t

# ── Keywords ───────────────────────────────────────────────────────────────
KEYWORDS = {
    "STOP": ["stop","baja","no mas mensajes","no quiero mensajes","desuscribir"],
    "CAMBIO": ["cambio de nombre","cambiar nombre","traspaso","cambio de participante",
               "a cambio de","quiero cambiar","cambiar a","en lugar de"],
    "INFO_C1": ["información del c1","info del c1","horario","dónde es","donde es",
                "dirección","fecha","cuando es","cuándo es","hotel","miraflores",
                "siguiente c1","próximo c1","proximo c1","c1 de mayo"],
    "YA_SE_SENTO": ["ya se sentó","ya asistió","ya fue","ya estuvo","ya lo hizo",
                    "ya la hizo","ya participo","ya participó","ya se sentaron"],
    "NO_RECUERDA": ["no recuerdo","no sé quién","no se quien","no conozco",
                    "quién es","quien es esta persona","no tengo información"],
    "FALLECIO_ENFERMO": ["falleció","fallecio","murió","murio","está muy enfermo",
                         "esta muy enfermo","hospitalizado","grave","accidente"],
    "NO INTERESADO": ["no quiere","ya no quiere","no le interesa","no interesa",
                      "desistio","desistió","no va a continuar","no continua",
                      "no continúa","no desea","se retira","no seguira",
                      "no seguirá","no quiere continuar","decidio no","decidió no",
                      "no va a ir","no piensa ir","no va a asistir"],
    "NO CONTESTA": ["no contesta","no me contesta","no contesto","no responde",
                    "no me responde","sin respuesta","no lo ubico","no la ubico",
                    "no lo encuentro","no la encuentro","no atiende","ilocalizable",
                    "numero malo","número malo","telefono malo","fuera de cobertura"],
    "PENDIENTE": ["pendiente","aun no se","aún no sé","todavia no","todavía no",
                  "esta pensando","está pensando","evaluando","conversando con",
                  "lo estoy hablando","seguimos hablando","en proceso","me avisara"],
    "SIGUIENTE": ["siguiente equipo","otro equipo","proximo equipo","próximo equipo",
                  "siguiente c1","otro c1","en el proximo","en el próximo"],
    "CONFIRMADO": ["confirma ","confirmado","confirmada","confirmo","si va","sí va",
                   "si viene","sí viene","asistira","asistirá","se va a sentar",
                   "va a venir","va a asistir","va al c1","se sienta",
                   "listo para el","lista para el","van todos","vienen todos",
                   "se sento","se sentó","ya va","ya viene"],
}

def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t

def detectar_intencion(texto):
    """Detecta la intención principal del mensaje."""
    t = normalizar(texto)
    # Orden de prioridad
    orden = ["STOP","CAMBIO","INFO_C1","YA_SE_SENTO","NO_RECUERDA",
             "FALLECIO_ENFERMO","NO INTERESADO","NO CONTESTA",
             "PENDIENTE","SIGUIENTE","CONFIRMADO"]
    for intencion in orden:
        for kw in KEYWORDS[intencion]:
            kw_n = normalizar(kw)
            patron = r'(?<![a-z])' + re.escape(kw_n) + r'(?![a-z])'
            if re.search(patron, t):
                return intencion
    return None

def buscar_px_en_texto(texto, px_list):
    """Extrae {px, estatus} del texto libre."""
    resultados = []
    t_norm = normalizar(texto)

    if len(px_list) == 1:
        intencion = detectar_intencion(texto)
        if intencion and intencion not in ("STOP","CAMBIO","INFO_C1",
                                           "NO_RECUERDA","FALLECIO_ENFERMO"):
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
                                                   "NO_RECUERDA","FALLECIO_ENFERMO"):
                    resultados.append({"px": px, "estatus": intencion})
                break

    vistos, dedup = set(), []
    for r in resultados:
        if r["px"] not in vistos:
            vistos.add(r["px"])
            dedup.append(r)
    return dedup

# ── Sesiones ───────────────────────────────────────────────────────────────
def _sf():
    return get_config()["sessions_path"]

def cargar_sesiones():
    try:
        with open(_sf(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_sesiones(s):
    with open(_sf(), "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)

def get_sesion(tel):
    return cargar_sesiones().get(str(tel), {})

def set_sesion(tel, datos):
    s = cargar_sesiones(); s[str(tel)] = datos; guardar_sesiones(s)

def borrar_sesion(tel):
    s = cargar_sesiones(); s.pop(str(tel), None); guardar_sesiones(s)

# ── Excel ──────────────────────────────────────────────────────────────────
def ep():
    return get_config()["excel_path"]

def cargar_px_del_imo(telefono):
    lock = FileLock(ep() + ".lock")
    with lock:
        try:
            wb     = load_workbook(ep(), data_only=True, read_only=True)
            ws     = wb["DATA"]
            px_list, imo_nombre = [], ""
            tel_n  = norm_tel(telefono)
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
    hoy   = datetime.now().strftime("%d/%m/%Y %H:%M")
    tel_n = norm_tel(telefono)
    cambios = 0
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
                    if normalizar(r["px"]) == normalizar(px_c) or \
                       (pa_r == pa_c and len(pa_r) > 3):
                        row[6].value = r["estatus"]
                        row[7].value = hoy
                        cambios += 1; break
            wb.save(ep()); wb.close()
        except Exception as e:
            print(f"[ERROR] actualizar_excel: {e}")
    return cambios

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
                    row[6].value = "STOP"
                    row[7].value = hoy
                    if len(row) > 8:
                        row[8].value = "Opt-out solicitado por IMO"
            wb.save(ep()); wb.close()
        except Exception as e:
            print(f"[ERROR] marcar_stop: {e}")

# ── WhatsApp ───────────────────────────────────────────────────────────────
# Diccionario global para rastrear respuestas enviadas
_respuestas_enviadas = {}

def enviar_mensaje(telefono, texto):
    cfg = get_config()
    payload = {"messaging_product":"whatsapp","to":str(telefono),
               "type":"text","text":{"body":texto,"preview_url":False}}
    headers = {"Authorization":f"Bearer {cfg['token']}",
               "Content-Type":"application/json"}
    try:
        r = req_lib.post(api_url(), json=payload, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"[WA ERROR] {r.status_code}: {r.text[:200]}")
        else:
            # Guardar respuesta enviada para registrarla en Sheets
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
    iconos = {"CONFIRMADO":"✅","SIGUIENTE":"➡️",
              "NO INTERESADO":"❌","NO CONTESTA":"📵","PENDIENTE":"⏳"}
    return "\n".join(f"{iconos.get(e['estatus'],'•')} {e['px']} — *{e['estatus']}*"
                     for e in extraidos)

def notificar_jose_luis(imo_nombre, confirmados):
    jose = get_config()["jose_tel"]
    if not jose or not confirmados: return
    nombres = "\n".join(f"• {c['px']}" for c in confirmados)
    enviar_mensaje(jose,
        f"✅ *Nueva confirmación C1 E27*\n\nIMO: {imo_nombre}\n\nConfirmados:\n{nombres}")

def es_confirmacion(texto):
    t = normalizar(texto)
    tokens = re.findall(r'[a-zaeioun]+', t)
    if not tokens: return False
    palabras_ok  = {"ok","dale","correcto","exacto","perfecto","listo",
                    "claro","afirmativo","confirmado","confirmo","si","sí"}
    palabras_neg = {"no","pero","aunque","llam","contesta","puede","podria",
                    "quiero","deseo","puedes","dices","espera"}
    if all(tok in palabras_ok for tok in tokens): return True
    if any(neg in t for neg in palabras_neg): return False
    if tokens[0] in palabras_ok and len(tokens) <= 3: return True
    return False

# ── Respuestas especiales ──────────────────────────────────────────────────
def respuesta_cambio(pila):
    return (
        f"Hola {pila}, gracias por escribirnos.\n\n"
        f"En Crear Poder Sin Límites no realizamos cambios de nombre. "
        f"El espacio en el salón es personal e intransferible.\n\n"
        f"Para cualquier consulta sobre tu proceso, comunícate con tu coordinadora:\n\n"
        f"{COORDINADORAS}\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )
def respuesta_info_c1(pila):
    return (
        f"Hola {pila}, con gusto te compartimos la información completa:\n\n"
        f"{INFO_C1}\n\n"
        f"Recuerda: *el C1 E27 es el único disponible en esta campaña*. "
        f"No hay próxima edición programada para este ciclo.\n\n"
        f"Para consultas adicionales:\n{COORDINADORAS}\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )

def respuesta_ya_sento(pila):
    return (
        f"Hola {pila}, muchas gracias por informarnos. 🙏\n\n"
        f"Revisaremos el sistema y actualizaremos el registro. "
        f"Un abrazo y seguimos en contacto.\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )

def respuesta_no_recuerda(pila):
    return (
        f"Hola {pila}, no hay problema. 😊\n\n"
        f"¿Cómo podemos apoyarte? Si tienes alguna duda sobre las personas "
        f"de tu equipo o sobre el proceso, con gusto te orientamos.\n\n"
        f"También puedes comunicarte directamente con tu coordinadora:\n"
        f"{COORDINADORAS}\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )

def respuesta_fallecio_enfermo(pila):
    return (
        f"Hola {pila}, lamentamos mucho la situación. 🙏\n\n"
        f"Por favor comunícate directamente con tu coordinadora "
        f"para que puedan acompañarte y orientarte en este caso:\n\n"
        f"{COORDINADORAS}\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )

def respuesta_no_campaña(telefono):
    return (
        f"Hola, gracias por escribirnos. 😊\n\n"
        f"Este canal es exclusivo para la gestión del *Capítulo 1 — Equipo 27*.\n\n"
        f"Si deseas información sobre nuestros entrenamientos o inscribirte, "
        f"con mucho gusto te atendemos a través de nuestras coordinadoras:\n\n"
        f"{COORDINADORAS}\n\n"
        f"¡Será un placer acompañarte en este proceso de transformación! 🚀\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
        + STOP_CLAUSULA
    )

def respuesta_pedir_fecha(pila, px_confirmados):
    nombres = "\n".join(f"• {px}" for px in px_confirmados)
    return (
        f"Excelente {pila}. 🎉\n\n"
        f"Nos alegra mucho saberlo. Las siguientes personas confirman su asistencia:\n\n"
        f"{nombres}\n\n"
        f"¿Nos puedes indicar en qué fecha exacta estarán presentes?\n"
        f"*(Viernes 1, Sábado 2 o Domingo 3 de mayo — o los tres días)*\n\n"
        f"Comunicaciones Crear Poder Sin Límites Perú"
    )

# ── Lógica principal ───────────────────────────────────────────────────────
def procesar_mensaje(telefono, texto):
    """Procesa el mensaje y devuelve el texto de la respuesta enviada."""
    _respuestas = []
    _enviar_original = enviar_mensaje

    def _enviar_tracked(tel, msg):
        _respuestas.append(msg)
        return _enviar_original(tel, msg)

    # Patch local de enviar_mensaje
    import builtins
    _globals = globals()
    _globals['_enviar_tracked_fn'] = _enviar_tracked

    t_norm = normalizar(texto)
    sesion = get_sesion(telefono)
    intencion_global = detectar_intencion(texto)

    # STOP
    if intencion_global == "STOP":
        marcar_stop(telefono)
        borrar_sesion(telefono)
        enviar_mensaje(telefono,
            "Has sido dado de baja de nuestras comunicaciones. "
            "No recibirás más mensajes de este número.\n\n"
            "Comunicaciones Crear Poder Sin Límites Perú")
        return

    # Esperando fecha de confirmación
    if sesion.get("estado") == "esperando_fecha":
        fecha = texto.strip()
        imo_nombre = sesion.get("imo_nombre","")
        px_confirmados = sesion.get("px_confirmados",[])
        # Guardar fecha en observaciones
        with _excel_lock, FileLock(ep() + ".lock"):
            try:
                wb = load_workbook(ep())
                ws = wb["DATA"]
                tel_n = norm_tel(telefono)
                for row in ws.iter_rows(min_row=2):
                    if not row or len(row) < 9: continue
                    if norm_tel(str(row[3].value or "")) != tel_n: continue
                    px_c = str(row[4].value or "").strip()
                    for px in px_confirmados:
                        if normalizar(px.split()[0]) == normalizar(px_c.split()[0]):
                            row[8].value = f"Fecha: {fecha}"
                wb.save(ep()); wb.close()
            except Exception as e:
                print(f"[ERROR] guardar fecha: {e}")
        borrar_sesion(telefono)
        notificar_jose_luis(imo_nombre, [{"px": p} for p in px_confirmados])
        enviar_mensaje(telefono,
            f"Perfecto, registrado. ✅\n\n"
            f"Esperamos verles el *{fecha}* en el Hotel José Antonio Deluxe, "
            f"Calle Bellavista 133, Miraflores.\n\n"
            f"Recuérdales llegar a las *9:00 am* para el registro. "
            f"Ropa cómoda y botella de agua. 💪\n\n"
            f"Comunicaciones Crear Poder Sin Límites Perú")
        return

    # Esperando confirmación del resumen
    if sesion.get("estado") == "esperando_confirmacion":
        if es_confirmacion(texto):
            extraidos = sesion.get("extraidos", [])
            actualizar_excel(extraidos, telefono)
            confirmados = [e for e in extraidos if e["estatus"] == "CONFIRMADO"]
            borrar_sesion(telefono)
            if confirmados:
                px_nombres = [e["px"] for e in confirmados]
                set_sesion(telefono, {
                    "estado": "esperando_fecha",
                    "imo_nombre": sesion.get("imo_nombre",""),
                    "px_confirmados": px_nombres,
                })
                enviar_mensaje(telefono,
                    respuesta_pedir_fecha(
                        nombre_pila(sesion.get("imo_nombre","")),
                        px_nombres))
            else:
                enviar_mensaje(telefono,
                    f"Gracias {nombre_pila(sesion.get('imo_nombre',''))}. "
                    f"Quedamos atentos a cualquier cambio.\n\n"
                    f"Comunicaciones Crear Poder Sin Límites Perú")
        else:
            borrar_sesion(telefono)
            enviar_mensaje(telefono,
                "Entendido. Por favor vuelve a enviarnos el estatus completo "
                "de tus personas y lo registramos correctamente." + STOP_CLAUSULA)
        return

    # Cargar IMO
    imo_nombre, px_list = cargar_px_del_imo(telefono)
    pila = nombre_pila(imo_nombre) if imo_nombre else ""

    # No es de la campaña
    if not imo_nombre:
        enviar_mensaje(telefono, respuesta_no_campaña(telefono))
        return

    # Intenciones especiales que no requieren lista de px
    if intencion_global == "CAMBIO":
        enviar_mensaje(telefono, respuesta_cambio(pila))
        return

    if intencion_global == "INFO_C1":
        enviar_mensaje(telefono, respuesta_info_c1(pila))
        return

    if intencion_global == "YA_SE_SENTO":
        enviar_mensaje(telefono, respuesta_ya_sento(pila))
        return

    if intencion_global == "NO_RECUERDA":
        enviar_mensaje(telefono, respuesta_no_recuerda(pila))
        return

    if intencion_global == "FALLECIO_ENFERMO":
        enviar_mensaje(telefono, respuesta_fallecio_enfermo(pila))
        return

    # Sin px pendientes
    if not px_list:
        enviar_mensaje(telefono,
            f"Hola {pila}. Ya tienes el estatus registrado para todas tus personas. "
            f"Si hay algún cambio cuéntanos y lo actualizamos.\n\n"
            f"Comunicaciones Crear Poder Sin Límites Perú")
        return

    # Extraer estatus del texto
    extraidos = buscar_px_en_texto(texto, px_list)

    if not extraidos:
        lista_px = "\n".join(f"{i+1}. {px}" for i, px in enumerate(px_list))
        enviar_mensaje(telefono,
            f"Hola {pila}, gracias por responder. 😊\n\n"
            f"Tienes estas personas pendientes:\n\n"
            f"{lista_px}\n\n"
            f"Por favor indícanos el estatus de cada uno usando estas palabras:\n\n"
            f"✅ *confirma* — va a sentarse el 1-3 de mayo\n"
            f"➡️ *siguiente equipo* — se sienta en otro equipo\n"
            f"❌ *no quiere* — no va a continuar\n"
            f"📵 *no contesta* — no has podido ubicarle\n"
            f"⏳ *pendiente* — aún conversando\n\n"
            f"Ejemplo: _Jorge confirma, María no contesta, Pedro pendiente_"
            + STOP_CLAUSULA)
        return

    # Resumen y confirmar
    set_sesion(telefono, {
        "estado":     "esperando_confirmacion",
        "imo_nombre": imo_nombre,
        "px_list":    px_list,
        "extraidos":  extraidos,
    })

    no_mencionados = [
        px for px in px_list
        if not any(
            normalizar(px.split()[0]) == normalizar(e["px"].split()[0])
            for e in extraidos if px.split() and e["px"].split()
        )
    ]

    msg = f"Perfecto {pila}, registré lo siguiente:\n\n{formatear_resumen(extraidos)}"
    if no_mencionados:
        faltantes = "\n".join(f"• {px}" for px in no_mencionados)
        msg += f"\n\n⚠️ No mencionaste a:\n{faltantes}\nPuedes incluirlos en tu siguiente mensaje."
    msg += "\n\n¿Está correcto? Responde *SÍ* para confirmar o corrígeme lo que necesites."
    enviar_mensaje(telefono, msg)

# ── Endpoints ──────────────────────────────────────────────────────────────
@app.route("/webhook", methods=["GET"])
def verificar_webhook():
    mode, token, challenge = (request.args.get(k) for k in
        ["hub.mode","hub.verify_token","hub.challenge"])
    if mode == "subscribe" and token == get_config()["verify_token"]:
        print("✅ Webhook verificado")
        return challenge, 200
    return "Token inválido", 403

@app.route("/webhook", methods=["POST"])
def recibir_mensaje():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status":"ok"}), 200
    try:
        changes = data["entry"][0]["changes"][0]["value"]
        if "messages" not in changes:
            return jsonify({"status":"ok"}), 200
        msg      = changes["messages"][0]
        telefono = msg["from"]
        tipo     = msg.get("type","")
        if tipo == "text":
            texto = msg["text"]["body"]
            print(f"[IN] {telefono}: {texto[:100]}")
            # Cargar nombre del IMO
            imo_nombre_sheet, _ = cargar_px_del_imo(telefono)
            # Procesar mensaje
            procesar_mensaje(telefono, texto)
            # Obtener respuesta enviada y registrar en Sheets
            respuesta_enviada = _respuestas_enviadas.pop(str(telefono), "")
            import threading as _th
            _th.Thread(
                target=registrar_en_sheets,
                args=(telefono, imo_nombre_sheet, texto,
                      respuesta_enviada[:500] if respuesta_enviada else "", ""),
                daemon=True
            ).start()
        elif tipo in ("audio","image","document","video","sticker"):
            enviar_mensaje(telefono,
                "Por favor responde con texto. No podemos procesar " +
                ("mensajes de voz." if tipo=="audio" else "archivos multimedia."))
    except (KeyError, IndexError, TypeError) as e:
        print(f"[ERROR] Webhook: {e}")
    return jsonify({"status":"ok"}), 200

@app.route("/status", methods=["GET"])
def status():
    cfg = get_config()
    return jsonify({
        "status":           "activo",
        "sesiones_activas": len(cargar_sesiones()),
        "excel_existe":     os.path.exists(cfg["excel_path"]),
        "token_ok":         bool(cfg["token"]),
        "phone_ok":         bool(cfg["phone_id"]),
        "hora":             datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }), 200

@app.route("/sesiones", methods=["GET"])
def ver_sesiones():
    return jsonify(cargar_sesiones()), 200

@app.route("/sesiones/<telefono>", methods=["DELETE"])
def borrar_sesion_endpoint(telefono):
    borrar_sesion(telefono)
    return jsonify({"borrado": telefono}), 200


def enviar_respuestas_manuales():
    """Revisa el Sheet cada 2 minutos y envía respuestas manuales pendientes."""
    sheet_id = os.environ.get("SHEET_ID", "")
    if not sheet_id:
        return
    try:
        gc = get_sheets_client()
        if not gc:
            return
        sh = gc.open_by_key(sheet_id)
        ws = sh.sheet1
        rows = ws.get_all_values()
        for i, row in enumerate(rows[1:], start=2):  # saltar encabezado
            if len(row) < 7: continue
            telefono = str(row[1]).strip()
            respuesta_manual = str(row[6]).strip()
            enviado = str(row[7]).strip() if len(row) > 7 else ""
            if not telefono or not respuesta_manual or enviado == "ENVIADO":
                continue
            # Enviar mensaje manual
            ok = enviar_mensaje(telefono, respuesta_manual)
            if ok:
                ws.update_cell(i, 8, "ENVIADO")
                print(f"[MANUAL SENT] {telefono}: {respuesta_manual[:50]}")
    except Exception as e:
        print(f"[MANUAL ERROR] {e}")

def hilo_respuestas_manuales():
    """Hilo que revisa respuestas manuales cada 2 minutos."""
    import time
    while True:
        try:
            enviar_respuestas_manuales()
        except Exception as e:
            print(f"[HILO ERROR] {e}")
        time.sleep(120)  # cada 2 minutos

# Arrancar hilo de respuestas manuales al importar
import threading as _threading
_hilo = _threading.Thread(target=hilo_respuestas_manuales, daemon=True)
_hilo.start()
print("✅ Hilo de respuestas manuales iniciado")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cfg  = get_config()
    print(f"🤖 Bot CPSL — puerto {port}")
    print(f"📁 Excel   : {cfg['excel_path']}")
    print(f"📱 PhoneID : {cfg['phone_id'] or '⚠️ NO CONFIGURADO'}")
    print(f"🔑 Token   : {'✅' if cfg['token'] else '⚠️ NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=port, debug=False)
