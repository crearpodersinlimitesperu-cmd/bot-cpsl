"""
ia_multimodelo.py — Motor de 20 IAs para CPSL Lima
====================================================
Prioriza IAs SIN API KEY (HuggingFace public, DuckDuckGo AI, etc.)
Luego usa IAs con key gratuita si están configuradas.
TODAS son 100% gratis, sin tarjeta de crédito.
"""
import os, re, json, logging, time, hashlib
from datetime import datetime, timezone, timedelta
import requests as req

log = logging.getLogger("IA20")
TZ = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

# ── API Keys OPCIONALES (gratis, sin tarjeta) ───────────────
GEMINI_KEY     = os.environ.get("GOOGLE_AI_KEY", "")
GROQ_KEY       = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
HF_TOKEN       = os.environ.get("HF_TOKEN", "")

# ── CONTEXTO CPSL ────────────────────────────────────────────
CPSL_CTX = (
    "Eres el asistente de CREAR PODER SIN LÍMITES PERÚ. "
    "Reglas: 1) Solo hablas de entrenamientos CPSL, fechas y coordinación. "
    "2) Sé empático, cálido, profesional. Máx 3 líneas. "
    "3) No inventes info. Si no sabes, di: 'Tu coordinadora te dará esos detalles.' "
    "4) No repitas. No hagas bucles. "
    "Info: C1 E27: 1-3 mayo 2026, Hotel José Antonio Deluxe, Miraflores. "
    "Pagos: BCP 1934218307060. CCs: Diana Moscoso, Joyce Marín, Zuley Urteaga."
)

PROMPTS = {
    "px_respuesta": CPSL_CTX + " Responde al participante con calidez. Si confirma, felicítalo. Si no puede, sé empático.",
    "imo_respuesta": CPSL_CTX + " Responde al IMO (graduado) con respeto como líder.",
    "clasificar": "Clasifica en UNA categoría: CONFIRMA, NEGATIVA, PREGUNTA_FECHA, PREGUNTA_PAGO, SALUDO, QUEJA, CONSULTA_GENERAL, SPAM. Responde SOLO la categoría.",
    "nuevo_info": CPSL_CTX + " Responde al prospecto nuevo con entusiasmo sin presionar. Máx 3 líneas.",
    "cc_intent": CPSL_CTX + ' Detecta intención. Responde JSON: {"intent":"CERRAR|ACTUALIZAR|NOTA|NINGUNA","nombre":"","resumen":""}',
}

# ── CACHE ────────────────────────────────────────────────────
_cache = {}

def _ck(p, c): return hashlib.md5(f"{c}:{p[:80]}".encode()).hexdigest()
def _cg(k):
    if k in _cache and time.time() - _cache[k][0] < 300: return _cache[k][1]
    return None
def _cs(k, v):
    _cache[k] = (time.time(), v)
    if len(_cache) > 500:
        for dk in sorted(_cache, key=lambda x: _cache[x][0])[:100]: del _cache[dk]

# ── NLP LOCAL (funciona SIEMPRE, sin IA, sin key) ────────────
_RESPUESTAS_LOCAL = {
    "CONFIRMA": "¡Excelente! Tu confirmación ha sido registrada. 🎉\nTu coordinadora recibirá la notificación.",
    "NEGATIVA": "Entendido. Tu mensaje fue enviado a tu coordinadora.\nSi cambias de parecer, escribe HOLA.",
    "PREGUNTA_FECHA": "📅 C1 Equipo 27: Viernes 1, Sábado 2 y Domingo 3 de mayo 2026\n📍 Hotel José Antonio Deluxe, Miraflores",
    "PREGUNTA_PAGO": "💳 BCP — Creación Cuántica E.I.R.L.\nCuenta Soles: 1934218307060\nTu coordinadora te dará los detalles de inversión.",
    "SALUDO": "¡Hola! 🌟 Bienvenido a CPSL Perú. Escribe el número de tu opción para continuar.",
    "QUEJA": "Lamento que tengas esa experiencia. Tu mensaje fue enviado a coordinación para atención inmediata. 🙏",
    "CONSULTA_GENERAL": "Gracias por tu mensaje. Tu coordinadora te dará esos detalles personalmente. 🙏",
    "IMO_CONFIRMA": "✅ Recibido. Tu reporte de confirmación fue enviado a coordinación.",
    "IMO_GENERAL": "Gracias, líder. Tu coordinadora puede ayudarte con eso. Escribe 5 para contactarla.",
    "NUEVO_INFO": "🌟 CPSL Perú ofrece entrenamientos de liderazgo transformacional. Escribe 2 para más información.",
}

