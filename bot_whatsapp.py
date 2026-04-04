"""
Bot WhatsApp — Campaña Rezagados C1 E27
Comunicaciones Crear Poder Sin Límites Perú

Requisitos:
  pip install flask requests openpyxl filelock

Variables de entorno:
  WA_TOKEN        — Token de acceso de Meta
  WA_PHONE_ID     — Phone Number ID del número de Comunicaciones
  WA_VERIFY_TOKEN — Token de verificación del webhook (ej: "cpsl2026")
  EXCEL_PATH      — Ruta al Excel (default: campana_imos_c1_e27.xlsx)
  JOSE_LUIS_TEL   — Tu teléfono con código país sin + (ej: 51999123456)
  SESSIONS_PATH   — Ruta al JSON de sesiones (default: sesiones.json)
"""

import os, re, json, threading
from flask import Flask, request, jsonify
from datetime import datetime
import requests as req_lib
from openpyxl import load_workbook
from filelock import FileLock

app = Flask(__name__)

# ── Config en runtime, no en import ───────────────────────────────────────
def get_config():
    return {
        "token":         os.environ.get("WA_TOKEN", ""),
        "phone_id":      os.environ.get("WA_PHONE_ID", ""),
        "verify_token":  os.environ.get("WA_VERIFY_TOKEN", "cpsl2026"),
        "excel_path":    os.environ.get("EXCEL_PATH", "campana_imos_c1_e27.xlsx"),
        "jose_tel":      os.environ.get("JOSE_LUIS_TEL", ""),
        "sessions_path": os.environ.get("SESSIONS_PATH", "sesiones.json"),
    }

def norm_tel(tel):
    """
    Normaliza teléfonos a 9 dígitos para comparar.
    Maneja: 51XXXXXXXXX, 0XXXXXXXXX, XXXXXXXXX, 593XXXXXXXXX, etc.
    """
    t = str(tel).strip().replace("+","").replace(" ","").replace("-","")
    if t.startswith("51") and len(t) == 11:
        t = t[2:]   # quitar código Perú → 9 dígitos
    elif t.startswith("0") and len(t) == 10:
        t = t[1:]   # quitar 0 inicial → 9 dígitos
    elif len(t) > 10 and not t.startswith("9"):
        t = t[-9:]  # código de otro país → últimos 9
    return t

def api_url():
    return f"https://graph.facebook.com/v19.0/{get_config()['phone_id']}/messages"

_excel_lock = threading.Lock()

# ── Keywords corregidas — frases, no palabras sueltas ─────────────────────
KEYWORDS = {
    "STOP": [
        "stop", "baja", "no mas mensajes", "no quiero mensajes",
        "desuscribir", "eliminar mi numero",
    ],
    "NO INTERESADO": [
        "no quiere", "ya no quiere", "no le interesa", "no interesa",
        "desistio", "desistió", "no va a continuar", "no continua",
        "no continúa", "rechazo el proceso", "rechazó el proceso",
        "no desea", "se retira", "no seguira", "no seguirá",
        "no quiere continuar", "decidio no", "decidió no",
        "no va a ir", "no piensa ir", "no va a asistir",
    ],
    "NO CONTESTA": [
        "no contesta", "no me contesta", "no contesto",
        "no responde", "no me responde", "sin respuesta",
        "no lo ubico", "no la ubico", "no lo encuentro",
        "no la encuentro", "no atiende", "ilocalizable",
        "numero equivocado", "número equivocado",
        "numero malo", "número malo", "telefono malo",
        "fuera de cobertura", "no existe el numero",
    ],
    "PENDIENTE": [
        "pendiente", "aun no se", "aún no sé", "todavia no",
        "todavía no", "esta pensando", "está pensando",
        "lo esta pensando", "lo está pensando", "evaluando",
        "conversando con", "lo estoy hablando", "seguimos hablando",
        "en proceso", "me avisara", "me avisará",
        "sin respuesta aun", "sin respuesta aún",
    ],
    "SIGUIENTE": [
        "siguiente equipo", "otro equipo", "proximo equipo",
        "próximo equipo", "siguiente c1", "otro c1",
        "en el proximo", "en el próximo", "se une luego",
    ],
    "CONFIRMADO": [
        "confirma ", "confirmado", "confirmada", "confirmo",
        "si va", "sí va", "si viene", "sí viene",
        "asistira", "asistirá", "se va a sentar",
        "va a venir", "va a asistir", "va al c1",
        "se sienta", "listo para el", "lista para el",
        "van todos", "vienen todos",
    ],
}

