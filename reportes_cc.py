"""
SISTEMA DE REPORTES DE COORDINADORAS — CPSL Lima
=================================================
SIN COSTO EN META — usa mensajes de texto libre (dentro de ventana de 24h)
El bot recibe el reporte de la CC → lo parsea → lo registra en Sheet → lo reenvía a José

FLUJO COMPLETO:
1. Bot solicita reporte a CC a las 12:30pm (scheduler)
2. CC responde con su reporte en formato libre
3. Bot parsea el texto → extrae OK, NC, Pendiente, Aliados
4. Registra en Google Sheet (pestaña REPORTES_CC)
5. Reenvía resumen consolidado a José (+51919563284)
6. Si CC no responde en 2h → recordatorio

COSTO META:
- La solicitud de reporte del bot → GRATIS si la CC respondió en las últimas 24h
  (ventana de conversación abierta = mensajes de texto libre = $0)
- Si la ventana está cerrada → usa plantilla de notificación (mínimo costo)
"""

import os, re, json, logging, threading, time
from datetime import datetime, timedelta, timezone

log = logging.getLogger("ReportesCC")
TZ  = timezone(timedelta(hours=-5))

def ahora(): return datetime.now(TZ)

# ── CONFIGURACIÓN ──────────────────────────────────────────────
JOSE_TEL   = "51919563284"
HORA_REPORTE = os.environ.get("REPORTE_HORA", "12:30")

CCS = {
    "51912379744": {"nombre": "Diana Moscoso",  "key": "dmoscoso"},
    "51933599903": {"nombre": "Joyce Marín",    "key": "jmarin"},
    "51933599864": {"nombre": "Zuley Urteaga",  "key": "zurteaga"},
}

# Almacén en memoria de reportes del día
_reportes_hoy = {}  # key → {cc, hora, raw, parsed, enviado_a_jose}
_reportes_lk  = threading.Lock()

# ── PARSER DE REPORTES ─────────────────────────────────────────
def _parsear_campos(bloque):
    """Extrae dict {CAMPO: valor_int} de un bloque de texto.
    Soporta: 'OK = 11', 'NC= 8', 'pendiente=15', '* Pendiente: 66'
    """
    campos = {}
    for line in bloque.split('\n'):
        line_clean = re.sub(r'[*•✅❌⏸🚫⏳🔄\u200b]', '', line).strip()
        m = re.search(r'([A-Za-záéíóúñÑ]+)\s*[=:]\s*(\d+)', line_clean)
        if m:
            campos[m.group(1).upper()] = int(m.group(2))
    return campos

def _partir_secciones(texto):
    """
    Divide el reporte en secciones por encabezado.
    Retorna dict {nombre_seccion_normalizado: bloque_texto}
    """
    # Limpiar asteriscos de formato WhatsApp del encabezado
    texto_limpio = re.sub(r'\*([^*]+)\*', r'\1', texto)
    # Partir por líneas que parecen encabezados: "Nuevos Cap 1:", "Rezagados Cap 1:", etc.
    patron = r'\n(?=\s*(?:Nuevos|Rezagados|Aliados|FDS|GRAN)\s)'
    partes = re.split(patron, '\n' + texto_limpio, flags=re.IGNORECASE)
    secciones = {}
    for parte in partes:
        parte = parte.strip()
        if not parte:
            continue
        lineas = parte.split('\n')
        encabezado = lineas[0].strip().rstrip(':').lower()
        contenido  = '\n'.join(lineas[1:])
        # Normalizar clave
        if re.search(r'nuevo', encabezado, re.IGNORECASE):
            secciones['nuevos'] = contenido
        elif re.search(r'rezagado', encabezado, re.IGNORECASE):
            secciones['rezagados'] = contenido
        elif re.search(r'aliado', encabezado, re.IGNORECASE):
            secciones['aliados'] = contenido
    return secciones



