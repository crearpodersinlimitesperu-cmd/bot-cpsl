import getpass
import time
from playwright.sync_api import sync_playwright

# --- CONFIGURACIÓN ---
URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
URL_REPORTE = "https://crearpslglobal.com/admin/reporte_gestionusuario.php"

# Usuarios configurados
USUARIOS = ["dmoscoso", "jmarin"]

# Equipos a procesar: del 14 al 25 (en orden ascendente, de más antiguo a más reciente)
EQUIPOS = list(range(14, 26))

# Datos de la gestión
TIPO_GESTION = "NO LE INTERESA"
NUMERO_LLAMADA = "PRIMERA"
COMENTARIO = "SE LES ENVIÓ MENSAJE POR WHATSAPP, SMS Y CORREO ELECTRÓNICO. NO ASISTEN NI CONFIRMAN ASISTENCIA."

def ejecutar_automatizacion():
    # Solicita la contraseña de forma segura en la consola antes de iniciar el navegador
    print("--- INGRESO DE CREDENCIALES SEGURAS ---")
    import sys
    if len(sys.argv) > 1:
        contrasena_comun = sys.argv[1]
    else:
        try:
            contrasena_comun = getpass.getpass("Introduce la contraseña para los usuarios: ")
            if not contrasena_comun:
                contrasena_comun = "crear2025"
        except:
            contrasena_comun = "crear2025"

    # Creamos el diccionario de cuentas con la contraseña ingresada
    cuentas = [{"usuario": u, "contrasena": contrasena_comun} for u in USUARIOS]

    with sync_playwright() as p:
        # Lanzar el navegador visible para monitorear el proceso
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        for cuenta in cuentas:
            print(f"\n=== Iniciando sesión con el usuario: {cuenta['usuario']} ===")
            
            try:
                page.goto(URL_LOGIN)
                page.wait_for_load_state("networkidle")
                
                # Rellenar formulario de login con selectores reales obtenidos
                page.fill("input[name='usuario']", cuenta["usuario"])
                page.fill("input[name='password']", cuenta["contrasena"])
                page.click("button[name='ingresar']")
                
                page.wait_for_load_state("networkidle")
                time.sleep(2) # Espera adicional de 2 segundos para redirecciones del lado del cliente
                
                url_actual = page.url
                print(f"URL tras intentar login: {url_actual}")
                
                if "login.php" in url_actual:
                    print("⚠️ ALERTA: No se logró salir de la página de inicio de sesión.")
                    print("Es posible que la contraseña ('crear2025') o el usuario sean incorrectos.")
                    # Buscar mensajes de error visibles en la página
                    texto_pagina = page.locator("body").inner_text()
                    lineas_error = []
                    for linea in texto_pagina.split("\n"):
                        l_upper = linea.upper()
                        if any(k in l_upper for k in ["ERROR", "INCORRECTO", "VALIDAR", "CLAVE", "USUARIO", "CONTRASEÑA"]):
                            lineas_error.append(linea.strip())
                    if lineas_error:
                        print("Mensajes de error detectados en pantalla:")
                        for err in set(lineas_error):
                            print(f"  -> {err}")
                    else:
                        print("No se encontraron textos explícitos de error, pero la sesión no inició.")
                    continue
                else:
                    print("Inicio de sesión completado con éxito (redirigido correctamente).")
            except Exception as e:
                print(f"Error al iniciar sesión para {cuenta['usuario']}: {e}")
                continue

            # Función interna para ayudar al usuario a ver qué botones y filtros existen realmente si falla
            def depurar_elementos(p):
                try:
                    print("\n--- DEPURACIÓN: ELEMENTOS ENCONTRADOS EN LA PÁGINA ACTUAL ---")
                    selects = p.query_selector_all("select")
                    print(f"Desplegables (select) ({len(selects)}):")
                    for s in selects:
                        print(f"  - <select id='{s.get_attribute('id') or ''}' name='{s.get_attribute('name') or ''}' class='{s.get_attribute('class') or ''}'>")
                    
                    buttons = p.query_selector_all("button, input[type='submit'], input[type='button']")
                    print(f"Botones ({len(buttons)}):")
                    for b in buttons:
                        tag = b.evaluate("el => el.tagName.toLowerCase()")
                        print(f"  - <{tag} id='{b.get_attribute('id') or ''}' class='{b.get_attribute('class') or ''}' value='{b.get_attribute('value') or ''}'> Texto: '{b.inner_text().strip()}'")
                    
                    links = p.query_selector_all("a")
                    print(f"Enlaces estilo botón ({len(links)}):")
                    for l in links:
                        cls = l.get_attribute('class') or ''
                        txt = l.inner_text().strip()
                        if "btn" in cls or txt:
                            print(f"  - <a id='{l.get_attribute('id') or ''}' class='{cls}'> Texto: '{txt}'")
                    print("------------------------------------------------------------\n")
                except Exception as ex:
                    print(f"No se pudo depurar la página: {ex}")

            # Lista para guardar los registros exitosos de esta ejecución
            gestiones_realizadas = []

            # Selectores que el script aprenderá en el primer registro para ir rápido en los siguientes
            selectores_aprendidos = {
                "select_tipo": None,
                "select_llamada": None,
                "txt_comentario": None,
                "btn_guardar": None
            }

            # Procesar cada equipo
            for equipo in EQUIPOS:
                print(f"\nProcesando Equipo {equipo}...")
                
                indice_participante = 0
                ultimo_total_participantes = None
                
                while True:
                    try:
                        page.goto(URL_REPORTE)
                        page.wait_for_load_state("networkidle")
                        
                        # Seleccionar equipo y filtrar con los selectores reales encontrados (cbnEquipo y invoice_btn)
                        try:
                            # Primero buscamos la opción del desplegable que coincida con el número del equipo
                            opciones_select = page.locator("#cbnEquipo option")
                            valor_encontrado = None
                            for i in range(opciones_select.count()):
                                opt = opciones_select.nth(i)
                                val = opt.get_attribute("value") or ""
                                txt = opt.inner_text() or ""
                                if str(equipo) in val or str(equipo) in txt:
                                    valor_encontrado = val
                                    break
                            
                            if valor_encontrado is not None:
                                page.select_option("#cbnEquipo", value=valor_encontrado)
                            else:
                                page.select_option("#cbnEquipo", value=str(equipo))
                            
                            page.click("#invoice_btn")
                            page.wait_for_load_state("networkidle")
                            time.sleep(1.5) # Esperar renderizado
                        except Exception as e_filtro:
                            print(f"Error al aplicar el filtro de equipo {equipo}: {e_filtro}")
                            depurar_elementos(page)
                            break
                        
                        # Obtener los participantes usando el localizador de texto real
                        participantes = page.locator("a:has-text('Registrar Gestión')").all()
                        total_actual = len(participantes)
                        
                        if total_actual == 0:
                            print(f"No hay participantes (PX) pendientes para el Equipo {equipo}.")
                            break
                        
                        # Verificar si el total disminuyó (el participante registrado desapareció de la lista)
                        if ultimo_total_participantes is not None:
                            if total_actual < ultimo_total_participantes:
                                # El participante anterior ya no está en la tabla, el siguiente está en la misma posición index
                                pass
                            else:
                                # Sigue igual, avanzamos al siguiente participante
                                indice_participante += 1
                        
                        # Si el índice supera la lista, terminamos con este equipo
                        if indice_participante >= total_actual:
                            print(f"Se procesaron todos los {total_actual} participantes del Equipo {equipo}.")
                            break
                            
                        print(f"Abriendo registro de gestión para el participante {indice_participante + 1} de {total_actual}...")
                        px = participantes[indice_participante]
                        
                        # Intentar extraer datos de la fila del participante antes de hacer clic
                        nombre_px = f"Participante_{indice_participante + 1}"
                        try:
                            fila = px.locator("xpath=./ancestor::tr")
                            celdas = fila.locator("td").all_inner_texts()
                            if len(celdas) > 2:
                                nombre_px = " - ".join([c.strip() for c in celdas[:4] if c.strip()])
                        except:
                            pass
                        
                        # Hacer clic para abrir el formulario
                        px.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(1)
                        
                        # Intentar leer el nombre exacto del formulario si la celda de la tabla falló
                        try:
                            input_nombre = page.query_selector("input[type='text']")
                            if input_nombre:
                                valor_input = input_nombre.evaluate("el => el.value")
                                if valor_input and len(valor_input) > 3:
                                    nombre_px = valor_input.strip()
                        except:
                            pass
                        
                        # Registrar gestión con auto-detección y aprendizaje veloz de selectores
                        try:
                            select_tipo = None
                            select_llamada = None
                            txt_comentario = None
                            btn_guardar = None
                            
                            # 1. Intentar usar selectores aprendidos previamente
                            usando_aprendidos = False
                            if selectores_aprendidos["select_tipo"]:
                                try:
                                    s_tipo = page.locator(selectores_aprendidos["select_tipo"])
                                    s_llamada = page.locator(selectores_aprendidos["select_llamada"])
                                    t_com = page.locator(selectores_aprendidos["txt_comentario"])
                                    b_guar = page.locator(selectores_aprendidos["btn_guardar"])
                                    
                                    if s_tipo.count() > 0 and s_llamada.count() > 0 and t_com.count() > 0 and b_guar.count() > 0:
                                        select_tipo = s_tipo
                                        select_llamada = s_llamada
                                        txt_comentario = t_com
                                        btn_guardar = b_guar
                                        usando_aprendidos = True
                                except:
                                    pass
                            
                            # 2. Si no se han aprendido o fallaron, analizamos y los guardamos
                            if not usando_aprendidos:
                                selects = page.query_selector_all("select")
                                s_tipo_obj = None
                                s_llamada_obj = None
                                
                                for s in selects:
                                    id_val = (s.get_attribute("id") or "").lower()
                                    name_val = (s.get_attribute("name") or "").lower()
                                    if "tipo" in id_val or "tipo" in name_val or "gestion" in id_val or "gestion" in name_val:
                                        s_tipo_obj = s
                                    elif "llamada" in id_val or "llamada" in name_val or "num" in id_val or "num" in name_val:
                                        s_llamada_obj = s
                                
                                if not s_tipo_obj and len(selects) >= 2:
                                    s_tipo_obj = selects[0]
                                    s_llamada_obj = selects[1]
                                
                                t_com_obj = page.query_selector("textarea")
                                
                                b_guar_obj = None
                                elementos_potenciales = page.query_selector_all("button, input[type='submit'], input[type='button'], a")
                                for el in elementos_potenciales:
                                    txt = el.inner_text().strip().upper()
                                    val = (el.get_attribute("value") or "").upper()
                                    id_el = (el.get_attribute("id") or "").upper()
                                    
                                    if "REGISTRAR" in txt or "REGISTRAR" in val or "REGISTRAR" in id_el or "GUARDAR" in txt or "GUARDAR" in val:
                                        if "CANCELAR" not in txt and "CANCELAR" not in val:
                                            if el.is_visible():
                                                b_guar_obj = el
                                                break
                                
                                if s_tipo_obj and s_llamada_obj and t_com_obj and b_guar_obj:
                                    # Generar selectores dinámicos e instruir aprendizaje
                                    def gen_sel(el):
                                        tag = el.evaluate("el => el.tagName.toLowerCase()")
                                        i = el.get_attribute("id")
                                        if i: return f"{tag}#{i}"
                                        n = el.get_attribute("name")
                                        if n: return f"{tag}[name='{n}']"
                                        txt = el.inner_text().strip().replace("'", "\\'")
                                        if txt: return f"{tag}:has-text('{txt}')"
                                        return tag
                                        
                                    selectores_aprendidos["select_tipo"] = gen_sel(s_tipo_obj)
                                    selectores_aprendidos["select_llamada"] = gen_sel(s_llamada_obj)
                                    selectores_aprendidos["txt_comentario"] = gen_sel(t_com_obj)
                                    selectores_aprendidos["btn_guardar"] = gen_sel(b_guar_obj)
                                    
                                    select_tipo = page.locator(selectores_aprendidos["select_tipo"])
                                    select_llamada = page.locator(selectores_aprendidos["select_llamada"])
                                    txt_comentario = page.locator(selectores_aprendidos["txt_comentario"])
                                    btn_guardar = page.locator(selectores_aprendidos["btn_guardar"])
                                    print(f"🤖 Selectores aprendidos para navegación rápida: {selectores_aprendidos}")
                                else:
                                    raise Exception("No se pudieron detectar los elementos del formulario.")
                            
                            # 3. Rellenar y enviar
                            opciones_tipo = select_tipo.locator("option").all()
                            val_tipo = None
                            for opt in opciones_tipo:
                                t_opt = opt.inner_text().upper()
                                if TIPO_GESTION in t_opt or "NO INTERESA" in t_opt:
                                    val_tipo = opt.get_attribute("value")
                                    break
                            if val_tipo:
                                select_tipo.select_option(value=val_tipo)
                            else:
                                select_tipo.select_option(label=TIPO_GESTION)

                            opciones_llamada = select_llamada.locator("option").all()
                            val_llamada = None
                            for opt in opciones_llamada:
                                t_opt = opt.inner_text().upper()
                                if NUMERO_LLAMADA in t_opt or "PRIMERA" in t_opt:
                                    val_llamada = opt.get_attribute("value")
                                    break
                            if val_llamada:
                                select_llamada.select_option(value=val_llamada)
                            else:
                                select_llamada.select_option(label=NUMERO_LLAMADA)
                            
                            txt_comentario.fill(COMENTARIO)
                            btn_guardar.click()
                            page.wait_for_load_state("networkidle")
                            
                            # Guardar registro para reporte
                            registro_exitoso = {
                                "coordinador": cuenta["usuario"],
                                "equipo": equipo,
                                "participante": nombre_px,
                                "fecha": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            gestiones_realizadas.append(registro_exitoso)
                            print(f"  [ÉXITO] Gestión registrada: {nombre_px}")
                            
                        except Exception as e_form:
                            print(f"  Error en el formulario de gestión: {e_form}")
                            depurar_elementos(page)
                            raise e_form
                        
                        ultimo_total_participantes = total_actual
                        time.sleep(0.5)
                        
                    except Exception as e_px:
                        print(f"  Error registrando gestión en índice {indice_participante}: {e_px}")
                        indice_participante += 1
                        ultimo_total_participantes = None


            # Cerrar sesión con el botón real (a.btn-warning con texto 'Salir')
            try:
                page.click("a.btn-warning")
                page.wait_for_load_state("networkidle")
                print("Sesión cerrada correctamente.")
            except Exception as e_logout:
                print(f"No se pudo cerrar sesión de forma automática: {e_logout}")

        print("\n=== Proceso finalizado para todas las cuentas ===")
        browser.close()

        # Escribir reporte final
        ruta_reporte = "C:\\Users\\josem\\Downloads\\reporte_no_interesados.md"
        try:
            with open(ruta_reporte, "w", encoding="utf-8") as f:
                f.write("# Reporte de Participantes (PX) Puestos en 'No Interesados'\n\n")
                f.write(f"**Fecha y Hora de Ejecución:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("| Coordinador | Equipo | Participante / DNI / Información | Fecha de Registro |\n")
                f.write("| --- | --- | --- | --- |\n")
                if gestiones_realizadas:
                    for r in gestiones_realizadas:
                        f.write(f"| {r['coordinador']} | {r['equipo']} | {r['participante']} | {r['fecha']} |\n")
                else:
                    f.write("| - | - | No se registraron gestiones en esta ejecución | - |\n")
            print(f"\n[REPORTE GENERADO] Se guardó el archivo en: {ruta_reporte}")
        except Exception as e_rep:
            print(f"No se pudo escribir el reporte: {e_rep}")

if __name__ == "__main__":
    ejecutar_automatizacion()