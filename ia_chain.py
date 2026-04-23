"""
IA_CHAIN — Cadena de IAs gratuitas para CPSL Lima
==================================================
Orden de prioridad:
  1. Gemini Flash 2.0 (Google AI Studio - free tier, 1500 req/day)
  2. Groq Llama 3.1 8B (free, 14400 req/day, 30 req/min)
  3. Cohere Command Light (free tier, 1000 req/month)
  4. Ollama local (si está disponible en el servidor)
  5. Fallback: respuesta predeterminada

Uso:
  from ia_chain import ia_responder
  respuesta = ia_responder(prompt, contexto="cc_derivacion")

Contextos disponibles:
  - "cc_intent"     : detectar intención de coordinadora (cerrar, gestionar, nota)
  - "cc_nombre"     : identificar nombre de PX en texto libre de CC
  - "px_nuevo"      : respuesta empática para PX nuevos
  - "general"       : conversación general
"""
import os, re, json, logging, time
import requests

log = logging.getLogger("IAChain")

# ── Tokens de IAs gratuitas (se cargan desde env vars) ─────────
GEMINI_KEY  = os.environ.get("GOOGLE_AI_KEY","")      # Google AI Studio (gratis)
GROQ_KEY    = os.environ.get("GROQ_API_KEY","")        # Groq (gratis)
COHERE_KEY  = os.environ.get("COHERE_API_KEY","")      # Cohere (gratis)

# ── Prompts de sistema por contexto ────────────────────────────
_SYSTEM = {
    "cc_intent": (
        "Eres el sistema de detección de intenciones del bot CPSL Lima. "
        "La coordinadora escribe un mensaje en WhatsApp. "
        "Detecta si quiere: CERRAR_CASO, ACTUALIZAR_CASO, NOTA_CASO, o NINGUNA. "
        "Si detecta un nombre de persona, extráelo. "
        "Responde SOLO con JSON: "
        '{"intent":"CERRAR_CASO|ACTUALIZAR_CASO|NOTA_CASO|NINGUNA", '
        '"nombre":"<nombre extraído o vacío>", '
        '"estado":"RESUELTO|EN_GESTION|SIN_CONTACTO|", '
        '"confianza":0.0-1.0}'
    ),
    "cc_nombre": (
        "Eres un extractor de nombres. El texto puede ser un nombre parcial de persona. "
        "Extrae solo el nombre más probable. Responde SOLO el nombre, sin explicación. "
        "Si no hay nombre claro, responde vacío."
    ),
    "px_nuevo": (
        "Eres el asistente de Crear Poder Sin Límites Perú. "
        "Eres empático, cálido y orientado a la transformación personal. "
        "Responde de forma breve (máx 3 líneas) al mensaje del prospecto. "
        "No inventes información. Si preguntan detalles del evento, di que su coordinadora los contactará."
    ),
}

# ── NLP LOCAL (sin IA) — para casos simples y rápidos ──────────
_INTENTS_LOCAL = {
    # Cierre / resolución
    r'resolv[íi]|cerr[eé]|cerrado|solucion[eé]|listo\s+(el\s+caso)?|ok\s+resolv|atend[íi]': 'CERRAR_CASO',
    r'ya\s+asist[íi]|ya\s+confirm[oó]|ya\s+viene|confirm[oó]\s+asistencia': 'CERRAR_CASO',
    r'caso\s+(cerrado|resuelto)|resolv[íi]\s+(el\s+caso|a)': 'CERRAR_CASO',
    # En gestión
    r'contact[eé]\s+(a\s+)?|le\s+escrib[íi]|le\s+llam[eé]|en\s+proceso|gestion[aá]nd': 'ACTUALIZAR_CASO',
    r'le\s+dej[eé]\s+mensaje|le\s+envi[eé]|habl[eé]\s+con|pend[ií]ente\s+de\s+respuesta': 'ACTUALIZAR_CASO',
    r'me\s+pidi[oó]|me\s+dijo|habl[eé]\s+con|ya\s+le\s+escrib[íi]': 'ACTUALIZAR_CASO',
    # Sin contacto
    r'no\s+contest[oó]|no\s+responde|no\s+lo\s+(pude\s+)?contact': 'SIN_CONTACTO',
    r'n[uú]mero\s+wrong|n[uú]mero\s+eq|tel[eé]fono\s+(mal|incorrecto|apagado)': 'SIN_CONTACTO',
}

def _intent_local(texto):
    """
    Detecta la intención de la CC con regex locales.
    Retorna dict o None si no hay coincidencia segura.
    """
    t = texto.lower().strip()
    for patron, intent in _INTENTS_LOCAL.items():
        if re.search(patron, t, re.IGNORECASE):
            return {"intent": intent, "confianza": 0.85, "local": True}
    return None

def _extraer_nombre_local(texto):
    """
    Intenta extraer un nombre propio del texto usando heurística simple.
    """
    patrones = [
        r'(?:resolv[íi]|cerr[eé]|contact[eé]|habl[eé]\s+con(?:la\s+sra\s+|el\s+sr\s+)?|a)\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+){0,2})',
        r'(?:caso\s+de|PX\s+|participante\s+|sra?\s+)([A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+){0,2})',
        r'^([A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+){0,2})\s+(?:ya|resolv|confirm|contest)',
        r'([A-ZÁÉÍÓÚÑa-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑa-záéíóúñ]+){0,2})\s+(?:fue|asisti|confirm)',
    ]
    for p in patrones:
        m = re.search(p, texto, re.IGNORECASE)
        if m:
            nombre = m.group(1).strip().title()
            if len(nombre) >= 3 and nombre.lower() not in ('que', 'con', 'para', 'una', 'del', 'pero', 'mas'):
                return nombre
    return ""

