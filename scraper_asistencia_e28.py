"""
SCRAPER DE ASISTENCIA E28 — reporte_equipos.php
=================================================
Extrae el estado de asistencia del portal IMO para el Equipo 28.
Detecta:
  - CONFIRMADO → se sentó (asistió)
  - PENDIENTE  → aún sin confirmar
  - DESERTOR / NO ASISTIÓ → desertó
  
Actualiza torre_control.db con el estado real.
Se puede programar para correr cada 12 horas.
"""
import os
import sys
import time
import re
import sqlite3
import unicodedata
import argparse
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
URL_REPORTE = "https://crearpslglobal.com/admin/reporte_equipos.php"

CUENTAS = {
    "dmoscoso": {"pass": "crear2025", "nombre": "Diana Moscoso"},
    "jmarin": {"pass": "crear2025", "nombre": "Joyce Marín"},
}

EQUIPO_LABEL = "EQUIPO 28 - CICLO_I"

LOG_FILE = os.path.join(BASE_DIR, "reporte_asistencia_e28.log")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def norm(s):
    if not s or str(s) == 'nan':
        return ''
    s = str(s).strip().upper()
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return ' '.join(s.split())

def extraer_asistencia_e28():
    """Scrape E28 attendance from the portal."""
    log("=" * 65)
    log("  SCRAPER DE ASISTENCIA — EQUIPO 28")
    log("=" * 65)
    
    from playwright.sync_api import sync_playwright
    
    participantes = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Solo necesitamos un usuario para ver el reporte
        user = "dmoscoso"
        info = CUENTAS[user]
        
        log(f"Iniciando sesión como {info['nombre']}...")
        page = browser.new_page()
        
        try:
            # 1. Login
            page.goto(URL_LOGIN, timeout=30000)
            page.fill("input[name='usuario']", user)
            page.fill("input[name='password']", info["pass"])
            page.click("button[name='ingresar']")
            page.wait_for_load_state("networkidle")
            
            if "login.php" in page.url.lower():
                log("❌ Error de login. Intentando con jmarin...")
                page.close()
                page = browser.new_page()
                user = "jmarin"
                info = CUENTAS[user]
                page.goto(URL_LOGIN, timeout=30000)
                page.fill("input[name='usuario']", user)
                page.fill("input[name='password']", info["pass"])
                page.click("button[name='ingresar']")
                page.wait_for_load_state("networkidle")
                
                if "login.php" in page.url.lower():
                    log("❌ Error: No se pudo iniciar sesión con ninguna cuenta.")
                    browser.close()
                    return []
            
            log(f"✅ Sesión iniciada como {info['nombre']}")
            
            # 2. Navegar al reporte de equipos
            page.goto(URL_REPORTE, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 3. Seleccionar EQUIPO 28
            try:
                page.select_option("#cbnEquipo", label=EQUIPO_LABEL)
            except:
                # Intentar con value
                options = page.query_selector_all("#cbnEquipo option")
                for opt in options:
                    text = opt.inner_text().strip()
                    if "28" in text and "CICLO_I" in text:
                        val = opt.get_attribute("value")
                        page.select_option("#cbnEquipo", value=val)
                        break
            
            # 4. Hacer clic en Consultar
            try:
                page.click("#invoice_btn", timeout=5000)
            except:
                page.click("button:has-text('Consultar')", timeout=5000)
            
            page.wait_for_load_state("networkidle")
            time.sleep(3)
            
            # 5. Mostrar todas las filas (400)
            try:
                page.select_option("select[name='example_length']", value="400")
                time.sleep(2)
            except:
                pass
            
            # 6. Extraer tabla
            rows = page.query_selector_all("#example tbody tr")
            log(f"Filas encontradas: {len(rows)}")
            
            # Obtener headers
            headers = []
            header_row = page.query_selector("#example thead tr")
            if header_row:
                headers = [th.inner_text().strip() for th in header_row.query_selector_all("th")]
            log(f"Headers: {headers}")
            
            for r in rows:
                cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                if not cells or len(cells) < 8 or "no data" in cells[0].lower():
                    continue
                
                # Mapear según la estructura visible en el screenshot:
                # Sede | NombreEquipo | Identificación | ApellidoCompleto | NombreCompleto | 
                # TeléfonoMóvil | PagoCapitulo2 | PagoMaestría | Asistencia | AsistenciaC2 | TipoBase | FD
                px = {
                    "sede": cells[0] if len(cells) > 0 else "",
                    "equipo": cells[1] if len(cells) > 1 else "",
                    "identificacion": cells[2] if len(cells) > 2 else "",
                    "apellido": cells[3] if len(cells) > 3 else "",
                    "nombre": cells[4] if len(cells) > 4 else "",
                    "telefono": cells[5] if len(cells) > 5 else "",
                    "pago_c2": cells[6] if len(cells) > 6 else "",
                    "pago_maestria": cells[7] if len(cells) > 7 else "",
                    "asistencia": cells[8] if len(cells) > 8 else "",
                    "asistencia_c2": cells[9] if len(cells) > 9 else "",
                    "tipo_base": cells[10] if len(cells) > 10 else "",
                }
                participantes.append(px)
            
            log(f"✅ {len(participantes)} participantes extraídos del E28")
            
        except Exception as e:
            log(f"❌ Error: {e}")
        finally:
            page.close()
            browser.close()
    
    return participantes

def clasificar_asistencia(participantes):
    """Clasifica participantes por estado de asistencia."""
    sentados = []        # CONFIRMADO = se sentó
    pendientes = []      # PENDIENTE = sin confirmar
    desertores = []      # Otros = desertó
    
    for px in participantes:
        asist = px.get("asistencia", "").upper().strip()
        if asist == "CONFIRMADO":
            sentados.append(px)
        elif asist == "PENDIENTE" or asist == "":
            pendientes.append(px)
        else:
            desertores.append(px)
    
    return sentados, pendientes, desertores

def actualizar_db(participantes, sentados, pendientes, desertores):
    """Actualiza torre_control.db con los estados de asistencia."""
    log(f"\nActualizando torre_control.db...")
    
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    c = conn.cursor()
    
    updated_sentados = 0
    updated_desertores = 0
    not_found = 0
    
    for px in participantes:
        dni = px.get("identificacion", "").strip()
        asist = px.get("asistencia", "").upper().strip()
        nombre_completo = f"{px.get('nombre','')} {px.get('apellido','')}"
        
        # Buscar por DNI en la DB
        if dni:
            c.execute("SELECT id, estado FROM participantes WHERE identificacion=?", (dni,))
            row = c.fetchone()
            
            if not row:
                # Buscar por teléfono
                tel = re.sub(r'\D', '', px.get("telefono", ""))
                if len(tel) >= 9:
                    tel_suffix = tel[-9:]
                    c.execute("SELECT id, estado FROM participantes WHERE telefono LIKE ?", (f"%{tel_suffix}%",))
                    row = c.fetchone()
            
            if row:
                pid, estado_actual = row
                
                if asist == "CONFIRMADO":
                    # Se sentó — actualizar c1='SI' si no lo tiene
                    c.execute(
                        "UPDATE participantes SET c1='SI', estado='ACTIVO' WHERE id=? AND (c1 IS NULL OR c1!='SI')",
                        (pid,)
                    )
                    if c.rowcount > 0:
                        updated_sentados += 1
                        
                elif asist not in ("PENDIENTE", ""):
                    # Desertó
                    if estado_actual != 'DESERTOR':
                        c.execute(
                            "UPDATE participantes SET estado='DESERTOR' WHERE id=?",
                            (pid,)
                        )
                        updated_desertores += 1
            else:
                not_found += 1
    
    conn.commit()
    
    # Resultados
    log(f"\n{'='*65}")
    log(f"  RESUMEN DE ACTUALIZACIÓN")
    log(f"{'='*65}")
    log(f"  Total participantes E28:  {len(participantes)}")
    log(f"  ✅ Sentados (CONFIRMADO): {len(sentados)}")
    log(f"  ⏳ Pendientes:            {len(pendientes)}")
    log(f"  ❌ Desertores:            {len(desertores)}")
    log(f"  DB actualizados sentados: +{updated_sentados}")
    log(f"  DB actualizados desert.:  +{updated_desertores}")
    log(f"  No encontrados en DB:     {not_found}")
    log(f"{'='*65}")
    
    # Mostrar desertores si los hay
    if desertores:
        log(f"\n--- DESERTORES DETECTADOS ---")
        for d in desertores:
            log(f"  ❌ {d['nombre']} {d['apellido']} | DNI: {d['identificacion']} | Tel: {d['telefono']} | Asist: {d['asistencia']}")
    
    # Mostrar sentados
    if sentados:
        log(f"\n--- SENTADOS (CONFIRMADOS) --- Primeros 20")
        for s in sentados[:20]:
            log(f"  ✅ {s['nombre']} {s['apellido']} | DNI: {s['identificacion']} | Tel: {s['telefono']}")
    
    conn.close()
    return len(sentados), len(pendientes), len(desertores)

def guardar_csv(participantes, sentados, pendientes, desertores):
    """Guarda un CSV de respaldo con el reporte."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # CSV completo
    df = pd.DataFrame(participantes)
    csv_path = os.path.join(BASE_DIR, f"asistencia_e28_{ts}.csv")
    df.to_csv(csv_path, index=False, encoding='utf-8')
    log(f"📁 CSV guardado: {csv_path}")
    
    # CSV de desertores
    if desertores:
        df_d = pd.DataFrame(desertores)
        csv_d = os.path.join(BASE_DIR, f"desertores_e28_{ts}.csv")
        df_d.to_csv(csv_d, index=False, encoding='utf-8')
        log(f"📁 CSV desertores: {csv_d}")

def ejecutar():
    """Ejecuta el scraping, clasificación y actualización."""
    participantes = extraer_asistencia_e28()
    
    if not participantes:
        log("⚠️ No se extrajeron participantes. Abortando.")
        return
    
    sentados, pendientes, desertores = clasificar_asistencia(participantes)
    actualizar_db(participantes, sentados, pendientes, desertores)
    guardar_csv(participantes, sentados, pendientes, desertores)
    
    log(f"\n✅ Proceso completado a las {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper de asistencia E28")
    parser.add_argument("--loop", action="store_true", help="Ejecutar cada 12 horas en bucle")
    parser.add_argument("--interval", type=int, default=12, help="Intervalo en horas (default: 12)")
    args = parser.parse_args()
    
    if args.loop:
        log(f"Iniciando modo bucle (cada {args.interval} horas)...")
        while True:
            try:
                ejecutar()
            except Exception as ex:
                log(f"❌ Error en bucle: {ex}")
            next_run = datetime.now().strftime('%H:%M') 
            log(f"Próxima ejecución en {args.interval} horas...")
            time.sleep(args.interval * 3600)
    else:
        ejecutar()