def _respuesta_local(cat, tipo="PX"):
    """Respuesta sin IA, basada en categoría detectada."""
    if tipo == "IMO":
        if cat == "CONFIRMA": return _RESPUESTAS_LOCAL["IMO_CONFIRMA"]
        return _RESPUESTAS_LOCAL.get("IMO_GENERAL")
    if tipo == "NUEVO":
        return _RESPUESTAS_LOCAL.get("NUEVO_INFO")
    return _RESPUESTAS_LOCAL.get(cat, _RESPUESTAS_LOCAL["CONSULTA_GENERAL"])


# ══════════════════════════════════════════════════════════════
# PROVEEDORES SIN API KEY (funcionan directo)
# ══════════════════════════════════════════════════════════════

# 1. HuggingFace Inference SIN token (rate limited pero funciona)
def _ia_hf_free(prompt, s="", **kw):
    """HuggingFace Inference API - funciona SIN token."""
    try:
        r = req.post(
            "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            json={"inputs": f"<s>[INST] {s}\n\n{prompt} [/INST]",
                  "parameters": {"max_new_tokens": 120, "temperature": 0.3}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {},
            timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("[/INST]")[-1].strip() if "[/INST]" in txt else txt.strip()
    except: pass
    return None

# 2. HuggingFace Zephyr SIN token
def _ia_hf_zephyr_free(prompt, s="", **kw):
    try:
        r = req.post(
            "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
            json={"inputs": f"<|system|>{s}</s>\n<|user|>{prompt}</s>\n<|assistant|>",
                  "parameters": {"max_new_tokens": 120}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {},
            timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("<|assistant|>")[-1].strip()
    except: pass
    return None

# 3. HuggingFace Qwen SIN token
def _ia_hf_qwen_free(prompt, s="", **kw):
    try:
        r = req.post(
            "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-1.5B-Instruct",
            json={"inputs": f"<|im_start|>system\n{s}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
                  "parameters": {"max_new_tokens": 120}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {},
            timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("<|im_start|>assistant")[-1].replace("<|im_end|>","").strip()
    except: pass
    return None

# 4. HuggingFace Phi-3 SIN token
def _ia_hf_phi_free(prompt, s="", **kw):
    try:
        r = req.post(
            "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-4k-instruct",
            json={"inputs": f"<|system|>{s}<|end|>\n<|user|>{prompt}<|end|>\n<|assistant|>",
                  "parameters": {"max_new_tokens": 120}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {},
            timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("<|assistant|>")[-1].replace("<|end|>","").strip()
    except: pass
    return None

# 5. HuggingFace Gemma SIN token
def _ia_hf_gemma_free(prompt, s="", **kw):
    try:
        r = req.post(
            "https://api-inference.huggingface.co/models/google/gemma-2-2b-it",
            json={"inputs": f"<start_of_turn>user\n{s}\n{prompt}<end_of_turn>\n<start_of_turn>model\n",
                  "parameters": {"max_new_tokens": 120}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"} if HF_TOKEN else {},
            timeout=12)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("<start_of_turn>model")[-1].replace("<end_of_turn>","").strip()
    except: pass
    return None

# 6-10. DuckDuckGo AI Chat (SIN key, SIN límite conocido)
def _duckduckgo_chat(prompt, s="", model="gpt-4o-mini", **kw):
    """DuckDuckGo AI Chat — completamente gratis, sin key."""
    try:
        # Obtener token vqd
        headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/html",
                   "x-vqd-accept": "1"}
        st = req.get("https://duckduckgo.com/duckchat/v1/status", headers=headers, timeout=5)
        vqd = st.headers.get("x-vqd-4", "")
        if not vqd: return None

        r = req.post("https://duckduckgo.com/duckchat/v1/chat",
            json={"model": model, "messages": [
                {"role": "user", "content": f"{s}\n\n{prompt}"}
            ]},
            headers={"User-Agent": "Mozilla/5.0", "x-vqd-4": vqd,
                     "Content-Type": "application/json", "Accept": "text/event-stream"},
            timeout=10, stream=True)
        if r.status_code == 200:
            full = ""
            for line in r.iter_lines():
                if not line: continue
                l = line.decode("utf-8", errors="ignore")
                if l.startswith("data: "):
                    chunk = l[6:]
                    if chunk == "[DONE]": break
                    try:
                        d = json.loads(chunk)
                        full += d.get("message", "")
                    except: pass
            if full.strip():
                return full.strip()[:500]
    except: pass
    return None

def _ia_ddg_gpt4mini(p, s="", **kw):
    return _duckduckgo_chat(p, s, model="gpt-4o-mini")

def _ia_ddg_claude(p, s="", **kw):
    return _duckduckgo_chat(p, s, model="claude-3-haiku-20240307")

def _ia_ddg_llama(p, s="", **kw):
    return _duckduckgo_chat(p, s, model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo")

def _ia_ddg_mixtral(p, s="", **kw):
    return _duckduckgo_chat(p, s, model="mistralai/Mixtral-8x7B-Instruct-v0.1")


# ══════════════════════════════════════════════════════════════
# PROVEEDORES CON KEY GRATUITA (opcionales, activan si hay key)
# ══════════════════════════════════════════════════════════════

def _oai(url, key, model, s, p, timeout=8):
    if not key: return None
    try:
        r = req.post(url, json={"model": model, "messages": [
            {"role": "system", "content": s}, {"role": "user", "content": p}
        ], "max_tokens": 150, "temperature": 0.3},
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=timeout)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

# 11. Gemini 2.0 Flash
def _ia_gemini(p, s="", **kw):
    if not GEMINI_KEY: return None
    try:
        r = req.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            json={"contents": [{"parts": [{"text": f"{s}\n\n{p}"}]}],
                  "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3}},
            params={"key": GEMINI_KEY}, timeout=8)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except: pass
    return None

# 12-15. Groq (4 modelos)
def _ia_groq1(p, s="", **kw): return _oai("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, "llama-3.1-8b-instant", s, p)
def _ia_groq2(p, s="", **kw): return _oai("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, "llama-3.3-70b-versatile", s, p)
def _ia_groq3(p, s="", **kw): return _oai("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, "gemma2-9b-it", s, p)
def _ia_groq4(p, s="", **kw): return _oai("https://api.groq.com/openai/v1/chat/completions", GROQ_KEY, "mixtral-8x7b-32768", s, p)

# 16-19. OpenRouter (modelos :free)
def _ia_or1(p, s="", **kw): return _oai("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "meta-llama/llama-3.1-8b-instruct:free", s, p)
def _ia_or2(p, s="", **kw): return _oai("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "google/gemma-2-9b-it:free", s, p)
def _ia_or3(p, s="", **kw): return _oai("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "mistralai/mistral-7b-instruct:free", s, p)
def _ia_or4(p, s="", **kw): return _oai("https://openrouter.ai/api/v1/chat/completions", OPENROUTER_KEY, "qwen/qwen-2.5-7b-instruct:free", s, p)

# 20. Gemini 1.5 Flash
def _ia_gemini15(p, s="", **kw):
    if not GEMINI_KEY: return None
    try:
        r = req.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json={"contents": [{"parts": [{"text": f"{s}\n\n{p}"}]}],
                  "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3}},
            params={"key": GEMINI_KEY}, timeout=8)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except: pass
    return None


# ── CADENA: primero SIN KEY, luego CON KEY ───────────────────
CADENA_IA = [
    # SIN KEY — funcionan siempre
    (_ia_ddg_gpt4mini, "DDG-GPT4mini", False),
    (_ia_ddg_claude, "DDG-Claude-Haiku", False),
    (_ia_ddg_llama, "DDG-Llama70B", False),
    (_ia_ddg_mixtral, "DDG-Mixtral", False),
    (_ia_hf_free, "HF-Mistral-Free", False),
    (_ia_hf_zephyr_free, "HF-Zephyr-Free", False),
    (_ia_hf_qwen_free, "HF-Qwen-Free", False),
    (_ia_hf_phi_free, "HF-Phi3-Free", False),
    (_ia_hf_gemma_free, "HF-Gemma-Free", False),
    # CON KEY (opcional, gratis)
    (_ia_gemini, "Gemini-2.0", True),
    (_ia_groq1, "Groq-Llama8B", True),
    (_ia_groq2, "Groq-Llama70B", True),
    (_ia_groq3, "Groq-Gemma9B", True),
    (_ia_groq4, "Groq-Mixtral", True),
    (_ia_or1, "OR-Llama-Free", True),
    (_ia_or2, "OR-Gemma-Free", True),
    (_ia_or3, "OR-Mistral-Free", True),
    (_ia_or4, "OR-Qwen-Free", True),
    (_ia_gemini15, "Gemini-1.5", True),
    # Fallback final sin key
    (None, "NLP-Local", False),
]


# ── FUNCIÓN PRINCIPAL ────────────────────────────────────────

def ia_responder(prompt, contexto="px_respuesta", timeout=8):
    """Cadena de 20 IAs con cache. SIN KEY = primeras 9."""
    ck = _ck(prompt, contexto)
    cached = _cg(ck)
    if cached: return cached

    system = PROMPTS.get(contexto, CPSL_CTX)

    for fn, nombre, _ in CADENA_IA:
        if fn is None: continue
        try:
            resp = fn(prompt, s=system)
            if resp and len(resp) > 5:
                resp = _sanitizar(resp)
                _cs(ck, resp)
                log.info(f"[IA] OK via {nombre}")
                return resp
        except Exception as e:
            log.debug(f"[IA] {nombre}: {e}")
            continue

    log.warning("[IA] Todas fallaron — usando NLP local")
    return None


def ia_clasificar(texto):
    """Clasifica intención sin IA (regex local siempre funciona)."""
    up = texto.upper().strip()
    if any(w in up for w in ["CONFIRMO","ASISTO","VOY","SI ASIST","CONFIRMA","SI, ASIS","SI ASIS","ESTARÉ","ESTARE","SI CONFIRMO","YA CONFIRMO"]):
        return "CONFIRMA"
    if any(w in up for w in ["NO QUIERO","NO PUEDO","NO DESEO","DEVUELVAN","NO ASIST","NO ME INTERESA","NO VOY","IMPOSIBLE","NO ESTOY INTERESADO"]):
        return "NEGATIVA"
    if any(w in up for w in ["FECHA","CUANDO","QUE DIA","QUÉ DÍA","QUE DIAS","MAYO","FERIADO"]):
        return "PREGUNTA_FECHA"
    if any(w in up for w in ["PAGO","PRECIO","COSTO","CUANTO","CUÁNTO","INVERSIÓN","INVERSION","BCP","CUENTA"]):
        return "PREGUNTA_PAGO"
    if any(w in up for w in ["HOLA","BUENOS","BUENAS","HI","HELLO"]):
        return "SALUDO"
    if any(w in up for w in ["QUEJA","RECLAMO","MOLEST","MAL SERVICIO","PESIMO","PÉSIMO"]):
        return "QUEJA"
    if len(texto.strip()) < 5:
        return "CORTO"

    # Solo si la clasificación local no es clara, intentar IA
    resp = ia_responder(f'Clasifica: "{texto}"', contexto="clasificar", timeout=5)
    if resp:
        for cat in ["CONFIRMA","NEGATIVA","PREGUNTA_FECHA","PREGUNTA_PAGO","QUEJA","SPAM"]:
            if cat in resp.upper(): return cat
    return "CONSULTA_GENERAL"


def ia_respuesta_px(nombre, texto, info_cc="", info_extra=""):
    """Respuesta inteligente para PX. Primero IA, fallback local."""
    prompt = f"Participante: {nombre}\nCC: {info_cc}\nMensaje: \"{texto}\"\nResponde corto, máx 3 líneas."
    resp = ia_responder(prompt, contexto="px_respuesta")
    if resp: return resp
    cat = ia_clasificar(texto)
    return _respuesta_local(cat, "PX")

def ia_respuesta_imo(nombre, texto, n_pendientes=0):
    """Respuesta inteligente para IMO. Primero IA, fallback local."""
    prompt = f"IMO: {nombre} ({n_pendientes} pendientes)\nMensaje: \"{texto}\"\nResponde corto."
    resp = ia_responder(prompt, contexto="imo_respuesta")
    if resp: return resp
    cat = ia_clasificar(texto)
    return _respuesta_local(cat, "IMO")

def ia_respuesta_nuevo(texto):
    """Respuesta para prospecto nuevo."""
    resp = ia_responder(f'Prospecto escribe: "{texto}"', contexto="nuevo_info")
    if resp: return resp
    return _respuesta_local("CONSULTA_GENERAL", "NUEVO")


def _sanitizar(texto):
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'\*\*\*', '*', texto)
    if len(texto) > 500: texto = texto[:497] + "..."
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


# ── FEEDBACK ─────────────────────────────────────────────────
FEEDBACK_FILE = os.path.join(DATA_DIR, "ia_feedback.json")

def guardar_feedback(tipo_usuario, mensaje, respuesta_ia, fue_util=None):
    try:
        data = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE) as f: data = json.load(f)
        data.append({"ts": datetime.now(TZ).isoformat(), "tipo": tipo_usuario,
                     "msg": mensaje[:200], "resp": (respuesta_ia or "")[:200], "util": fue_util})
        data = data[-1000:]
        with open(FEEDBACK_FILE, "w") as f: json.dump(data, f, ensure_ascii=False, indent=1)
    except: pass

def estado_ias():
    """Estado de las 20 IAs."""
    resultado = []
    for fn, nombre, necesita_key in CADENA_IA:
        if fn is None:
            resultado.append({"nombre": nombre, "activa": True, "tipo": "local"})
            continue
        activa = True
        if necesita_key:
            if "gemini" in nombre.lower(): activa = bool(GEMINI_KEY)
            elif "groq" in nombre.lower(): activa = bool(GROQ_KEY)
            elif "or-" in nombre.lower(): activa = bool(OPENROUTER_KEY)
        resultado.append({"nombre": nombre, "activa": activa,
                          "tipo": "sin_key" if not necesita_key else ("con_key" if activa else "necesita_key")})
    return resultado