def parsear_reporte(texto, cc_nom):
    """
    Parsea el texto libre del reporte de la coordinadora.
    Soporta el formato C1 E27: Nuevos Cap 1 + Rezagados Cap 1
    con campos OK, SIG, NC, XC, NI, Pendiente, Total.
    Tambien soporta el formato FDS por equipo de Linid.
    """
    r = {
        "cc":        cc_nom,
        "hora":      ahora().strftime("%d/%m/%Y %H:%M"),
        "nuevos":    {},   # Nuevos Cap 1
        "rezagados": {},   # Rezagados Cap 1
        "fds":       [],   # Formato Linid por equipo
        "gran_total": "",
        "notas":      "",
        "raw":        texto.strip()
    }

    tiene_nuevos    = bool(re.search(r'nuevo|Nuevo|NUEVO', texto))
    tiene_rezagados = bool(re.search(r'rezagado|Rezagado|REZAGADO', texto))
    tiene_fds       = bool(re.search(r'FDS|fds|GRAN TOTAL', texto, re.IGNORECASE))

    if tiene_nuevos or tiene_rezagados:
        # Partir el reporte por secciones
        secciones = _partir_secciones(texto)
        if secciones.get('nuevos'):
            r['nuevos'] = _parsear_campos(secciones['nuevos'])
        if secciones.get('rezagados'):
            r['rezagados'] = _parsear_campos(secciones['rezagados'])
        if secciones.get('aliados'):
            r['aliados'] = _parsear_campos(secciones['aliados'])
        # Notas libres
        notas_m = re.search(r'[Nn]ota[s]?\s*[:=]\s*(.+)', texto)
        if notas_m:
            r['notas'] = notas_m.group(1).strip()[:200]

    elif tiene_fds:
        # Formato Linid — FDS por equipo
        blocks = re.findall(r'(\d+)\s*FDS\s*(E\d+)(.*?)(?=\d+\s*FDS|GRAN\s*TOTAL|$)',
                             texto, re.DOTALL | re.IGNORECASE)
        for num, eq, blk in blocks:
            fds_data = {'num': num, 'equipo': eq}
            for line in blk.split('\n'):
                m = re.search(r'[*\u2022]?\s*(PX|MNG|CAPI|TOTAL|NOTA)\s*[=:]\s*(.+)',
                               line, re.IGNORECASE)
                if m:
                    fds_data[m.group(1).upper()] = m.group(2).strip()
            r['fds'].append(fds_data)
        gt = re.search(r'GRAN\s*TOTAL\s*[:\s]*(\d+/\d+)', texto, re.IGNORECASE)
        if gt:
            r['gran_total'] = gt.group(1)

    else:
        # Formato libre — extraer todo lo que tenga KEY = Número
        for line in texto.split('\n'):
            m = re.search(r'[*\u2022]?\s*(\w+)\s*[=:]\s*(\d+)', line)
            if m:
                r['nuevos'][m.group(1).upper()] = int(m.group(2))

    return r

def _fmt_bloque(titulo, d):
    """Formatea un bloque de datos de reporte."""
    if not d:
        return ''
    ok   = d.get('OK',0)
    sig  = d.get('SIG',0)
    nc   = d.get('NC',0)
    xc   = d.get('XC',0)
    ni   = d.get('NI',0)
    pend = d.get('PENDIENTE', d.get('PEND', d.get('PENDIENTE', 0)))
    tot  = d.get('TOTAL', ok+sig+nc+xc+ni+pend)
    return (
        f"\n{titulo}\n"
        f"  ✅ OK: *{ok}*  🔄 SIG: *{sig}*  ❌ NC: *{nc}*\n"
        f"  ⏸ XC: *{xc}*  🚫 NI: *{ni}*  ⏳ Pend: *{pend}*\n"
        f"  Total: *{tot}*"
    )

