"""
AGENTE AUTÓNOMO DE SINCRONIZACIÓN Y MAILING - CREAR PODER SIN LÍMITES
=====================================================================
Monitorea archivos de OneDrive (Excel de precios, Mapeo operativo, Manuales PDF)
y extrae la data en tiempo real. Sincroniza participantes desde Excel local y
de forma dinámica mediante Web Scraping (Selenium) de crearpslglobal.com cada 24h.
Opera silenciosamente en segundo plano, consumiendo <1% de CPU cuando está inactivo.
"""
import os
import sys
import time
import json
import sqlite3
import re
import hashlib
import io
import logging
from datetime import datetime
import pandas as pd
import pypdf
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

sys.stdout.reconfigure(encoding='utf-8')

# --- CONFIGURACIÓN DE RUTAS ---
BASE_DIR = r"C:\Users\josem\Downloads\bot-cpsl-review"
DB_PATH = os.path.join(BASE_DIR, "torre_control.db")
METADATA_PATH = os.path.join(BASE_DIR, "agente_metadata.json")
LOG_PATH = os.path.join(BASE_DIR, "agente_sincronizador.log")

# Rutas de archivos de entrada
ONEDRIVE_DIR = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA"
EXCEL_PRECIOS = os.path.join(ONEDRIVE_DIR, "CREAR LIMA", "PRECIOS CREAR LIMA 2025.xlsx")
EXCEL_MAPEO = os.path.join(ONEDRIVE_DIR, "GERENCIA LIMA", "Mapeo Operativo Global_.xlsx")
DIR_MANUALES = os.path.join(ONEDRIVE_DIR, "MANUALES")
EXCEL_GRADUADOS = os.path.join(ONEDRIVE_DIR, "CREAR LIMA", "GRADUADOS LIMA.xlsx")

EXCEL_EQUIPOS = r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\reporte_equipos (1).xlsx"

# Web Scraping
URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
TARGET_URL = "https://crearpslglobal.com/admin/datosparticipante.php?mostrar=todos"
USER = "jsanchez"
PASS = "crearpsl25"

# Mapeo de Coordinadoras
COORDINATORS_MAP = {
    "dmoscoso": {"cc_asignada": "DIANA", "cc_nombre": "Diana Moscoso", "cc_tel": "51912379744"},
    "diana": {"cc_asignada": "DIANA", "cc_nombre": "Diana Moscoso", "cc_tel": "51912379744"},
    "jmarin": {"cc_asignada": "JOYCE", "cc_nombre": "Joyce Marín", "cc_tel": "51991765740"},
    "joyce": {"cc_asignada": "JOYCE", "cc_nombre": "Joyce Marín", "cc_tel": "51991765740"},
    "lvalencia": {"cc_asignada": "LVALENCIA", "cc_nombre": "Linid Valencia", "cc_tel": "51912379686"},
    "zurteaga": {"cc_asignada": "ZULEY", "cc_nombre": "Zuley Urteaga", "cc_tel": "51933599864"}
}

# --- CONFIGURAR LOGGING ---
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger("agente_sincronizador")

# Fallback logs en consola por si se corre de forma interactiva
c_handler = logging.StreamHandler()
c_handler.setLevel(logging.INFO)
c_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(c_handler)

def normalizar_dni(v) -> str:
    if pd.isna(v) or not v:
        return ""
    return "".join(c for c in str(v).strip() if c.isdigit())[:8]

def normalizar_telefono(v) -> str:
    if pd.isna(v) or not v:
        return ""
    digitos = "".join(c for c in str(v).strip() if c.isdigit())
    if len(digitos) == 9:
        return f"51{digitos}"
    if len(digitos) == 11 and digitos.startswith("51"):
        return digitos
    return digitos

def normalizar_nombre(v) -> str:
    if pd.isna(v) or not v:
        return ""
    return " ".join(str(v).strip().upper().split())

