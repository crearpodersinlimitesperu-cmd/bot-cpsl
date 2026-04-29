"""
sync_crearpsl.py — Sincronizador maestro CPSL Lima
====================================================
Lee 7 endpoints de crearpslglobal.com/admin cada 30 minutos y vuelca todo a
Google Sheets para que el bot-cpsl y el CRM-CREARLIMA trabajen con datos reales.

Endpoints sincronizados:
  1. datosparticipante.php?mostrar=todos
  2. reporte_detallegestion.php
  3. reporte_cierrefactura.php
  4. resultado_llamadas.php          (C1)
  5. resultado_llamadasc2.php        (C2)
  6. listar_asignaciones.php         (C1)
  7. listar_asignacionesc2.php       (C2)

Hojas destino en el Sheet maestro (variable de entorno SHEET_CRM_ID):
  CREARPSL_PARTICIPANTES
  CREARPSL_GESTION
  CREARPSL_FACTURAS
  CREARPSL_LLAMADAS_C1
  CREARPSL_LLAMADAS_C2
  CREARPSL_ASIGNACIONES_C1
  CREARPSL_ASIGNACIONES_C2
  CREARPSL_AUDITORIA      (log de cada corrida)
"""
from __future__ import annotations
import os, json, time, logging, threading
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("sync_crearpsl")
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [sync_crearpsl] %(levelname)s %(message)s"))
    log.addHandler(h)
    log.setLevel(logging.INFO)

# ── Configuración ────────────────────────────────────────────────────────
BASE_URL    = "https://crearpslglobal.com/admin"
LOGIN_URL   = f"{BASE_URL}/login.php"
USUARIO     = os.environ.get("CREARPSL_USER", "jsanchez")
PASSWORD    = os.environ.get("CREARPSL_PASS", "crearpsl25")

# Nombres de los campos del form de login. Si no son estos, ajustar vía env vars.
CAMPO_USR   = os.environ.get("CREARPSL_FIELD_USER", "usuario")
CAMPO_PWD   = os.environ.get("CREARPSL_FIELD_PASS", "password")

INTERVALO_SEG = int(os.environ.get("SYNC_INTERVAL_SEG", "1800"))  # 30 min
SHEET_ID      = os.environ.get("SHEET_CRM_ID", "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y")

ENDPOINTS = [
    {"hoja": "CREARPSL_PARTICIPANTES",     "url": f"{BASE_URL}/datosparticipante.php?mostrar=todos"},
    {"hoja": "CREARPSL_GESTION",           "url": f"{BASE_URL}/reporte_detallegestion.php"},
    {"hoja": "CREARPSL_FACTURAS",          "url": f"{BASE_URL}/reporte_cierrefactura.php"},
    {"hoja": "CREARPSL_LLAMADAS_C1",       "url": f"{BASE_URL}/resultado_llamadas.php"},
    {"hoja": "CREARPSL_LLAMADAS_C2",       "url": f"{BASE_URL}/resultado_llamadasc2.php"},
    {"hoja": "CREARPSL_ASIGNACIONES_C1",   "url": f"{BASE_URL}/listar_asignaciones.php"},
    {"hoja": "CREARPSL_ASIGNACIONES_C2",   "url": f"{BASE_URL}/listar_asignacionesc2.php"},
]


# ── Utilidades ───────────────────────────────────────────────────────────
def ahora_lima() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=5)

def normalizar_dni(v: str) -> str:
    return "".join(c for c in str(v or "") if c.isdigit())[:8]

def normalizar_telefono(v: str) -> str:
    digitos = "".join(c for c in str(v or "") if c.isdigit())
    if len(digitos) == 9:                  # 9XXXXXXXX → 519XXXXXXXX
        return f"51{digitos}"
    if len(digitos) == 11 and digitos.startswith("51"):
        return digitos
    return digitos

def normalizar_nombre(v: str) -> str:
    return " ".join(str(v or "").upper().split())