def formatear_reporte(r, include_raw=False):
    """Genera el texto de resumen del reporte parseado."""
    cc   = r.get('cc', '?')
    hora = r.get('hora', '')
    lines = [f"📊 *Reporte {cc}* — {hora}"]

    blk_n = _fmt_bloque('🆕 *Nuevos Cap 1 (E27):*', r.get('nuevos',{}))
    if blk_n:
        lines.append(blk_n)

    blk_r = _fmt_bloque('📉 *Rezagados Cap 1:*', r.get('rezagados',{}))
    if blk_r:
        lines.append(blk_r)

    if r.get('fds'):
        lines.append('\n📋 *FDS por equipo:*')
        for fds in r['fds']:
            eq    = fds.get('equipo', '')
            total = fds.get('TOTAL', '?')
            px    = fds.get('PX', '')
            nota  = fds.get('NOTA', '')
            nota_str = f' ⚠️ {nota[:40]}' if nota and nota.strip() not in ('','(Vacío)') else ''
            lines.append(f'  FDS {eq}: {total} (PX {px}){nota_str}')
        if r.get('gran_total'):
            lines.append(f"  🏆 *GRAN TOTAL: {r['gran_total']}*")

    if r.get('notas'):
        lines.append(f"\n📝 Nota: {r['notas']}")

    if include_raw and r.get('raw'):
        lines.append(f"\n_Mensaje original:_\n{r['raw'][:300]}")

    return '\n'.join(lines)

def consolidar_reportes():
    """Genera resumen consolidado de todas las CCs para José."""
    with _reportes_lk:
        rep = dict(_reportes_hoy)

    if not rep:
        return None

    hora_s = ahora().strftime("%d/%m/%Y %H:%M")
    lines  = [f"📊 *CONSOLIDADO REPORTES — CPSL Lima*\n_{hora_s}_\n"]

    # Sumar totales de rezagados
    tot_ok = tot_nc = tot_pend = tot_total = 0
    for key, r in rep.items():
        d = r.get("parsed", {})
        if d.get("rezagados"):
            tot_ok   += d["rezagados"].get("OK", 0)
            tot_nc   += d["rezagados"].get("NC", 0)
            tot_pend += d["rezagados"].get("PENDIENTE", d["rezagados"].get("PEND", 0))
            tot_total+= d["rezagados"].get("TOTAL", 0)

    for key, r in sorted(rep.items()):
        lines.append(formatear_reporte(r.get("parsed", {})))
        lines.append("─" * 30)

    if tot_total > 0:
        lines.append(
            f"\n📈 *TOTALES REZAGADOS:*\n"
            f"  ✅ OK: {tot_ok}  |  ❌ NC: {tot_nc}  |  ⏳ Pend: {tot_pend}\n"
            f"  Total gestionado: {tot_total}"
        )

    ccs_faltantes = [CCS[t]["nombre"] for t in CCS if t not in rep]
    if ccs_faltantes:
        lines.append(f"\n⚠️ *Sin reporte:* {', '.join(ccs_faltantes)}")

    return "\n".join(lines)

def registrar_reporte(tel_cc, texto_raw):
    """
    Registra y procesa el reporte de una coordinadora.
    Retorna el texto de respuesta para enviarle a la CC.
    """
    cc_info = CCS.get(tel_cc, {})
    cc_nom  = cc_info.get("nombre", "CC")
    cc_key  = cc_info.get("key", tel_cc)

    parsed  = parsear_reporte(texto_raw, cc_nom)
    hora_s  = ahora().strftime("%d/%m/%Y %H:%M:%S")

    with _reportes_lk:
        _reportes_hoy[cc_key] = {
            "cc":     cc_nom,
            "tel":    tel_cc,
            "hora":   hora_s,
            "raw":    texto_raw,
            "parsed": parsed,
        }

    resumen = formatear_reporte(parsed)
    log.info(f"Reporte registrado: {cc_nom} | {hora_s}")

    return resumen, parsed

def reportes_pendientes():
    """Lista de CCs que aún no enviaron reporte hoy."""
    with _reportes_lk:
        enviados = set(_reportes_hoy.keys())
    return [
        {"nombre": info["nombre"], "tel": tel, "key": info["key"]}
        for tel, info in CCS.items()
        if info["key"] not in enviados
    ]
