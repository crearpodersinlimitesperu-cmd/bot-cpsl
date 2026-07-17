# PREMIUM TEMPLATES - CREAR PODER SIN LIMITES GLOBAL
# Alineado con Disney Institute, Ritz-Carlton, McKinsey y Liderazgo Transformacional

TEMPLATES = {
    "BOUNCE_PX": (
        "Hola {nombre}, de CREAR Poder Sin Límites Global. 🌐 "
        "Tu comunicación de Capítulo Uno® retornó por error de entrega. "
        "En compromiso con tu transformación y excelencia, por favor facilítanos "
        "tu correo actual por esta vía para asegurar que recibas tu información de alto impacto. "
        "¡Tu rediseño comienza aquí!"
    ),
    "BOUNCE_IMO": (
        "Estimado IMO {nombre_imo}, de CREAR Global. 🚀 "
        "Informamos que el correo de tu invitado {nombre_px} ha rebotado. "
        "Buscamos sostener el contexto de alto impacto; por favor apóyanos validando "
        "su email correcto para asegurar su integración al Capítulo Uno®. "
        "¡Excelencia en cada paso!"
    ),
    "CONFIRMATION_RESPONSE": (
        "Bienvenido al ecosistema CREAR, {nombre}. ✨ "
        "Confirmamos tu participación en Capítulo Uno®. Estás por iniciar un viaje "
        "de consciencia, liderazgo y ejecución consistente. "
        "Mantente atento a nuestros canales oficiales. "
        "¡Un futuro de infinitas posibilidades te espera!"
    ),
    "GENERAL_NOTIFICATION": (
        "CREAR Global informa: {mensaje}. "
        "Sosteniendo el estándar de excelencia operativa para tu transformación. 🏛️"
    )
}

def get_message(tipo, **kwargs):
    tpl = TEMPLATES.get(tipo, "Mensaje de CREAR Global.")
    return tpl.format(**kwargs)
