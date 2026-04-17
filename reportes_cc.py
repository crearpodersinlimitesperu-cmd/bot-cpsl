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
def parsear_reporte(texto, cc_nom):
    """
    Parsea el texto libre del reporte de la coordinadora.
    Soporta los formatos de Diana, Zuley y Linid.
    """
    r = {
        "cc":       cc_nom,
        "hora":     ahora().strftime("%d/%m/%Y %H:%M"),
        "rezagados": {},
        "aliados":   {},
        "fds":       [],
        "gran_total": "",
        "raw":       texto.strip()
    }

    tiene_rezagados = bool(re.search(r'rezagado|Rezagado|REZAGADO', texto))
    tiene_fds       = bool(re.search(r'FDS|fds|GRAN TOTAL', texto))

    if tiene_rezagados:
        # Formato Diana / Zuley
        rez = re.search(r'[Rr]ezagados?[^:]*:(.*?)(?:✅|[Aa]liados|$)', texto, re.DOTALL)
        if rez:
            for line in rez.group(1).split('\n'):
                m = re.search(r'[*•]?\s*(\w+)\s*[=:]\s*(\d+)', line)
                if m:
                    r["rezagados"][m.group(1).upper()] = int(m.group(2))

        ali = re.search(r'[Aa]liados?[^:]*:(.*?)$', texto, re.DOTALL)
        if ali:
            for line in ali.group(1).split('\n'):
                m = re.search(r'[*•]?\s*(\w+)\s*[=:]\s*(\d+)', line)
                if m:
                    r["aliados"][m.group(1).upper()] = int(m.group(2))

    elif tiene_fds:
        # Formato Linid - múltiples equipos
        blocks = re.findall(r'(\d+)\s*FDS\s*(E\d+)(.*?)(?=\d+\s*FDS|GRAN\s*TOTAL|$)', texto, re.DOTALL|re.IGNORECASE)
        for num, eq, blk in blocks:
            fds_data = {"num": num, "equipo": eq}
            for line in blk.split('\n'):
                m = re.search(r'[*•]?\s*(PX|MNG|CAPI|TOTAL|NOTA)\s*[=:]\s*(.+)', line, re.IGNORECASE)
                if m:
                    fds_data[m.group(1).upper()] = m.group(2).strip()
            r["fds"].append(fds_data)

        gt = re.search(r'GRAN\s*TOTAL\s*[:\s]*(\d+/\d+)', texto, re.IGNORECASE)
        if gt:
            r["gran_total"] = gt.group(1)

    else:
        # Formato libre — intentar extraer números clave
        numeros = re.findall(r'(\w+)\s*[:=]\s*(\d+)', texto)
        for clave, val in numeros:
            r["rezagados"][clave.upper()] = int(val)

    return r

def formatear_reporte(r, include_raw=True):
    """Genera el texto de resumen del reporte parseado."""
    cc  = r.get("cc", "?")
    hora = r.get("hora", "")
    lines = [f"📊 *Reporte {cc}* — {hora}"]

    if r.get("rezagados"):
        d = r["rezagados"]
        ok   = d.get("OK", 0)
        pend = d.get("PENDIENTE", d.get("PEND", 0))
        nc   = d.get("NC", 0)
        xc   = d.get("XC", 0)
        sig  = d.get("SIG", 0)
        ni   = d.get("NI", 0)
        tot  = d.get("TOTAL", 0)
        lines.append(
            f"\n📉 *Rezagados C1:*\n"
            f"  ✅ OK: {ok}  |  🔄 SIG: {sig}  |  ❌ NC: {nc}\n"
            f"  ⏸ XC: {xc}  |  🚫 NI: {ni}  |  ⏳ Pendiente: {pend}\n"
            f"  Total: {tot}"
        )

    if r.get("aliados"):
        d = r["aliados"]
        ok   = d.get("OK", 0)
        pend = d.get("PEND", d.get("PENDIENTE", 0))
        nc   = d.get("NC", 0)
        xc   = d.get("XC", 0)
        ni   = d.get("NI", 0)
        tot  = d.get("TOTAL", 0)
        lines.append(
            f"\n✅ *Aliados C1 E27:*\n"
            f"  ✅ OK: {ok}  |  ❌ NC: {nc}  |  ⏸ XC: {xc}\n"
            f"  🚫 NI: {ni}  |  ⏳ Pend: {pend}  |  Total: {tot}"
        )

    if r.get("fds"):
        lines.append(f"\n📋 *FDS por equipo:*")
        for fds in r["fds"]:
            eq    = fds.get("equipo", "")
            total = fds.get("TOTAL", "?")
            px    = fds.get("PX", "")
            nota  = fds.get("NOTA", "")
            nota_str = f" ⚠️ {nota[:40]}" if nota and nota.strip() and nota.strip() != "(Vacío)" else ""
            lines.append(f"  FDS {eq}: {total} (PX {px}){nota_str}")
        if r.get("gran_total"):
            lines.append(f"\n  🏆 *GRAN TOTAL: {r['gran_total']}*")

    return "\n".join(lines)

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

