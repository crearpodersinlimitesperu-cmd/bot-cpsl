import pandas as pd
import requests
import time
import os
import sys
from dotenv import load_dotenv

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

# Mapeo de coordinadores a partir del 'Usuario Actual' en Excel
COORDINADORES = {
    'jmarin': {'nombre': 'Joyce', 'telefono': '933599903'},
    'dmoscoso': {'nombre': 'Diana', 'telefono': '912379744'},
    'jsanchez': {'nombre': 'Jose', 'telefono': '919563284'},
    'jose': {'nombre': 'Jose', 'telefono': '919563284'}
}

def limpiar_telefono(tel_str):
    if pd.isna(tel_str):
        return ""
    tel_clean = "".join(filter(str.isdigit, str(tel_str)))
    if len(tel_clean) > 9 and tel_clean.startswith("51"):
        tel_clean = tel_clean[2:]
    return tel_clean

def limpiar_nombre(nombre_str):
    if pd.isna(nombre_str):
        return ""
    return str(nombre_str).split()[0].title()

def ejecutar_correccion():
    print("="*60)
    print("  ENVÍO DE SMS MASIVO - FE DE ERRATAS C1 EQUIPO 28")
    print("="*60)
    
    csv_path = r'C:\Users\josem\Downloads\participantes_2026-05-25.csv'
    excel_path = r'C:\Users\josem\Downloads\ASIGNACIONES 0526.xlsx'
    
    df_csv = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    df_excel = pd.read_excel(excel_path)
    
    # Identificar columnas
    id_col_csv = [c for c in df_csv.columns if 'identificac' in c.lower()][0]
    id_col_excel = [c for c in df_excel.columns if 'identificac' in c.lower() and 'imo' not in c.lower()][0]
    
    # Limpiar DNI para cruce
    df_csv['Identificación_clean'] = df_csv[id_col_csv].astype(str).str.strip().str.replace('.0', '', regex=False)
    df_excel['Identificación_clean'] = df_excel[id_col_excel].astype(str).str.strip().str.replace('.0', '', regex=False)
    
    # Filtrar solo E28 del CSV
    e28_csv = df_csv[df_csv['Equipo'].str.contains('28', na=False, case=False)]
    
    # Cruzar datos
    merged = pd.merge(e28_csv, df_excel, on='Identificación_clean', how='inner')
    
    total_participantes = len(merged)
    print(f"Total participantes E28 cruzados exitosamente: {total_participantes}\n")

    enviados = 0
    errores = 0
    omitidos = 0
    
    log_file = open(r'C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_erratas_e28.txt', 'w', encoding='utf-8')
    log_file.write(f"REPORTE FE DE ERRATAS SMS C1 EQUIPO 28\n")
    log_file.write("="*60 + "\n")

    for index, row in merged.iterrows():
        nombre_px = limpiar_nombre(row.get('Nombre_x', row.get('Nombre')))
        tel_px = limpiar_telefono(row.get('Teléfono', ''))
        usuario_actual = str(row.get('Usuario Actual', '')).strip().lower()
        
        if not tel_px or len(tel_px) < 9:
            msg_log = f"⚠️ OMITIDO: {nombre_px} - Sin teléfono."
            print(msg_log)
            log_file.write(msg_log + "\n")
            omitidos += 1
            continue
            
        coord_info = COORDINADORES.get(usuario_actual)
        if not coord_info:
            msg_log = f"⚠️ OMITIDO: {nombre_px} - Coordinador '{usuario_actual}' desconocido."
            print(msg_log)
            log_file.write(msg_log + "\n")
            omitidos += 1
            continue

        nombre_coord = coord_info['nombre']
        tel_coord = coord_info['telefono']

        # Crear mensaje corregido
        texto = f"FE DE ERRATAS: Hola {nombre_px}, de CREAR. Hubo un error en nuestro msj anterior. Tu coordinador oficial para el C1 es {nombre_coord}. Por favor guarda su numero: {tel_coord}. Disculpa la confusion!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_px, "mensaje": texto}
        
        # Modo Debug: mostrar el primer mensaje
        if enviados == 0 and errores == 0 and omitidos == 0:
            print("\n--- EJEMPLO DE MENSAJE ---")
            print(f"Destinatario: {tel_px} ({nombre_px})")
            print(f"Mensaje: {texto}")
            print("--------------------------\n")
            time.sleep(2)

        print(f"Enviando ERRATA a {nombre_px} ({tel_px})... ", end="", flush=True)
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print(f"[OK - Asignado a {nombre_coord}]", flush=True)
                log_file.write(f"[EXITO] {tel_px} - {nombre_px} -> Coord: {nombre_coord}\n")
                enviados += 1
            else:
                print(f"[ERROR HTTP {r.status_code}]", flush=True)
                log_file.write(f"[ERROR {r.status_code}] {tel_px} - {nombre_px}\n")
                errores += 1
        except Exception as e:
            print(f"[EXCEPCIÓN]", flush=True)
            log_file.write(f"[EXCEPCION] {tel_px} - {nombre_px}: {str(e)}\n")
            errores += 1
            
        time.sleep(4)
        
    log_file.write("\n" + "="*60 + "\n")
    log_file.write(f"RESUMEN FINAL:\n")
    log_file.write(f"Total procesados: {total_participantes}\n")
    log_file.write(f"Enviados con éxito: {enviados}\n")
    log_file.write(f"Errores de envío: {errores}\n")
    log_file.write(f"Omitidos: {omitidos}\n")
    log_file.close()

    print("\n" + "="*60)
    print(f"  RESUMEN FINAL ERRATAS")
    print(f"  Total cruzados: {total_participantes}")
    print(f"  Enviados éxito: {enviados}")
    print(f"  Errores: {errores}")
    print(f"  Omitidos: {omitidos}")
    print("="*60)
    print("Reporte guardado en: reporte_sms_erratas_e28.txt")

if __name__ == "__main__":
    ejecutar_correccion()