def load_metadata() -> dict:
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Error al cargar metadata: {e}")
    return {
        "precios_mtime": 0.0,
        "mapeo_mtime": 0.0,
        "reporte_equipos_mtime": 0.0,
        "manual_gerente_mtime": 0.0,
        "manual_coord_c1c2_mtime": 0.0,
        "manual_coord_mj_mtime": 0.0,
        "manuales_operativos_mtime": 0.0,
        "graduados_mtime": 0.0,
        "last_web_scrape": 0.0
    }

def save_metadata(meta: dict):
    try:
        with open(METADATA_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log.error(f"Error al guardar metadata: {e}")

# --- PARSERS DE DOCUMENTOS ---

def procesar_precios():
    """Parsea el Excel de precios e inserta en la tabla config_precios."""
    log.info("Procesando Excel de precios...")
    try:
        df = pd.read_excel(EXCEL_PRECIOS, sheet_name='PRECIOS LIMA 2025')
        df.columns = [str(c).strip() for c in df.columns]
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        c = conn.cursor()
        
        parsed_count = 0
        for index, row in df.iterrows():
            concepto = row.iloc[0]
            notas = row.iloc[1]
            usd = row.iloc[2]
            pen = row.iloc[3]
            
            if pd.isna(concepto) or str(concepto).strip().upper() in ["CONCEPTO", "INVERSIÓN ENTRENAMIENTOS CREAR LIMA 2025"]:
                continue
                
            concepto_str = str(concepto).strip()
            notas_str = str(notas).strip() if not pd.isna(notas) else ""
            usd_val = float(usd) if not pd.isna(usd) else None
            pen_val = float(pen) if not pd.isna(pen) else None
            
            c.execute("""
                INSERT OR REPLACE INTO config_precios (concepto, soles, dolares, notas, fecha_actualizacion)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (concepto_str, pen_val, usd_val, notas_str))
            parsed_count += 1
            
        conn.commit()
        conn.close()
        log.info(f"Excel de precios sincronizado con éxito. {parsed_count} registros guardados.")
    except Exception as e:
        log.error(f"Error procesando precios: {e}")

def parse_pdf_manual(path) -> dict:
    """Parsea el manual de PDF extrayendo secciones principales."""
    reader = pypdf.PdfReader(path)
    full_text = ""
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            full_text += txt + "\n"
            
    lines = full_text.split('\n')
    sections = {}
    current_section = "GENERAL"
    section_text = []
    
    headings = [
        "PERFIL DEL CARGO",
        "MANUAL DE FUNCIONES",
        "RESPONSABILIDADES DIARIAS",
        "HORARIOS Y JORNADAS",
        "JORNADAS LABORALES",
        "SISTEMA DE INDICADORES",
        "KPI",
        "ESTRUCTURA DE JORNADAS",
        "GLOSARIO DE TÉRMINOS",
        "PROTOCOLOS DE SEGURIDAD"
    ]
    
    for line in lines:
        cleaned_line = line.strip().upper()
        is_heading = False
        for h in headings:
            if h in cleaned_line and len(cleaned_line) < 100:
                is_heading = True
                new_section = h
                break
        
        if is_heading:
            if section_text:
                sections[current_section] = "\n".join(section_text).strip()
            current_section = new_section
            section_text = [line]
        else:
            section_text.append(line)
            
    if section_text:
        sections[current_section] = "\n".join(section_text).strip()
        
    return sections

def procesar_manuales():
    """Parsea todos los PDFs e inyecta reglas estructuradas en config_manuales."""
    log.info("Procesando manuales de PDF...")
    manuals_map = {
        "GERENTE MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES.pdf": "Gerente Sede",
        "COORDINADOR C1 y C2 MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES1.pdf": "Coordinador C1 y C2",
        "COORDINADOR DE MAESTRÍA MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES2.pdf": "Coordinador de Maestría",
        "MANUALES OPERATIVOS INTEGRALES.pdf": "Manual Operativo Global"
    }
    
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        c = conn.cursor()
        
        for filename, rol in manuals_map.items():
            path = os.path.join(DIR_MANUALES, filename)
            if not os.path.exists(path):
                log.warning(f"Manual no encontrado: {path}")
                continue
                
            sections = parse_pdf_manual(path)
            sections_json = json.dumps(sections, ensure_ascii=False)
            
            c.execute("""
                INSERT OR REPLACE INTO config_manuales (manual_nombre, rol, reglas_extraidas, fecha_actualizacion)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (filename, rol, sections_json))
            
        conn.commit()
        conn.close()
        log.info("PDF Manuals procesados y sincronizados con éxito.")
    except Exception as e:
        log.error(f"Error procesando manuales PDF: {e}")

# --- ESTRATEGIA DE SINCRONIZACIÓN Y UPSERT ---

def sincronizar_participante(px_data: dict, c) -> tuple:
    """
    Sincroniza un participante aplicando validaciones de consistencia y deduplicación.
    Retorna (insertado, actualizado) como booleans.
    """
    dni = normalizar_dni(px_data.get('identificacion'))
    tel = normalizar_telefono(px_data.get('telefono'))
    nombre = normalizar_nombre(px_data.get('nombre'))
    apellido = normalizar_nombre(px_data.get('apellido'))
    
    if not nombre and not tel and not dni:
        return False, False
        
    # Estrategia de búsqueda multidimensional
    existing = None
    
    # 1. Búsqueda por DNI
    if dni:
        c.execute("SELECT * FROM participantes WHERE identificacion = ?", (dni,))
        existing = c.fetchone()
        
    # 2. Búsqueda por Teléfono (los últimos 9 dígitos) con validación de similitud de nombres
    if not existing and tel:
        c.execute("SELECT * FROM participantes WHERE telefono LIKE ?", (f"%{tel[-9:]}%",))
        candidates = c.fetchall()
        if candidates:
            from rapidfuzz import fuzz
            target_full = f"{nombre} {apellido}".strip()
            similar_candidates = []
            for cand in candidates:
                if hasattr(cand, 'keys'):
                    cand_nom = cand['nombre']
                    cand_ape = cand['apellido']
                else:
                    cand_nom = cand[1]
                    cand_ape = cand[2]
                cand_full = f"{cand_nom} {cand_ape}".strip()
                sim = fuzz.token_set_ratio(target_full, cand_full)
                if sim >= 80:
                    similar_candidates.append((sim, cand))
            if similar_candidates:
                similar_candidates.sort(key=lambda x: x[0], reverse=True)
                existing = similar_candidates[0][1]
        
    # 3. Búsqueda por Nombre y Apellido exactos
    if not existing and nombre and apellido:
        c.execute("SELECT * FROM participantes WHERE nombre = ? AND apellido = ?", (nombre, apellido))
        existing = c.fetchone()
        
    if existing:
        px_id = existing['id']
        updates = {}
        
        # Copiar datos vacíos
        if not existing['identificacion'] and dni:
            updates['identificacion'] = dni
        
        # Normalizar o completar teléfono
        db_tel = existing['telefono'] if existing['telefono'] else ""
        if not db_tel and tel:
            updates['telefono'] = tel
            
        # Correo
        db_email = existing['email'] if existing['email'] else ""
        src_email = px_data.get('email')
        if not db_email and src_email and not pd.isna(src_email):
            updates['email'] = src_email.strip()
            
        # Equipo
        db_eq = existing['equipo'] if existing['equipo'] else ""
        src_eq = px_data.get('equipo')
        if not db_eq and src_eq and not pd.isna(src_eq):
            updates['equipo'] = str(src_eq).strip()
            
        # Asistencias C1, C2, Maestría
        # Si origen dice 'SI' y destino dice 'NO', actualizar
        for key in ['c1', 'c2', 'maestria']:
            db_val = existing[key] if existing[key] else 'NO'
            src_val = px_data.get(key)
            if src_val == 'SI' and db_val != 'SI':
                updates[key] = 'SI'
                
        # Estado
        db_est = existing['estado'] if existing['estado'] else ""
        src_est = px_data.get('estado')
        if src_est and src_est != db_est and not pd.isna(src_est):
            # Salvaguarda: no degradar GRADUADO_COMPLETO a ACTIVO/PENDIENTE desde el scrape web/local
            if db_est == 'GRADUADO_COMPLETO' and src_est.strip().upper() in ['ACTIVO', 'PENDIENTE']:
                log.info(f"Evitando degradar estado de participante ID {px_id} de GRADUADO_COMPLETO a {src_est.strip().upper()}")
            else:
                updates['estado'] = src_est.strip().upper()
            
        # Coordinadora asignada
        db_cc = existing['cc_nombre'] if existing['cc_nombre'] else ""
        src_cc_code = px_data.get('cc_code')
        if src_cc_code and not pd.isna(src_cc_code):
            src_cc_str = str(src_cc_code).strip().lower()
            if src_cc_str in COORDINATORS_MAP:
                cc_info = COORDINATORS_MAP[src_cc_str]
                if db_cc != cc_info['cc_nombre']:
                    updates['cc_asignada'] = cc_info['cc_asignada']
                    updates['cc_nombre'] = cc_info['cc_nombre']
                    updates['cc_tel'] = cc_info['cc_tel']
                
        # Observaciones
        db_obs = existing['observaciones'] if existing['observaciones'] else ""
        src_obs = px_data.get('observaciones')
        if src_obs and src_obs != db_obs and not pd.isna(src_obs):
            updates['observaciones'] = f"{db_obs} | {src_obs}".strip(" | ") if db_obs else src_obs
            
        if updates:
            set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
            params = list(updates.values()) + [px_id]
            c.execute(f"""
                UPDATE participantes 
                SET {set_clause}, fecha_actualizacion = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, params)
            return False, True
            
        return False, False
    else:
        # Insertar nuevo participante
        # Obtener mapeo de coordinadora si existe
        cc_cols = {}
        src_cc_code = px_data.get('cc_code')
        if src_cc_code and not pd.isna(src_cc_code):
            src_cc_str = str(src_cc_code).strip().lower()
            if src_cc_str in COORDINATORS_MAP:
                cc_cols = COORDINATORS_MAP[src_cc_str]
            
        insert_data = {
            'nombre': nombre,
            'apellido': apellido,
            'identificacion': dni,
            'telefono': tel,
            'email': px_data.get('email') if not pd.isna(px_data.get('email')) else None,
            'equipo': str(px_data.get('equipo')).strip() if not pd.isna(px_data.get('equipo')) else None,
            'imo': px_data.get('imo') if not pd.isna(px_data.get('imo')) else None,
            'tel_imo': normalizar_telefono(px_data.get('tel_imo')),
            'c1': px_data.get('c1', 'NO'),
            'c2': px_data.get('c2', 'NO'),
            'maestria': px_data.get('maestria', 'NO'),
            'tipo': px_data.get('tipo', 'NUEVO'),
            'estado': px_data.get('estado', 'ACTIVO'),
            'observaciones': px_data.get('observaciones'),
            'es_pendiente_real': px_data.get('es_pendiente_real', 'NO'),
            'tiene_cambio_cupo': px_data.get('tiene_cambio_cupo', 'NO')
        }
        
        insert_data.update(cc_cols)
        
        # Eliminar llaves vacías
        insert_data = {k: v for k, v in insert_data.items() if v is not None}
        
        cols = ", ".join(insert_data.keys())
        placeholders = ", ".join(["?" for _ in insert_data.keys()])
        vals = list(insert_data.values())
        
        c.execute(f"""
            INSERT INTO participantes ({cols}, fecha_registro, fecha_actualizacion)
            VALUES ({placeholders}, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, vals)
        return True, False

# --- PROCESADORES DE FUENTES DE DATOS ---

def sincronizar_excel_equipos():
    """Lee el Excel local de equipos y sincroniza los participantes con la DB."""
    log.info(f"Sincronizando participantes desde Excel local: {EXCEL_EQUIPOS}...")
    if not os.path.exists(EXCEL_EQUIPOS):
        log.error(f"Archivo Excel de equipos no encontrado: {EXCEL_EQUIPOS}")
        return
        
    try:
        xl = pd.ExcelFile(EXCEL_EQUIPOS)
        sheet = 'Equipos' if 'Equipos' in xl.sheet_names else xl.sheet_names[0]
        df = xl.parse(sheet)
        
        # Normalizar nombres de columnas a mayúsculas y quitar espacios
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        col_map = {
            'IDENTIFICACIÓN': 'identificacion',
            'NOMBRECOMPLETO': 'nombre',
            'APELLIDOCOMPLETO': 'apellido',
            'TELEFONOMOVIL': 'telefono',
            'COASISTENCIA': 'c1',
            'ASISTENCIA': 'c1',
            'ASISTENCIAC2': 'c2',
            'TIPOBASE': 'tipo',
            'COREGISTRO': 'fecha_registro',
            'NOMBREIMO': 'imo',
            'TELEFONOIMO': 'tel_imo',
            'USUARIOSEGUIMIENTO': 'cc_code',
            'CORREO': 'email',
            'NOMBREEQUIPO': 'equipo'
        }
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        inserted = 0
        updated = 0
        total_rows = 0
        
        for _, row in df.iterrows():
            px_data = {}
            for col_src, key in col_map.items():
                # Buscar columna correspondiente
                col_found = next((cf for cf in df.columns if col_src in cf), None)
                if col_found:
                    px_data[key] = row[col_found]
            
            # Mapeos específicos de valores
            # Asistencia C1
            asist_c1 = px_data.get('c1')
            px_data['c1'] = 'SI' if str(asist_c1).strip().upper() in ['CONFIRMADO', 'SI', 'ASISTIÓ', 'ASISTIO'] else 'NO'
            # Asistencia C2
            asist_c2 = px_data.get('c2')
            px_data['c2'] = 'SI' if str(asist_c2).strip().upper() in ['CONFIRMADO', 'SI', 'ASISTIÓ', 'ASISTIO'] else 'NO'
            
            # Maestría de reporte de equipos
            pago_mj = row.get('PAGO MAESTRÍA')
            px_data['maestria'] = 'SI' if str(pago_mj).strip().upper() in ['PAGADO', 'SI'] else 'NO'
            
            # Observaciones
            obs_parts = []
            fds = row.get('FDS')
            if fds and not pd.isna(fds):
                obs_parts.append(f"FDS: {fds}")
            pago_c2 = row.get('PAGO CAPÍTULO2')
            if pago_c2 and not pd.isna(pago_c2):
                obs_parts.append(f"Pago C2: {pago_c2}")
            pago_mj_val = row.get('PAGO MAESTRÍA')
            if pago_mj_val and not pd.isna(pago_mj_val):
                obs_parts.append(f"Pago MJ: {pago_mj_val}")
                
            if obs_parts:
                px_data['observaciones'] = " | ".join(obs_parts)
                
            ins, upd = sincronizar_participante(px_data, c)
            if ins: inserted += 1
            if upd: updated += 1
            total_rows += 1
            
        conn.commit()
        conn.close()
        log.info(f"Excel local finalizado. Procesados: {total_rows} filas. Insertados: {inserted}, Actualizados: {updated}")
    except Exception as e:
        log.error(f"Error procesando Excel local: {e}")

def sincronizar_web_participantes():
    """Scrapea la lista viva de la web de crearpslglobal.com utilizando Selenium."""
    log.info("Iniciando web scraping en crearpslglobal.com...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 1. Login
        driver.get(URL_LOGIN)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "exampleInputEmail1")))
        
        driver.find_element(By.ID, "exampleInputEmail1").send_keys(USER)
        driver.find_element(By.ID, "exampleInputPassword1").send_keys(PASS)
        driver.find_element(By.CSS_SELECTOR, "button.btn-primary").click()
        time.sleep(3)
        
        # 2. Navegar a datos de participante
        driver.get(TARGET_URL)
        time.sleep(5)
        
        # 3. Mostrar Todos (seleccionar 'all' en pageSize select)
        try:
            length_select = Select(driver.find_element(By.ID, "pageSize"))
            length_select.select_by_value("all")
            log.info("Configurado dropdown a 'Todos' (mostrar toda la base de datos).")
            time.sleep(5)
        except Exception as se:
            log.warning(f"No se encontró dropdown de paginación pageSize: {se}")
            
        # 4. Obtener HTML y parsear la tabla
        tables = driver.find_elements(By.TAG_NAME, "table")
        if not tables:
            log.error("No se encontraron tablas de participantes en la página web.")
            driver.quit()
            return
            
        tabla = max(tables, key=lambda t: len(t.find_elements(By.TAG_NAME, "tr")))
        html_table = tabla.get_attribute('outerHTML')
        driver.quit()
        
        df_list = pd.read_html(io.StringIO(html_table))
        if not df_list:
            log.error("Pandas no pudo parsear la tabla HTML.")
            return
            
        df = df_list[0]
        # Normalizar nombres de columnas a mayúsculas
        df.columns = [str(col).strip().upper() for col in df.columns]
        
        col_map = {
            'IDENTIFICACIÓN': 'identificacion',
            'NOMBRE': 'nombre',
            'APELLIDO': 'apellido',
            'TELÉFONO': 'telefono',
            'C1': 'c1',
            'C2': 'c2',
            'MAESTRÍA': 'maestria',
            'TIPO': 'tipo',
            'EQUIPO': 'equipo',
            'IMO': 'imo',
            'TEL. IMO': 'tel_imo'
        }
        
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        inserted = 0
        updated = 0
        total_rows = 0
        
        for _, row in df.iterrows():
            px_data = {}
            for col_src, key in col_map.items():
                col_found = next((cf for cf in df.columns if col_src in cf), None)
                if col_found:
                    px_data[key] = row[col_found]
                    
            # Mapeos de flags de asistencia
            px_data['c1'] = 'SI' if px_data.get('c1') == 'SI' else 'NO'
            px_data['c2'] = 'SI' if px_data.get('c2') == 'SI' else 'NO'
            px_data['maestria'] = 'SI' if px_data.get('maestria') == 'SI' else 'NO'
            
            px_data['observaciones'] = "Origen: Web Scrape"
            
            ins, upd = sincronizar_participante(px_data, c)
            if ins: inserted += 1
            if upd: updated += 1
            total_rows += 1
            
        conn.commit()
        conn.close()
        log.info(f"Sincronización web finalizada. Filas: {total_rows}. Insertados: {inserted}, Actualizados: {updated}")
    except Exception as e:
        log.error(f"Error en web scraper: {e}")
        if driver:
            try: driver.quit()
            except: pass

