"""
SCRAPER DE ASISTENCIA TODOS LOS EQUIPOS
=================================================================
Itera sobre todos los equipos en reporte_asistencia.php y actualiza la DB.
"""
import os
import sys
import time
import re
import sqlite3
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
}

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def extraer_y_actualizar_todos():
    log("=" * 65)
    log("  SCRAPER ASISTENCIA TODOS LOS EQUIPOS")
    log("=" * 65)
    
    from playwright.sync_api import sync_playwright
    
    all_participantes = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        user = list(CUENTAS.keys())[0]
        info = CUENTAS[user]
        
        log(f"Iniciando sesión con {user}...")
        try:
            page.goto(URL_LOGIN, timeout=30000)
            page.fill("input[name='usuario']", user)
            page.fill("input[name='password']", info["pass"])
            page.click("button[name='ingresar']")
            page.wait_for_load_state("networkidle")
            
            if "login.php" in page.url.lower():
                log(f"❌ Login fallido")
                browser.close()
                return
            
            log(f"✅ Sesión iniciada como {info['nombre']}")
            
            # Ir al reporte
            page.goto(URL_ASISTENCIA, timeout=30000)
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # Obtener todos los equipos del select
            equipos_opts = []
            options = page.query_selector_all("#cbnEquipo option")
            for opt in options:
                val = opt.get_attribute("value")
                text = opt.inner_text().strip()
                if val and "Seleccionar" not in text:
                    equipos_opts.append({"value": val, "text": text})
            
            log(f"Se encontraron {len(equipos_opts)} equipos para scrapear.")
            
            # Iterar por cada equipo
            for eq in equipos_opts:
                log(f"\n--- Procesando {eq['text']} ---")
                try:
                    page.select_option("#cbnEquipo", value=eq["value"])
                    try:
                        page.click("button:has-text('Consultar')", timeout=5000)
                    except:
                        page.click("#invoice_btn", timeout=5000)
                    
                    page.wait_for_load_state("networkidle")
                    time.sleep(3)
                    
                    # Mostrar 400 por página para asegurar que salgan todos
                    try:
                        page.select_option("select[name='example_length']", value="400")
                        time.sleep(2)
                    except:
                        pass
                    
                    # Extraer filas
                    rows = page.query_selector_all("#example tbody tr, table tbody tr")
                    
                    eq_participantes = []
                    for r in rows:
                        cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                        if not cells or len(cells) < 6 or "no data" in cells[0].lower():
                            continue
                            
                        px = {
                            "ficha": cells[0] if len(cells) > 0 else "",
                            "asistencia": cells[1] if len(cells) > 1 else "",
                            "equipo": eq["text"], # forzamos el nombre del equipo
                            "usuario_seguimiento": cells[3] if len(cells) > 3 else "",
                            "identificacion": cells[4] if len(cells) > 4 else "",
                            "apellido": cells[5] if len(cells) > 5 else "",
                            "nombre": cells[6] if len(cells) > 6 else "",
                        }
                        
                        if len(cells) > 7:
                            px["telefono"] = cells[7] if len(cells) > 7 else ""
                        
                        asist = px["asistencia"].upper().strip()
                        if "CONFIRMADO" in asist:
                            px["asistencia"] = "CONFIRMADO"
                        elif "DESERTOR" in asist:
                            px["asistencia"] = "DESERTOR"
                        elif "PENDIENTE" in asist or "ACTUALIZAR" in asist:
                            px["asistencia"] = "PENDIENTE"
                        
                        eq_participantes.append(px)
                    
                    log(f"  > Extraídos {len(eq_participantes)} participantes de {eq['text']}")
                    all_participantes.extend(eq_participantes)
                    
                except Exception as ex:
                    log(f"  ❌ Error en equipo {eq['text']}: {str(ex)}")
                    continue
            
            page.close()
            browser.close()
            
        except Exception as e:
            log(f"❌ Error fatal en scraper: {e}")
            if 'browser' in locals(): browser.close()
            return
            
    log(f"\n=================================================================")
    log(f"✅ EXTRACCIÓN COMPLETADA: {len(all_participantes)} participantes totales.")
    log(f"=================================================================")
    
    if all_participantes:
        actualizar_db_todos(all_participantes)