# ── Scraper ──────────────────────────────────────────────────────────────
class CrearPSLScraper:
    """
    Scraper para sistema PHP corporativo crearpslglobal.com/admin.
    Mantiene una sesión HTTP persistente con cookies.
    """

    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0 Safari/537.36",
            "Accept-Language": "es-PE,es;q=0.9",
        })
        self._logueado = False

    # ── Login ─────────────────────────────────────────────
    def login(self) -> bool:
        try:
            # 1. GET inicial para recibir cookies de sesión PHP
            self.s.get(LOGIN_URL, timeout=20)

            # 2. POST de credenciales
            payload = {CAMPO_USR: USUARIO, CAMPO_PWD: PASSWORD}
            r = self.s.post(LOGIN_URL, data=payload, timeout=20, allow_redirects=True)

            # 3. Validar éxito: si la URL final aún apunta a login.php es fail
            url_final = r.url.lower()
            if "login.php" in url_final and "error" in (r.text.lower()[:1000] if r.text else ""):
                log.error("Login falló. La página devolvió error.")
                return False
            if "login.php" in url_final and r.status_code == 200:
                # Algunos sistemas devuelven 200 sin redirigir: revisar si hay form de login
                soup = BeautifulSoup(r.text, "html.parser")
                if soup.find("input", {"type": "password"}):
                    log.error(f"Login falló. Sigue mostrando form. "
                              f"Verificar campos: {CAMPO_USR}/{CAMPO_PWD}")
                    return False

            self._logueado = True
            log.info("✅ Login OK en crearpslglobal.com")
            return True

        except Exception as e:
            log.error(f"Login excepción: {e}")
            return False

    # ── Scrape de tablas HTML ─────────────────────────────
    def scrape_tabla(self, url: str) -> List[Dict[str, Any]]:
        """
        Extrae la primera tabla con datos (>1 fila) de la URL.
        Retorna lista de dicts con headers como llaves.
        """
        try:
            r = self.s.get(url, timeout=30)
            if r.status_code != 200:
                log.warning(f"GET {url} → {r.status_code}")
                return []

            # Si nos redirigieron al login → reintentar login y refetch
            if "login.php" in r.url.lower():
                log.warning(f"Sesión expiró en {url} — re-loguenado")
                if self.login():
                    r = self.s.get(url, timeout=30)
                else:
                    return []

            soup = BeautifulSoup(r.text, "html.parser")

            # Buscar la tabla con más filas (la "principal")
            tablas = soup.find_all("table")
            if not tablas:
                log.warning(f"Sin tablas en {url}")
                return []

            tabla = max(tablas, key=lambda t: len(t.find_all("tr")))

            # Extraer headers
            headers = []
            primera = tabla.find("tr")
            if primera:
                ths = primera.find_all(["th", "td"])
                headers = [self._limpiar(th.get_text()) for th in ths]

            # Extraer filas
            filas = []
            for tr in tabla.find_all("tr")[1:]:
                celdas = [self._limpiar(td.get_text()) for td in tr.find_all(["td", "th"])]
                if not any(celdas):  # fila vacía
                    continue
                # Empatar headers con celdas
                row = {}
                for i, val in enumerate(celdas):
                    key = headers[i] if i < len(headers) else f"col_{i}"
                    row[key] = val
                filas.append(row)

            log.info(f"  · {url.split('/')[-1]} → {len(filas)} filas")
            return filas

        except Exception as e:
            log.error(f"scrape_tabla({url}) error: {e}")
            return []

    @staticmethod
    def _limpiar(s: str) -> str:
        return " ".join(str(s or "").split())


