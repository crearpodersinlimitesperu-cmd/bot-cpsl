"""
ia_multimodelo.py — Motor de 20 IAs Gratuitas para CPSL Lima
=============================================================
Cadena de fallback con 20 proveedores. Respuestas contextuales,
sin bucles, sin salir del contexto CPSL.
"""
import os, re, json, logging, time, hashlib, random
from datetime import datetime, timezone, timedelta
import requests as req

log = logging.getLogger("IA20")
TZ = timezone(timedelta(hours=-5))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = "/data" if os.path.exists("/data") else BASE_DIR

# ── API Keys (se cargan de env vars en Render) ──────────────
GEMINI_KEY   = os.environ.get("GOOGLE_AI_KEY", "")
GROQ_KEY     = os.environ.get("GROQ_API_KEY", "")
COHERE_KEY   = os.environ.get("COHERE_API_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
MISTRAL_KEY  = os.environ.get("MISTRAL_API_KEY", "")
TOGETHER_KEY = os.environ.get("TOGETHER_API_KEY", "")
OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "")
SAMBANOVA_KEY = os.environ.get("SAMBANOVA_API_KEY", "")

# ── CONTEXTO CPSL (entrenamiento base para TODAS las IAs) ────
CPSL_CONTEXT = """
Eres el asistente virtual de CREAR PODER SIN LÍMITES PERÚ (CPSL).
REGLAS ABSOLUTAS:
1. NUNCA salgas del contexto de CPSL. Solo hablas de entrenamientos, fechas, coordinación.
2. Sé empático, cálido, profesional y asertivo. NUNCA agresivo ni robótico.
3. Respuestas MÁXIMO 3 líneas. Sin párrafos largos.
4. NUNCA inventes fechas, precios ni información que no tengas.
5. Si no sabes algo, di: "Tu coordinadora te dará esos detalles."
6. NUNCA envíes al usuario en bucle. Si ya respondiste, no repitas.
7. Protege a las CC: NO las satures con mensajes innecesarios.
8. Detecta intención del usuario y responde directamente.

INFORMACIÓN VÁLIDA:
- C1 Equipo 27: Viernes 1, Sábado 2 y Domingo 3 de mayo 2026
- Lugar: Hotel José Antonio Deluxe, Calle Bellavista 133, Miraflores
- Pagos: BCP Cuenta Soles 1934218307060
- CCs: Diana Moscoso, Joyce Marín, Zuley Urteaga
"""

# ── PROMPTS POR TIPO DE USUARIO ─────────────────────────────
PROMPTS = {
    "px_respuesta": (
        CPSL_CONTEXT +
        "\nEl participante (PX) escribe un mensaje. Responde de forma cálida y directa. "
        "Si confirma asistencia, felicítalo. Si dice que no puede, sé empático y sugiere hablar con su coordinadora. "
        "Si pregunta algo, responde con la info que tienes o deriva a coordinadora."
    ),
    "imo_respuesta": (
        CPSL_CONTEXT +
        "\nUn IMO (graduado enrolador) escribe. Trátalo con respeto como líder. "
        "Si reporta una confirmación, agradece y registra. Si tiene dudas, oriéntalo al menú o coordinación."
    ),
    "cc_intent": (
        CPSL_CONTEXT +
        "\nDetecta la intención de la coordinadora. Responde SOLO JSON: "
        '{"intent":"CERRAR|ACTUALIZAR|NOTA|DERIVAR|NINGUNA","nombre":"<nombre>","resumen":"<breve>"}'
    ),
    "clasificar": (
        "Clasifica el mensaje del usuario en UNA categoría. Responde SOLO la categoría:\n"
        "CONFIRMA, NEGATIVA, PREGUNTA_FECHA, PREGUNTA_PAGO, SALUDO, QUEJA, CONSULTA_GENERAL, SPAM"
    ),
    "nuevo_info": (
        CPSL_CONTEXT +
        "\nUn prospecto nuevo pregunta por información. Sé entusiasta pero NO presiones. "
        "Máximo 3 líneas. Si pregunta precio, di que su coordinadora le dará los detalles personalizados."
    ),
}

# ── CACHE de respuestas (evita llamadas duplicadas) ──────────
_cache = {}
_CACHE_TTL = 300  # 5 min

def _cache_key(prompt, ctx):
    return hashlib.md5(f"{ctx}:{prompt[:100]}".encode()).hexdigest()

def _cache_get(key):
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _cache[key]
    return None

def _cache_set(key, val):
    _cache[key] = (time.time(), val)
    if len(_cache) > 500:
        oldest = sorted(_cache, key=lambda k: _cache[k][0])[:100]
        for k in oldest: del _cache[k]

# ── PROVEEDORES DE IA (20 modelos) ───────────────────────────