# ── Normalización ──────────────────────────────────────────────────────────
def normalizar(texto):
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t

def detectar_estatus(texto):
    """
    Orden de prioridad: STOP → NO INTERESADO → NO CONTESTA
    → PENDIENTE → SIGUIENTE → CONFIRMADO
    Usa regex de palabra completa para evitar substrings.
    """
    t = normalizar(texto)
    orden = ["STOP","NO INTERESADO","NO CONTESTA","PENDIENTE","SIGUIENTE","CONFIRMADO"]
    for estatus in orden:
        for kw in KEYWORDS[estatus]:
            kw_n = normalizar(kw)
            patron = r'(?<![a-z])' + re.escape(kw_n) + r'(?![a-z])'
            if re.search(patron, t):
                return estatus
    return None

def buscar_px_en_texto(texto, px_list):
    """
    Extrae {px, estatus} del texto libre.
    Un solo px → estatus global. Varios px → busca cada uno.
    """
    resultados = []
    t_norm = normalizar(texto)

    if len(px_list) == 1:
        estatus = detectar_estatus(texto)
        if estatus and estatus != "STOP":
            resultados.append({"px": px_list[0], "estatus": estatus})
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
                estatus   = detectar_estatus(fragmento) or detectar_estatus(texto)
                if estatus and estatus != "STOP":
                    resultados.append({"px": px, "estatus": estatus})
                break

    # Deduplicar
    vistos, dedup = set(), []
    for r in resultados:
        if r["px"] not in vistos:
            vistos.add(r["px"])
            dedup.append(r)
    return dedup

# ── Sesiones en JSON (sobrevive reinicios) ─────────────────────────────────
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

# ── Excel helpers ──────────────────────────────────────────────────────────
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
                    if estado in ("PENDIENTE", "") and px_n:
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
STOP_CLAUSULA = "\n\nSi no deseas recibir más mensajes de este número, responde STOP."

def enviar_mensaje(telefono, texto):
    cfg = get_config()
    payload = {"messaging_product":"whatsapp","to":str(telefono),
               "type":"text","text":{"body":texto}}
    headers = {"Authorization":f"Bearer {cfg['token']}",
               "Content-Type":"application/json"}
    try:
        r = req_lib.post(api_url(), json=payload, headers=headers, timeout=10)
        if r.status_code != 200:
            print(f"[WA ERROR] {r.status_code}: {r.text[:200]}")
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
    """
    Detecta confirmación real en texto libre.
    Diferencia 'sí' (solo) de 'si me llaman' (falso positivo).
    """
    t = normalizar(texto)
    tokens = re.findall(r'[a-zaeioun]+', t)
    if not tokens:
        return False
    palabras_ok  = {"ok","dale","correcto","exacto","perfecto","listo",
                    "claro","afirmativo","confirmado","confirmo","si","si"}
    palabras_neg = {"no","pero","aunque","llam","contesta","puede","podria",
                    "quiero","deseo","puedes","dices","espera","llaman"}
    # Solo palabras de confirmación → confirmar
    if all(tok in palabras_ok for tok in tokens):
        return True
    # Hay negación → no confirmar
    if any(neg in t for neg in palabras_neg):
        return False
    # Primera palabra es confirmación y mensaje corto → confirmar
    if tokens[0] in palabras_ok and len(tokens) <= 3:
        return True
    return False