# ── GEMINI Flash (Google AI Studio — gratis) ────────────────────
def _gemini(prompt, system="", timeout=8):
    if not GEMINI_KEY:
        return None
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    body = {
        "contents": [{"parts": [{"text": f"{system}\n\n{prompt}" if system else prompt}]}],
        "generationConfig": {"maxOutputTokens": 200, "temperature": 0.2}
    }
    try:
        r = requests.post(url, json=body, params={"key": GEMINI_KEY}, timeout=timeout)
        if r.status_code == 200:
            return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        log.warning(f"Gemini {r.status_code}: {r.text[:80]}")
    except Exception as e:
        log.warning(f"Gemini exc: {e}")
    return None

# ── Groq (Llama 3.1 8B — completamente gratis) ─────────────────
def _groq(prompt, system="", timeout=8):
    if not GROQ_KEY:
        return None
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            json={"model": "llama-3.1-8b-instant", "messages": messages,
                  "max_tokens": 200, "temperature": 0.2},
            headers={"Authorization": f"Bearer {GROQ_KEY}",
                     "Content-Type": "application/json"},
            timeout=timeout
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
        log.warning(f"Groq {r.status_code}: {r.text[:80]}")
    except Exception as e:
        log.warning(f"Groq exc: {e}")
    return None

# ── Cohere (Command Light — gratis limitado) ────────────────────
def _cohere(prompt, system="", timeout=8):
    if not COHERE_KEY:
        return None
    try:
        r = requests.post(
            "https://api.cohere.ai/v1/generate",
            json={"model": "command-light", "prompt": f"{system}\n\n{prompt}",
                  "max_tokens": 150, "temperature": 0.2},
            headers={"Authorization": f"Bearer {COHERE_KEY}",
                     "Content-Type": "application/json"},
            timeout=timeout
        )
        if r.status_code == 200:
            return r.json()["generations"][0]["text"].strip()
        log.warning(f"Cohere {r.status_code}: {r.text[:80]}")
    except Exception as e:
        log.warning(f"Cohere exc: {e}")
    return None

# ── Función principal: cadena de fallback ───────────────────────
def ia_responder(prompt, contexto="general", timeout=8):
    """
    Intenta con Gemini → Groq → Cohere → None
    Retorna el texto de respuesta o None si todo falla.
    """
    system = _SYSTEM.get(contexto, "")
    for fn, nombre in [(_gemini, "Gemini"), (_groq, "Groq"), (_cohere, "Cohere")]:
        try:
            resp = fn(prompt, system=system, timeout=timeout)
            if resp:
                log.info(f"IA OK via {nombre}")
                return resp
        except Exception as e:
            log.warning(f"IA {nombre} falló: {e}")
    log.warning("Todos los proveedores de IA fallaron")
    return None

def ia_detect_intent_cc(texto):
    """
    Detecta la intención de la CC en su mensaje.
    Primero prueba NLP local (sin costo), luego IA si es ambiguo.
    Retorna: {"intent": str, "nombre": str, "estado": str, "confianza": float}
    """
    # 1. Intento con NLP local (sin latencia, sin costo)
    intent_local = _intent_local(texto)
    nombre_local = _extraer_nombre_local(texto)

    if intent_local and intent_local["confianza"] >= 0.8:
        return {
            "intent":    intent_local["intent"],
            "nombre":    nombre_local,
            "estado":    _intent_a_estado(intent_local["intent"]),
            "confianza": intent_local["confianza"],
            "source":    "local"
        }

    # 2. Si es ambiguo o texto largo → usar IA
    if len(texto) > 10:
        resp_ia = ia_responder(
            f'Mensaje de coordinadora: "{texto}"',
            contexto="cc_intent",
            timeout=6
        )
        if resp_ia:
            try:
                # Extraer JSON de la respuesta
                json_str = re.search(r'\{.*\}', resp_ia, re.DOTALL)
                if json_str:
                    data = json.loads(json_str.group())
                    return {
                        "intent":    data.get("intent", "NINGUNA"),
                        "nombre":    data.get("nombre", nombre_local),
                        "estado":    data.get("estado", ""),
                        "confianza": float(data.get("confianza", 0.7)),
                        "source":    "ia"
                    }
            except Exception as e:
                log.warning(f"ia_detect_intent parse error: {e}")

    return {
        "intent": "NINGUNA",
        "nombre": nombre_local,
        "estado": "",
        "confianza": 0.0,
        "source": "ninguna"
    }

def _intent_a_estado(intent):
    return {"CERRAR_CASO": "RESUELTO", "ACTUALIZAR_CASO": "EN_GESTION",
            "SIN_CONTACTO": "SIN_CONTACTO"}.get(intent, "")

def buscar_caso_por_nombre(nombre_buscado, mis_casos):
    """
    Busca el caso más parecido al nombre dado usando fuzzy match simple.
    Retorna el caso o None.
    """
    if not nombre_buscado or not mis_casos:
        return None

    nombre_norm = nombre_buscado.lower().strip()
    # Palabras del nombre buscado (filtrar cortas)
    palabras = [p for p in nombre_norm.split() if len(p) > 2]
    if not palabras:
        return None

    mejor_caso  = None
    mejor_score = 0

    for caso in mis_casos:
        nom_caso = (caso.get("nombre") or "").lower()
        # Contar cuántas palabras del nombre buscado aparecen en el nombre del caso
        score = sum(1 for p in palabras if p in nom_caso)
        # Bonus: si empieza igual
        if nom_caso.startswith(palabras[0]):
            score += 0.5
        if score > mejor_score:
            mejor_score = score
            mejor_caso  = caso

    # Solo retornar si hay al menos 1 palabra en común
    return mejor_caso if mejor_score >= 1 else None