def _call_openai_compat(url, key, model, system, prompt, timeout=8, max_tokens=150):
    """Llamada genérica compatible con API OpenAI."""
    if not key: return None
    try:
        r = req.post(url, json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens, "temperature": 0.3
        }, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        timeout=timeout)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except: pass
    return None

# 1. Gemini 2.0 Flash (1500 req/day)
def _ia_gemini(prompt, system="", **kw):
    if not GEMINI_KEY: return None
    try:
        r = req.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            json={"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                  "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3}},
            params={"key": GEMINI_KEY}, timeout=8)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except: pass
    return None

# 2. Groq Llama 3.1 8B (14400 req/day)
def _ia_groq_llama(p, s="", **kw):
    return _call_openai_compat("https://api.groq.com/openai/v1/chat/completions",
                               GROQ_KEY, "llama-3.1-8b-instant", s, p)

# 3. Groq Llama 3.3 70B (14400 req/day)
def _ia_groq_llama70(p, s="", **kw):
    return _call_openai_compat("https://api.groq.com/openai/v1/chat/completions",
                               GROQ_KEY, "llama-3.3-70b-versatile", s, p)

# 4. Groq Gemma 2 9B
def _ia_groq_gemma(p, s="", **kw):
    return _call_openai_compat("https://api.groq.com/openai/v1/chat/completions",
                               GROQ_KEY, "gemma2-9b-it", s, p)

# 5. Groq Mixtral 8x7B
def _ia_groq_mixtral(p, s="", **kw):
    return _call_openai_compat("https://api.groq.com/openai/v1/chat/completions",
                               GROQ_KEY, "mixtral-8x7b-32768", s, p)

# 6. DeepSeek Chat
def _ia_deepseek(p, s="", **kw):
    return _call_openai_compat("https://api.deepseek.com/chat/completions",
                               DEEPSEEK_KEY, "deepseek-chat", s, p)

# 7. Mistral Tiny
def _ia_mistral(p, s="", **kw):
    return _call_openai_compat("https://api.mistral.ai/v1/chat/completions",
                               MISTRAL_KEY, "mistral-tiny", s, p)

# 8. Together Llama 3.1 8B
def _ia_together_llama(p, s="", **kw):
    return _call_openai_compat("https://api.together.xyz/v1/chat/completions",
                               TOGETHER_KEY, "meta-llama/Llama-3.1-8B-Instruct-Turbo", s, p)

# 9. Together Mistral 7B
def _ia_together_mistral(p, s="", **kw):
    return _call_openai_compat("https://api.together.xyz/v1/chat/completions",
                               TOGETHER_KEY, "mistralai/Mistral-7B-Instruct-v0.3", s, p)

# 10. Together Qwen 2.5 7B
def _ia_together_qwen(p, s="", **kw):
    return _call_openai_compat("https://api.together.xyz/v1/chat/completions",
                               TOGETHER_KEY, "Qwen/Qwen2.5-7B-Instruct-Turbo", s, p)

# 11. OpenRouter (free models)
def _ia_openrouter_llama(p, s="", **kw):
    return _call_openai_compat("https://openrouter.ai/api/v1/chat/completions",
                               OPENROUTER_KEY, "meta-llama/llama-3.1-8b-instruct:free", s, p)

# 12. OpenRouter Gemma
def _ia_openrouter_gemma(p, s="", **kw):
    return _call_openai_compat("https://openrouter.ai/api/v1/chat/completions",
                               OPENROUTER_KEY, "google/gemma-2-9b-it:free", s, p)

# 13. OpenRouter Mistral
def _ia_openrouter_mistral(p, s="", **kw):
    return _call_openai_compat("https://openrouter.ai/api/v1/chat/completions",
                               OPENROUTER_KEY, "mistralai/mistral-7b-instruct:free", s, p)

# 14. OpenRouter Qwen
def _ia_openrouter_qwen(p, s="", **kw):
    return _call_openai_compat("https://openrouter.ai/api/v1/chat/completions",
                               OPENROUTER_KEY, "qwen/qwen-2.5-7b-instruct:free", s, p)

