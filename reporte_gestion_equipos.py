import os
import sys
import time
import re
import json
import argparse
import pandas as pd
from playwright.sync_api import sync_playwright

# Asegurar codificación UTF-8 en consola
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
URL_REPORTE = "https://crearpslglobal.com/admin/reporte_gestionusuario.php"

# Credenciales de acceso
CUENTAS = {
    "dmoscoso": {"pass": "crear2025", "nombre": "Diana Moscoso"},
    "jmarin": {"pass": "crear2025", "nombre": "Joyce Marín"}
}

# Equipos a procesar
EQUIPOS = [28, 27, 26, 25, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14]

# Ruta de salida del reporte Excel
OUTPUT_EXCEL = r"C:\Users\josem\Downloads\Reporte_Gestion_Usuario.xlsx"

def clean_phone(p):
    if not p:
        return ""
    p_clean = re.sub(r'\D', '', str(p))
    if p_clean.startswith('51') and len(p_clean) > 9:
        return "+" + p_clean
    if len(p_clean) == 9:
        return "+51 " + p_clean
    return p_clean

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def extraer_datos_reporte():
    log("Iniciando proceso de extracción de datos desde el portal IMO...")
    
    # Estructura para almacenar los datos agrupados por equipo
    datos_por_equipo = {eq: [] for eq in EQUIPOS}
    
    with sync_playwright() as p:
        # Ejecutar en modo headless
        browser = p.chromium.launch(headless=True)
        
        for user, info in CUENTAS.items():
            log(f"Iniciando sesión con el usuario: {user} ({info['nombre']})...")
            page = browser.new_page()
            
            try:
                # 1. Login
                page.goto(URL_LOGIN)
                page.fill("input[name='usuario']", user)
                page.fill("input[name='password']", info["pass"])
                page.click("button[name='ingresar']")
                page.wait_for_load_state("networkidle")
                
                url_actual = page.url
                if "login.php" in url_actual.lower():
                    log(f"❌ Error: No se pudo iniciar sesión para {user}. Clave incorrecta.")
                    page.close()
                    continue
                    
                log(f"✅ Sesión iniciada con éxito para {user}")
                
                # 2. Extraer datos para cada equipo
                for eq in EQUIPOS:
                    log(f"  Procesando Equipo {eq}...")
                    page.goto(URL_REPORTE)
                    page.wait_for_load_state("networkidle")
                    
                    # Buscar opción exacta
                    label_buscado = f"EQUIPO {eq} - CICLO_I"
                    page.select_option("#cbnEquipo", label=label_buscado)
                    page.click("#invoice_btn")
                    page.wait_for_load_state("networkidle")
                    time.sleep(2)
                    
                    # Mostrar todas las entradas (200) para evitar paginación
                    try:
                        page.select_option("select[name='example_length']", value="200")
                        time.sleep(1)
                    except:
                        pass
                        
                    # Extraer filas de la tabla principal
                    rows = page.query_selector_all("#example tbody tr")
                    log(f"    Filas encontradas para Equipo {eq}: {len(rows)}")
                    
                    registros_eq = 0
                    for r in rows:
                        cells = [td.inner_text().strip() for td in r.query_selector_all("td")]
                        # Asegurarse de que no sea una fila de "No data"
                        if cells and len(cells) > 8 and "no data" not in cells[0].lower():
                            px_row = {
                                "Coordinador": info["nombre"],
                                "Nombre Equipo": cells[1],
                                "Primera Llamada": cells[2],
                                "Segunda Llamada": cells[3],
                                "Ultima Gestión": cells[4],
                                "Comentario Ultima Gestión": cells[5],
                                "Asistencia": cells[6],
                                "ApellidoCompleto": cells[7],
                                "NombreCompleto": cells[8],
                                "NombrePreferido": cells[9],
                                "TeléfonoMovil": clean_phone(cells[10]),
                                "Teléfono IMO": clean_phone(cells[11]),
                                "Nombre IMO": cells[12],
                                "Equipo IMO": cells[13]
                            }
                            datos_por_equipo[eq].append(px_row)
                            registros_eq += 1
                            
                    log(f"    ✅ {registros_eq} registros agregados de {user} para Equipo {eq}")
                    
            except Exception as e:
                log(f"❌ Error al procesar datos para el usuario {user}: {e}")
            finally:
                page.close()
                
        browser.close()
        
    # 3. Guardar en archivo Excel
    log("Consolidando datos y generando archivo Excel...")
    try:
        # Usar pd.ExcelWriter para guardar múltiples pestañas
        with pd.ExcelWriter(OUTPUT_EXCEL, engine='openpyxl') as writer:
            for eq in EQUIPOS:
                df_eq = pd.DataFrame(datos_por_equipo[eq])
                
                # Si el dataframe está vacío, crear uno con las columnas correspondientes vacías
                if df_eq.empty:
                    df_eq = pd.DataFrame(columns=[
                        "Coordinador", "Nombre Equipo", "Primera Llamada", "Segunda Llamada", 
                        "Ultima Gestión", "Comentario Ultima Gestión", "Asistencia", 
                        "ApellidoCompleto", "NombreCompleto", "NombrePreferido", 
                        "TeléfonoMovil", "Teléfono IMO", "Nombre IMO", "Equipo IMO"
                    ])
                    
                # Guardar en pestaña correspondiente
                sheet_name = str(eq)
                df_eq.to_excel(writer, sheet_name=sheet_name, index=False)
                log(f"💾 Pestaña '{sheet_name}' guardada con {len(df_eq)} filas.")
                
        log(f"🎉 ¡Éxito! Reporte consolidado guardado en: {OUTPUT_EXCEL}")
        
    except Exception as e:
        log(f"❌ Error escribiendo archivo Excel: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scraper IMO reporte de gestión de usuario por equipo.")
    parser.add_argument("--loop", action="store_true", help="Ejecutar en bucle cada 1 hora")
    args = parser.parse_args()
    
    if args.loop:
        log("Iniciando en modo bucle continuo (ejecución cada 1 hora)...")
        # Loop infinito
        while True:
            try:
                extraer_datos_reporte()
            except Exception as ex:
                log(f"Error en ejecución del bucle: {ex}")
            log("Esperando 1 hora hasta la siguiente extracción...")
            time.sleep(1 * 60 * 60) # 1 hora
    else:
        # Ejecutar una vez
        extraer_datos_reporte()
