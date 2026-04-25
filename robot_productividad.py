import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# CONFIGURACIÓN
URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
USER = "jsanchez"
PASS = "crearpsl25"
OUTPUT_FILE = "Productividad_Web.xlsx"

def iniciar_robot():
    print("[ROBOT] Iniciando Robot de Productividad...")
    chrome_options = Options()
    chrome_options.add_argument("--headless") # Ejecutar sin ventana
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 1. Login
        driver.get(URL_LOGIN)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "exampleInputEmail1")))
        
        driver.find_element(By.ID, "exampleInputEmail1").send_keys(USER)
        driver.find_element(By.ID, "exampleInputPassword1").send_keys(PASS)
        driver.find_element(By.CSS_SELECTOR, "button.btn-primary").click()
        
        # Esperar a que cargue la página de reportes
        # Nota: Después del login, puede que necesitemos navegar a la URL del reporte
        URL_REPORTE = "https://crearpslglobal.com/admin/reporte_productividad.php"
        driver.get(URL_REPORTE)
        
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "idsede")))
        print("[OK] Login y navegación exitosa.")

        ccs = {
            "DIANA": "DIANA YESENIA MOSCOSO ROBLES",
            "JOYCE": "JOYCE PAMELA MARÍN SUAREZ",
            "ZULEY": "OTTY ZULEY URTEAGA SILVA"
        }
        
        all_data = []

        for alias, full_name in ccs.items():
            print(f"[DATA] Extrayendo data para: {alias}...")
            
            # Seleccionar Sede LIMA
            sede_select = Select(driver.find_element(By.ID, "idsede"))
            sede_select.select_by_visible_text("LIMA")
            
            # Seleccionar Coordinadora
            cc_select = Select(driver.find_element(By.ID, "IdCoordinador"))
            try:
                cc_select.select_by_visible_text(full_name)
            except:
                print(f"⚠️ No se encontró la opción exacta para {full_name}, intentando búsqueda parcial...")
                for opt in cc_select.options:
                    if alias in opt.text.upper():
                        cc_select.select_by_visible_text(opt.text)
                        break
            
            # Consultar
            driver.find_element(By.ID, "invoice_btn").click()
            time.sleep(3) # Esperar a que la tabla cargue (AJAX)
            
            # Poner "All" en entradas
            try:
                length_select = Select(driver.find_element(By.NAME, "tablaProductividad_length"))
                length_select.select_by_value("-1")
                time.sleep(2)
            except: pass
            
            # Capturar Tabla
            html_table = driver.find_element(By.ID, "tablaProductividad").get_attribute('outerHTML')
            import io
            df_list = pd.read_html(io.StringIO(html_table))
            if df_list:
                df_cc = df_list[0]
                df_cc['CC_Reportada'] = alias
                all_data.append(df_cc)
                print(f"   - {len(df_cc)} registros capturados.")

        if all_data:
            df_final = pd.concat(all_data, ignore_index=True)
            df_final.to_excel(OUTPUT_FILE, index=False)
            print(f"[SUCCESS] Proceso completado. Archivo guardado: {OUTPUT_FILE}")
            
            # Subir a la nube
            try:
                from sync_cloud import sincronizar_productividad_a_cloud
                sincronizar_productividad_a_cloud(OUTPUT_FILE)
            except Exception as se:
                print(f"[!] Error al subir a Google Sheets: {se}")
                
        else:
            print("[!] No se capturó ninguna información de productividad.")

        # ========================================================
        # 2. EXTRAER ASIGNACIONES (LISTADO OFICIAL)
        # ========================================================
        print("\n[ROBOT] Navegando a listar_asignaciones.php...")
        driver.get("https://crearpslglobal.com/admin/listar_asignaciones.php")
        time.sleep(4)
        
        # Poner "All" en entradas si existe
        try:
            length_select = Select(driver.find_element(By.NAME, "tabla_length"))
            length_select.select_by_value("-1")
            time.sleep(2)
        except:
            pass
            
        # Capturar la tabla que haya en la pantalla
        try:
            html_asig = driver.find_element(By.ID, "tabla").get_attribute('outerHTML')
            import io
            df_asig_list = pd.read_html(io.StringIO(html_asig))
            if df_asig_list:
                df_asig = df_asig_list[0]
                df_asig.to_excel("Asignaciones_Web.xlsx", index=False)
                print(f"[SUCCESS] Asignaciones capturadas: {len(df_asig)} registros en Asignaciones_Web.xlsx")
                
                # Sincronizar asignaciones
                from sync_cloud import sincronizar_asignaciones_a_cloud
                sincronizar_asignaciones_a_cloud("Asignaciones_Web.xlsx")
        except Exception as ea:
            print(f"⚠️ No se pudo extraer la tabla de asignaciones: {ea}")

    except Exception as e:
        import traceback
        print(f"[ERROR] Error en el robot: {e}")
        traceback.print_exc()
    finally:
        driver.quit()

if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    iniciar_robot()