# 15. HuggingFace Inference (Mistral)
def _ia_hf_mistral(p, s="", **kw):
    if not HF_TOKEN: return None
    try:
        r = req.post("https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
            json={"inputs": f"<s>[INST] {s}\n\n{p} [/INST]", "parameters": {"max_new_tokens": 150}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("[/INST]")[-1].strip() if "[/INST]" in txt else txt.strip()
    except: pass
    return None

# 16. HuggingFace Zephyr
def _ia_hf_zephyr(p, s="", **kw):
    if not HF_TOKEN: return None
    try:
        r = req.post("https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta",
            json={"inputs": f"<|system|>{s}</s>\n<|user|>{p}</s>\n<|assistant|>",
                  "parameters": {"max_new_tokens": 150}},
            headers={"Authorization": f"Bearer {HF_TOKEN}"}, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list) and data:
                txt = data[0].get("generated_text", "")
                return txt.split("<|assistant|>")[-1].strip()
    except: pass
    return None

# 17. Cerebras (Llama 3.1 8B — extremely fast)
def _ia_cerebras(p, s="", **kw):
    return _call_openai_compat("https://api.cerebras.ai/v1/chat/completions",
                               CEREBRAS_KEY, "llama3.1-8b", s, p)

# 18. SambaNova Cloud
def _ia_sambanova(p, s="", **kw):
    return _call_openai_compat("https://api.sambanova.ai/v1/chat/completions",
                               SAMBANOVA_KEY, "Meta-Llama-3.1-8B-Instruct", s, p)

# 19. Cohere Command
def _ia_cohere(p, s="", **kw):
    if not COHERE_KEY: return None
    try:
        r = req.post("https://api.cohere.ai/v1/generate",
            json={"model": "command-light", "prompt": f"{s}\n\n{p}",
                  "max_tokens": 150, "temperature": 0.3},
            headers={"Authorization": f"Bearer {COHERE_KEY}"}, timeout=8)
        if r.status_code == 200:
            return r.json()["generations"][0]["text"].strip()
    except: pass
    return None

# 20. Gemini 1.5 Flash (backup Google)
def _ia_gemini15(prompt, system="", **kw):
    if not GEMINI_KEY: return None
    try:
        r = req.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
            json={"contents": [{"parts": [{"text": f"{system}\n\n{prompt}"}]}],
                  "generationConfig": {"maxOutputTokens": 150, "temperature": 0.3}},
            params={"key": GEMINI_KEY}, timeout=8)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except: pass
    return None


# ── CADENA PRINCIPAL DE 20 IAs ───────────────────────────────
CADENA_IA = [
    (_ia_gemini, "Gemini-2.0-Flash"),
    (_ia_groq_llama, "Groq-Llama3.1-8B"),
    (_ia_groq_llama70, "Groq-Llama3.3-70B"),
    (_ia_cerebras, "Cerebras-Llama3.1"),
    (_ia_sambanova, "SambaNova-Llama3.1"),
    (_ia_groq_gemma, "Groq-Gemma2-9B"),
    (_ia_groq_mixtral, "Groq-Mixtral-8x7B"),
    (_ia_deepseek, "DeepSeek-Chat"),
    (_ia_mistral, "Mistral-Tiny"),
    (_ia_together_llama, "Together-Llama3.1"),
    (_ia_together_mistral, "Together-Mistral"),
    (_ia_together_qwen, "Together-Qwen2.5"),
    (_ia_openrouter_llama, "OpenRouter-Llama"),
    (_ia_openrouter_gemma, "OpenRouter-Gemma"),
    (_ia_openrouter_mistral, "OpenRouter-Mistral"),
    (_ia_openrouter_qwen, "OpenRouter-Qwen"),
    (_ia_hf_mistral, "HF-Mistral"),
    (_ia_hf_zephyr, "HF-Zephyr"),
    (_ia_cohere, "Cohere-Command"),
    (_ia_gemini15, "Gemini-1.5-Flash"),
]


def ia_responder(prompt, contexto="px_respuesta", timeout=8):
    """Intenta con 20 IAs en cadena de fallback con cache."""
    ck = _cache_key(prompt, contexto)
    cached = _cache_get(ck)
    if cached:
        return cached

    system = PROMPTS.get(contexto, CPSL_CONTEXT)

    for fn, nombre in CADENA_IA:
        try:
            resp = fn(prompt, s=system)
            if resp and len(resp) > 5:
                # Sanitizar: quitar markdown excesivo, limitar largo
                resp = _sanitizar_respuesta(resp)
                _cache_set(ck, resp)
                log.info(f"[IA] OK via {nombre}")
                return resp
        except Exception as e:
            log.debug(f"[IA] {nombre} falló: {e}")
            continue

    log.warning("[IA] Todas las 20 IAs fallaron")
    return None


def ia_clasificar(texto):
    """Clasifica intención del mensaje en una categoría."""
    # Primero intentar regex locales (sin costo)
    up = texto.upper().strip()
    if any(w in up for w in ["CONFIRMO", "ASISTO", "VOY", "SI ASIST", "CONFIRMA"]):
        return "CONFIRMA"
    if any(w in up for w in ["NO QUIERO", "NO PUEDO", "DEVUELVAN", "NO ASIST", "NO ME INTERESA"]):
        return "NEGATIVA"
    if any(w in up for w in ["FECHA", "CUANDO", "QUE DIA", "QUÉ DÍA"]):
        return "PREGUNTA_FECHA"
    if any(w in up for w in ["PAGO", "PRECIO", "COSTO", "CUANTO", "INVERSIÓN"]):
        return "PREGUNTA_PAGO"
    if any(w in up for w in ["HOLA", "BUENOS", "BUENAS"]):
        return "SALUDO"
    if any(w in up for w in ["QUEJA", "RECLAMO", "MOLEST", "MAL SERVICIO"]):
        return "QUEJA"
    if len(texto.strip()) < 5:
        return "CORTO"

    # Si no es claro, usar IA
    resp = ia_responder(f'Clasifica: "{texto}"', contexto="clasificar", timeout=5)
    if resp:
        for cat in ["CONFIRMA", "NEGATIVA", "PREGUNTA_FECHA", "PREGUNTA_PAGO", "QUEJA", "SPAM"]:
            if cat in resp.upper():
                return cat
    return "CONSULTA_GENERAL"


def ia_respuesta_px(nombre, texto, info_cc="", info_extra=""):
    """Genera respuesta inteligente para un PX."""
    prompt = (
        f"Participante: {nombre}\n"
        f"Su coordinadora: {info_cc}\n"
        f"Mensaje del PX: \"{texto}\"\n"
        f"{info_extra}\n"
        f"Genera UNA respuesta corta, cálida y directa (máx 3 líneas)."
    )
    return ia_responder(prompt, contexto="px_respuesta")


def ia_respuesta_imo(nombre, texto, n_pendientes=0):
    """Genera respuesta inteligente para un IMO."""
    prompt = (
        f"IMO (graduado): {nombre} tiene {n_pendientes} enrolados pendientes.\n"
        f"Mensaje del IMO: \"{texto}\"\n"
        f"Genera UNA respuesta corta y respetuosa (máx 3 líneas)."
    )
    return ia_responder(prompt, contexto="imo_respuesta")


def ia_respuesta_nuevo(texto):
    """Genera respuesta para prospecto nuevo."""
    prompt = f'Prospecto nuevo escribe: "{texto}"\nResponde cálido, máx 3 líneas.'
    return ia_responder(prompt, contexto="nuevo_info")


def _sanitizar_respuesta(texto):
    """Limpia respuesta de IA para WhatsApp."""
    # Quitar markdown excesivo
    texto = re.sub(r'#{1,6}\s*', '', texto)
    texto = re.sub(r'\*\*\*', '*', texto)
    # Limitar a 500 chars
    if len(texto) > 500:
        texto = texto[:497] + "..."
    # Quitar líneas vacías múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    return texto.strip()


# ── APRENDIZAJE: guardar feedback para mejorar ───────────────
FEEDBACK_FILE = os.path.join(DATA_DIR, "ia_feedback.json")

def guardar_feedback(tipo_usuario, mensaje, respuesta_ia, fue_util=None):
    """Guarda interacción para aprendizaje futuro."""
    try:
        data = []
        if os.path.exists(FEEDBACK_FILE):
            with open(FEEDBACK_FILE) as f:
                data = json.load(f)
        data.append({
            "ts": datetime.now(TZ).isoformat(),
            "tipo": tipo_usuario,
            "msg": mensaje[:200],
            "resp": respuesta_ia[:200] if respuesta_ia else "",
            "util": fue_util,
        })
        # Mantener solo últimos 1000 registros
        data = data[-1000:]
        with open(FEEDBACK_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except: pass


def estado_ias():
    """Retorna estado de todas las IAs configuradas."""
    resultado = []
    for fn, nombre in CADENA_IA:
        # Detectar si tiene key configurada
        tiene_key = True
        if "gemini" in nombre.lower() and not GEMINI_KEY: tiene_key = False
        if "groq" in nombre.lower() and not GROQ_KEY: tiene_key = False
        if "deepseek" in nombre.lower() and not DEEPSEEK_KEY: tiene_key = False
        if "mistral" in nombre.lower() and not MISTRAL_KEY: tiene_key = False
        if "together" in nombre.lower() and not TOGETHER_KEY: tiene_key = False
        if "openrouter" in nombre.lower() and not OPENROUTER_KEY: tiene_key = False
        if "hf" in nombre.lower() and not HF_TOKEN: tiene_key = False
        if "cohere" in nombre.lower() and not COHERE_KEY: tiene_key = False
        if "cerebras" in nombre.lower() and not CEREBRAS_KEY: tiene_key = False
        if "sambanova" in nombre.lower() and not SAMBANOVA_KEY: tiene_key = False
        resultado.append({"nombre": nombre, "activa": tiene_key})
    return resultado
