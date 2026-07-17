"""
SCRAPER DE ASISTENCIA E28 — reporte_asistencia.php (FUENTE REAL)
=================================================================
Total real: 199 participantes | 112 CONFIRMADOS | 4 DESERTORES | 83 PENDIENTES
"""
import os
import sys
import time
import re
import sqlite3
import unicodedata
import pandas as pd
from datetime import datetime

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")

URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
URL_ASISTENCIA = "https://crearpslglobal.com/admin/reporte_asistencia.php"

CUENTAS = {
    "dmoscoso": {"pass": "crear2025", "nombre": "Diana Moscoso"},
    "jmarin": {"pass": "crear2025", "nombre": "Joyce Marín"},
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def extraer_asistencia_real():
    """Scrape reporte_asistencia.php — fuente definitiva."""
    log("=" * 65)
    log("  SCRAPER ASISTENCIA REAL — reporte_asistencia.php")
    log("=" * 65)
    
    from playwright.sync_api import sync_playwright
    
    participantes = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        for user, info in CUENTAS.items():
            log(f"Intentando login con {user}...")
            page = browser.new_page()
            
            try:
                page.goto(URL_LOGIN, timeout=30000)
                page.fill("input[name='usuario']", user)
                page.fill("input[name='password']", info["pass"])
                page.click("button[name='ingresar']")
                page.wait_for_load_state("networkidle")
                
                if "login.php" in page.url.lower():
                    log(f"❌ Login fallido con {user}")
                    page.close()
                    continue
                
                log(f"✅ Sesión iniciada como {info['nombre']}")
                
                # Ir al reporte de asistencia
                page.goto(URL_ASISTENCIA, timeout=30000)
                page.wait_for_load_state("networkidle")
                time.sleep(2)
                
                # Seleccionar EQUIPO 28
                try:
                    page.select_option("#cbnEquipo", label="EQUIPO 28")
                except:
                    options = page.query_selector_all("#cbnEquipo option")
                    for opt in options:
                        text = opt.inner_text().strip()
                        if "28" in text:
                            val = opt.get_attribute("value")
                            page.select_option("#cbnEquipo", value=val)
                            log(f"  Seleccionado: {text}")
                            break
                
                # Consultar
                try:
                    page.click("button:has-text('Consultar')", timeout=5000)
                except:
                    page.click("#invoice_btn", timeout=5000)
                
                page.wait_for_load_state("networkidle")
                time.sleep(3)
                
                # Mostrar 400 por página
                try:
                    page.select_option("select[name='example_length']", value="400")
                    time.sleep(2)
                except:
                    pass
                
                # Extraer headers
                headers = []
                header_els = page.query_selector_all("#example thead th, table thead th")
                if header_els:
                    headers = [h.inner_text().strip() for h in header_els]
                log(f"Headers: {headers}")
                
                # Extraer filas
                rows = page.query_selector_all("#example tbody tr, table tbody tr")
                log(f"Filas: {len(rows)}")
                
                for r in rows:
                    cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                    if not cells or len(cells) < 6 or "no data" in cells[0].lower():
                        continue
                    
                    # Estructura visible del screenshot:
                    # Ficha | Asistencia | Equipo | Usuario Seguimiento | Identificación | Apellido Completo | Nombre Completo | ...
                    px = {
                        "ficha": cells[0] if len(cells) > 0 else "",
                        "asistencia": cells[1] if len(cells) > 1 else "",
                        "equipo": cells[2] if len(cells) > 2 else "",
                        "usuario_seguimiento": cells[3] if len(cells) > 3 else "",
                        "identificacion": cells[4] if len(cells) > 4 else "",
                        "apellido": cells[5] if len(cells) > 5 else "",
                        "nombre": cells[6] if len(cells) > 6 else "",
                    }
                    
                    # Capture remaining columns
                    if len(cells) > 7:
                        px["telefono"] = cells[7] if len(cells) > 7 else ""
                    if len(cells) > 8:
                        px["extra1"] = cells[8]
                    if len(cells) > 9:
                        px["extra2"] = cells[9]
                    
                    # Clean asistencia (remove extra whitespace, "Actualizar Asistencia" etc)
                    asist = px["asistencia"].upper().strip()
                    if "CONFIRMADO" in asist:
                        px["asistencia"] = "CONFIRMADO"
                    elif "DESERTOR" in asist:
                        px["asistencia"] = "DESERTOR"
                    elif "PENDIENTE" in asist:
                        px["asistencia"] = "PENDIENTE"
                    elif "ACTUALIZAR" in asist:
                        px["asistencia"] = "PENDIENTE"
                    
                    participantes.append(px)
                
                log(f"✅ {len(participantes)} participantes extraídos")
                page.close()
                break  # Solo necesitamos un usuario
                
            except Exception as e:
                log(f"❌ Error: {e}")
                page.close()
                continue
        
        browser.close()
    
    return participantes

def actualizar_db(participantes):
    """Actualiza torre_control.db con la asistencia real."""
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()
    
    confirmados = 0
    desertores = 0
    pendientes = 0
    not_found = []
    added_new = 0
    
    for px in participantes:
        dni = px.get("identificacion", "").strip()
        nombre = px.get("nombre", "").strip()
        apellido = px.get("apellido", "").strip()
        asist = px.get("asistencia", "").upper()
        telefono = re.sub(r'\D', '', px.get("telefono", ""))
        
        # Buscar por DNI
        found_id = None
        if dni:
            c.execute("SELECT id FROM participantes WHERE identificacion=?", (dni,))
            r = c.fetchone()
            if r:
                found_id = r[0]
            else:
                stripped = dni.lstrip('0')
                c.execute("SELECT id FROM participantes WHERE REPLACE(LTRIM(COALESCE(identificacion,''),'0'),' ','') = ?", (stripped,))
                r = c.fetchone()
                if r:
                    found_id = r[0]
        
        # Por teléfono
        if not found_id and telefono and len(telefono) >= 9:
            c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{telefono[-9:]}%",))
            r = c.fetchone()
            if r:
                found_id = r[0]
        
        # Por nombre+apellido
        if not found_id and nombre and apellido:
            c.execute("""SELECT id FROM participantes 
                        WHERE UPPER(COALESCE(nombre,''))=UPPER(?) 
                          AND UPPER(COALESCE(apellido,''))=UPPER(?)""", (nombre, apellido))
            r = c.fetchone()
            if r:
                found_id = r[0]
        
        if not found_id:
            # Insertar nuevo
            estado = 'ACTIVO' if asist == 'CONFIRMADO' else ('DESERTOR' if asist == 'DESERTOR' else 'PENDIENTE')
            c1_val = 'SI' if asist == 'CONFIRMADO' else 'NO'
            c.execute("""INSERT INTO participantes (nombre, apellido, identificacion, equipo, estado, c1)
                        VALUES (?, ?, ?, 'EQUIPO 28', ?, ?)""", (nombre, apellido, dni, estado, c1_val))
            added_new += 1
            if asist == 'CONFIRMADO':
                confirmados += 1
            elif asist == 'DESERTOR':
                desertores += 1
            else:
                pendientes += 1
            continue
        
        # Actualizar existente
        if asist == 'CONFIRMADO':
            c.execute("UPDATE participantes SET c1='SI', estado='ACTIVO', equipo='EQUIPO 28' WHERE id=?", (found_id,))
            confirmados += 1
        elif asist == 'DESERTOR':
            c.execute("UPDATE participantes SET c1='NO', estado='DESERTOR', equipo='EQUIPO 28' WHERE id=?", (found_id,))
            desertores += 1
        else:
            c.execute("UPDATE participantes SET equipo='EQUIPO 28' WHERE id=?", (found_id,))
            pendientes += 1
    
    conn.commit()
    
    # Verificar Eliana Jara
    c.execute("SELECT id, nombre, apellido, c1, estado FROM participantes WHERE identificacion LIKE '%7938881%'")
    jara = c.fetchall()
    
    # Stats E28
    e28_c1 = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo='EQUIPO 28' AND c1='SI'").fetchone()[0]
    e28_total = c.execute("SELECT COUNT(*) FROM participantes WHERE equipo='EQUIPO 28'").fetchone()[0]
    
    log(f"\n{'='*65}")
    log(f"  RESULTADO ACTUALIZACIÓN ASISTENCIA E28")
    log(f"{'='*65}")
    log(f"  Total procesados: {len(participantes)}")
    log(f"  ✅ CONFIRMADOS → C1=SI: {confirmados}")
    log(f"  ❌ DESERTORES: {desertores}")
    log(f"  ⏳ PENDIENTES: {pendientes}")
    log(f"  🆕 Nuevos agregados: {added_new}")
    log(f"\n  E28 C1=SI total: {e28_c1}")
    log(f"  E28 total: {e28_total}")
    
    if jara:
        log(f"\n  📋 ELIANA JARA: C1={jara[0][3]} | Estado={jara[0][4]}")
    
    log(f"{'='*65}")
    
    # Guardar CSV
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_out = pd.DataFrame(participantes)
    csv_path = os.path.join(BASE_DIR, f"asistencia_real_e28_{ts}.csv")
    df_out.to_csv(csv_path, index=False, encoding='utf-8')
    log(f"📁 CSV: {csv_path}")
    
    conn.close()

if __name__ == "__main__":
    pxs = extraer_asistencia_real()
    if pxs:
        actualizar_db(pxs)
    else:
        log("⚠️ No se extrajeron participantes")