def actualizar_db_todos(participantes):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    stats = {"confirmados": 0, "desertores": 0, "pendientes": 0, "agregados": 0}
    
    for px in participantes:
        dni = px.get("identificacion", "").strip()
        nombre = px.get("nombre", "").strip()
        apellido = px.get("apellido", "").strip()
        asist = px.get("asistencia", "").upper()
        telefono = re.sub(r'\D', '', px.get("telefono", ""))
        equipo = px.get("equipo", "").strip()
        
        found_id = None
        if dni:
            c.execute("SELECT id FROM participantes WHERE identificacion=?", (dni,))
            r = c.fetchone()
            if r: found_id = r[0]
            else:
                stripped = dni.lstrip('0')
                c.execute("SELECT id FROM participantes WHERE REPLACE(LTRIM(COALESCE(identificacion,''),'0'),' ','') = ?", (stripped,))
                r = c.fetchone()
                if r: found_id = r[0]
        
        if not found_id and telefono and len(telefono) >= 9:
            c.execute("SELECT id FROM participantes WHERE telefono LIKE ?", (f"%{telefono[-9:]}%",))
            r = c.fetchone()
            if r: found_id = r[0]
            
        if not found_id and nombre and apellido:
            c.execute("""SELECT id FROM participantes 
                        WHERE UPPER(COALESCE(nombre,''))=UPPER(?) AND UPPER(COALESCE(apellido,''))=UPPER(?)""", 
                        (nombre, apellido))
            r = c.fetchone()
            if r: found_id = r[0]
            
        estado = 'ACTIVO' if asist == 'CONFIRMADO' else ('DESERTOR' if asist == 'DESERTOR' else 'PENDIENTE')
        c1_val = 'SI' if asist == 'CONFIRMADO' else 'NO'
        
        if not found_id:
            c.execute("""INSERT INTO participantes (nombre, apellido, identificacion, equipo, estado, c1)
                        VALUES (?, ?, ?, ?, ?, ?)""", (nombre, apellido, dni, equipo, estado, c1_val))
            stats["agregados"] += 1
        else:
            c.execute("UPDATE participantes SET c1=?, estado=?, equipo=COALESCE(NULLIF(equipo,''), ?) WHERE id=?", 
                      (c1_val, estado, equipo, found_id))
            
        if asist == 'CONFIRMADO': stats["confirmados"] += 1
        elif asist == 'DESERTOR': stats["desertores"] += 1
        else: stats["pendientes"] += 1

    conn.commit()
    
    log(f"\n=================================================================")
    log(f"  RESULTADO ACTUALIZACIÓN DB (TODOS LOS EQUIPOS)")
    log(f"=================================================================")
    log(f"  ✅ CONFIRMADOS → C1=SI: {stats['confirmados']}")
    log(f"  ❌ DESERTORES: {stats['desertores']}")
    log(f"  ⏳ PENDIENTES: {stats['pendientes']}")
    log(f"  🆕 Nuevos agregados: {stats['agregados']}")
    
    total = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
    total_c1_si = c.execute("SELECT COUNT(*) FROM participantes WHERE c1='SI'").fetchone()[0]
    log(f"\n  Total en DB: {total}")
    log(f"  Total con C1=SI histórico: {total_c1_si}")
    log(f"=================================================================")
    
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    df_out = pd.DataFrame(participantes)
    csv_path = os.path.join(BASE_DIR, f"asistencia_real_todos_{ts}.csv")
    df_out.to_csv(csv_path, index=False, encoding='utf-8')
    log(f"📁 CSV respaldo guardado en: {csv_path}")
    
    conn.close()

if __name__ == "__main__":
    extraer_y_actualizar_todos()