# ── Sheets writer ─────────────────────────────────────────────────────────
def conectar_sheets():
    """Retorna (svc, SHEET_ID) o (None, None) si falla."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_json = os.environ.get("GOOGLE_CREDENTIALS", "")
        if not creds_json:
            log.warning("GOOGLE_CREDENTIALS no definido")
            return None, None

        creds = service_account.Credentials.from_service_account_info(
            json.loads(creds_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        svc = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return svc, SHEET_ID
    except Exception as e:
        log.error(f"conectar_sheets error: {e}")
        return None, None


def escribir_hoja(svc, sheet_id: str, hoja: str, filas: List[Dict[str, Any]]):
    """Reemplaza el contenido de una hoja con los datos nuevos."""
    if not filas:
        log.warning(f"  ⚠ {hoja}: sin filas, no se escribe")
        return

    try:
        # 1. Crear hoja si no existe
        meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existentes = [s["properties"]["title"] for s in meta.get("sheets", [])]
        if hoja not in existentes:
            svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={
                "requests": [{"addSheet": {"properties": {"title": hoja}}}]
            }).execute()

        # 2. Limpiar la hoja
        svc.spreadsheets().values().clear(
            spreadsheetId=sheet_id, range=f"{hoja}!A:ZZ"
        ).execute()

        # 3. Escribir headers + filas
        headers = list(filas[0].keys())
        rows = [headers] + [[r.get(h, "") for h in headers] for r in filas]

        svc.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"{hoja}!A1",
            valueInputOption="RAW",
            body={"values": rows}
        ).execute()

        log.info(f"  ✓ {hoja}: {len(filas)} filas escritas")

    except Exception as e:
        log.error(f"escribir_hoja({hoja}) error: {e}")


def escribir_auditoria(svc, sheet_id: str, resultados: Dict[str, int], duracion: float):
    """Append una fila al log de auditoría."""
    try:
        meta = svc.spreadsheets().get(spreadsheetId=sheet_id).execute()
        existentes = [s["properties"]["title"] for s in meta.get("sheets", [])]
        hoja = "CREARPSL_AUDITORIA"
        if hoja not in existentes:
            svc.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={
                "requests": [{"addSheet": {"properties": {"title": hoja}}}]
            }).execute()
            svc.spreadsheets().values().update(
                spreadsheetId=sheet_id, range=f"{hoja}!A1",
                valueInputOption="RAW",
                body={"values": [["TIMESTAMP", "ENDPOINT", "FILAS", "DURACION_SEG", "ESTADO"]]}
            ).execute()

        ts = ahora_lima().strftime("%Y-%m-%d %H:%M:%S")
        rows = []
        for ep, n in resultados.items():
            rows.append([ts, ep, n, f"{duracion:.1f}", "OK" if n > 0 else "VACIO"])

        svc.spreadsheets().values().append(
            spreadsheetId=sheet_id, range=f"{hoja}!A:E",
            valueInputOption="RAW", insertDataOption="INSERT_ROWS",
            body={"values": rows}
        ).execute()
    except Exception as e:
        log.error(f"escribir_auditoria error: {e}")


# ── Loop principal ───────────────────────────────────────────────────────
def correr_una_vez():
    """Ejecuta una sincronización completa de los 7 endpoints."""
    inicio = time.time()
    log.info("═" * 60)
    log.info(f"⚡ Sincronización CrearPSL — {ahora_lima():%Y-%m-%d %H:%M:%S} Lima")
    log.info("═" * 60)

    scraper = CrearPSLScraper()
    if not scraper.login():
        log.error("Login fallido — abortando ciclo")
        return

    svc, sheet_id = conectar_sheets()
    if not svc:
        log.error("Sheets no disponible — abortando ciclo")
        return

    resultados: Dict[str, int] = {}
    for ep in ENDPOINTS:
        filas = scraper.scrape_tabla(ep["url"])
        resultados[ep["hoja"]] = len(filas)
        if filas:
            escribir_hoja(svc, sheet_id, ep["hoja"], filas)
        time.sleep(2)  # cortesía con el servidor

    duracion = time.time() - inicio
    escribir_auditoria(svc, sheet_id, resultados, duracion)

    total = sum(resultados.values())
    log.info(f"✅ Ciclo completo: {total} filas en {duracion:.1f}s")
    log.info("═" * 60)


def loop_sincronizador():
    """Loop infinito — corre cada INTERVALO_SEG segundos."""
    while True:
        try:
            correr_una_vez()
        except Exception as e:
            log.error(f"Loop error: {e}")
        log.info(f"⏸ Próxima sync en {INTERVALO_SEG//60} min...")
        time.sleep(INTERVALO_SEG)


def iniciar_thread() -> threading.Thread:
    """Llamar esto desde bot_whatsapp.py al startup."""
    t = threading.Thread(target=loop_sincronizador, daemon=True, name="sync_crearpsl")
    t.start()
    log.info(f"🚀 Sync CrearPSL iniciado — intervalo {INTERVALO_SEG//60} min")
    return t


if __name__ == "__main__":
    # Modo standalone: una corrida y termina
    correr_una_vez()