# --- DEMONIO / BUCLE DE MONITOREO ---

def run_once():
    """Ejecuta una iteración de comprobación y procesamiento."""
    meta = load_metadata()
    metadata_updated = False
    
    # 1. Comprobar Precios Excel
    if os.path.exists(EXCEL_PRECIOS):
        mtime = os.path.getmtime(EXCEL_PRECIOS)
        if mtime > meta.get("precios_mtime", 0.0):
            log.info("Detectado cambio en Excel de precios.")
            procesar_precios()
            meta["precios_mtime"] = mtime
            metadata_updated = True
            
    # 2. Comprobar Manuales de PDF
    pdf_changed = False
    manuals = [
        "GERENTE MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES.pdf",
        "COORDINADOR C1 y C2 MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES1.pdf",
        "COORDINADOR DE MAESTRÍA MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES2.pdf",
        "MANUALES OPERATIVOS INTEGRALES.pdf"
    ]
    
    mtime_keys = {
        "GERENTE MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES.pdf": "manual_gerente_mtime",
        "COORDINADOR C1 y C2 MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES1.pdf": "manual_coord_c1c2_mtime",
        "COORDINADOR DE MAESTRÍA MANUAL CORPORATIVO INTEGRAL - CREAR PODER SIN LÍMITES2.pdf": "manual_coord_mj_mtime",
        "MANUALES OPERATIVOS INTEGRALES.pdf": "manuales_operativos_mtime"
    }
    
    for filename in manuals:
        path = os.path.join(DIR_MANUALES, filename)
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            k = mtime_keys[filename]
            if mtime > meta.get(k, 0.0):
                log.info(f"Detectado cambio en manual PDF: {filename}")
                pdf_changed = True
                meta[k] = mtime
                metadata_updated = True
                
    if pdf_changed:
        procesar_manuales()
        
    # 3. Comprobar Excel de Equipos Local
    if os.path.exists(EXCEL_EQUIPOS):
        mtime = os.path.getmtime(EXCEL_EQUIPOS)
        if mtime > meta.get("reporte_equipos_mtime", 0.0):
            log.info("Detectado cambio en Excel local de equipos.")
            sincronizar_excel_equipos()
            meta["reporte_equipos_mtime"] = mtime
            metadata_updated = True
            
    # 3.5. Comprobar Excel de Graduados
    if os.path.exists(EXCEL_GRADUADOS):
        mtime = os.path.getmtime(EXCEL_GRADUADOS)
        if mtime > meta.get("graduados_mtime", 0.0):
            log.info("Detectado cambio en Excel oficial de graduados. Iniciando Agente Vigilante...")
            try:
                import agente_vigilante_graduados_completo
                agente_vigilante_graduados_completo.run_agent()
            except Exception as ev:
                log.error(f"Error al ejecutar el Agente Vigilante de Graduados: {ev}")
            meta["graduados_mtime"] = mtime
            metadata_updated = True
            
    # 4. Comprobar Sincronización Web (cada 24 horas = 86400s)
    now = time.time()
    if now - meta.get("last_web_scrape", 0.0) >= 86400:
        log.info("Transcurridas 24 horas desde la última sincronización web. Iniciando...")
        sincronizar_web_participantes()
        meta["last_web_scrape"] = now
        metadata_updated = True
        
    if metadata_updated:
        save_metadata(meta)

def loop_daemon():
    log.info("=================================================================")
    log.info("   INICIANDO AGENTE AUTÓNOMO DE SINCRONIZACIÓN EN SEGUNDO PLANO")
    log.info("=================================================================")
    # Primera comprobación al arrancar
    try:
        run_once()
    except Exception as e:
        log.error(f"Error en iteración inicial: {e}")
        
    while True:
        try:
            run_once()
        except Exception as e:
            log.error(f"Error en bucle del agente: {e}")
        # Comprobar cada 60 segundos (mantiene consumo de CPU a 0% cuando no hay cambios)
        time.sleep(60)

def is_already_running(script_name):
    import os
    try:
        import psutil
        my_pid = os.getpid()
        my_ppid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                if name and 'python' in name.lower():
                    pid = proc.info['pid']
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if pid != my_pid and pid != my_ppid and script_name in cmdline_str:
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except:
        return False

if __name__ == "__main__":
    if is_already_running("agente_sincronizador_autonomo.py"):
        log.error("El agente de sincronización ya está en ejecución en otro proceso. Cancelando inicio.")
        sys.exit(1)
    loop_daemon()