# ── Lógica principal ───────────────────────────────────────────────────────
def procesar_mensaje(telefono, texto):
    t_norm = normalizar(texto)
    sesion = get_sesion(telefono)

    # STOP — opt-out legal
    if detectar_estatus(texto) == "STOP":
        marcar_stop(telefono)
        borrar_sesion(telefono)
        enviar_mensaje(telefono,
            "Has sido dado de baja de nuestras comunicaciones. "
            "No recibirás más mensajes de este número.\n\n"
            "Comunicaciones Crear Poder Sin Límites Perú")
        return

    # Esperando confirmación del resumen
    if sesion.get("estado") == "esperando_confirmacion":
        # Regex de palabra completa — evita "si me llaman" → falso positivo
        confirma = es_confirmacion(texto)
        if confirma:
            extraidos = sesion.get("extraidos", [])
            actualizar_excel(extraidos, telefono)
            confirmados = [e for e in extraidos if e["estatus"] == "CONFIRMADO"]
            if confirmados:
                notificar_jose_luis(sesion.get("imo_nombre",""), confirmados)
            borrar_sesion(telefono)
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

    # Primera vez / retoma
    imo_nombre, px_list = cargar_px_del_imo(telefono)

    if not imo_nombre:
        enviar_mensaje(telefono,
            "Hola. Tu número no está registrado en nuestra campaña. "
            "Si crees que es un error, escríbele a tu coordinadora.\n\n"
            "Comunicaciones Crear Poder Sin Límites Perú" + STOP_CLAUSULA)
        return

    if not px_list:
        enviar_mensaje(telefono,
            f"Hola {nombre_pila(imo_nombre)}. "
            "Ya tienes el estatus registrado para todas tus personas. "
            "Si hay un cambio cuéntanos y lo actualizamos.\n\n"
            "Comunicaciones Crear Poder Sin Límites Perú")
        return

    pila     = nombre_pila(imo_nombre)
    extraidos = buscar_px_en_texto(texto, px_list)

    if not extraidos:
        lista_px = "\n".join(f"{i+1}. {px}" for i, px in enumerate(px_list))
        enviar_mensaje(telefono,
            f"Hola {pila}, gracias por responder.\n\n"
            f"No pude identificar el estatus de tus personas. "
            f"Por favor menciona el nombre de cada uno y su situación:\n\n"
            f"{lista_px}\n\n"
            f"Usa estas palabras:\n"
            f"✅ *confirma* — va a sentarse\n"
            f"➡️ *siguiente equipo* — se sienta en otro equipo\n"
            f"❌ *no quiere* — no va a continuar\n"
            f"📵 *no contesta* — no has podido ubicarle\n"
            f"⏳ *pendiente* — aún conversando\n\n"
            f"Ejemplo: _Jorge confirma, María no contesta, Pedro pendiente_"
            + STOP_CLAUSULA)
        return

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
            procesar_mensaje(telefono, texto)
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
        "status":            "activo",
        "sesiones_activas":  len(cargar_sesiones()),
        "excel_existe":      os.path.exists(cfg["excel_path"]),
        "token_ok":          bool(cfg["token"]),
        "phone_ok":          bool(cfg["phone_id"]),
        "hora":              datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
    }), 200

@app.route("/sesiones", methods=["GET"])
def ver_sesiones():
    return jsonify(cargar_sesiones()), 200

@app.route("/sesiones/<telefono>", methods=["DELETE"])
def borrar_sesion_endpoint(telefono):
    borrar_sesion(telefono); return jsonify({"borrado": telefono}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    cfg  = get_config()
    print(f"🤖 Bot CPSL — puerto {port}")
    print(f"📁 Excel   : {cfg['excel_path']}")
    print(f"💾 Sesiones: {cfg['sessions_path']}")
    print(f"📱 PhoneID : {cfg['phone_id'] or '⚠️ NO CONFIGURADO'}")
    print(f"🔑 Token   : {'✅' if cfg['token'] else '⚠️ NO CONFIGURADO'}")
    app.run(host="0.0.0.0", port=port, debug=False)
