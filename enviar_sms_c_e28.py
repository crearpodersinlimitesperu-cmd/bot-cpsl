import pandas as pd
import requests
import time
import os
import sys
from dotenv import load_dotenv

# Asegurar UTF-8 en consola
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Cargar variables de entorno
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"

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
    # Tomar solo el primer nombre
    return str(nombre_str).split()[0].title()

def ejecutar_envio():
    print("="*60)
    print("  ENVÍO DE SMS MASIVO - C1 EQUIPO 28 - ASIGNACIÓN DE IMO")
    print("="*60)
    
    csv_path = r'C:\Users\josem\Downloads\participantes_2026-05-25.csv'
    
    try:
        df = pd.read_csv(csv_path, encoding='utf-8', on_bad_lines='skip')
    except Exception as e:
        print(f"Error leyendo CSV: {e}")
        return

    # Filtrar Equipo 28
    e28_df = df[df['Equipo'].str.contains('28', na=False, case=False)]
    
    total_participantes = len(e28_df)
    print(f"Total participantes E28 encontrados: {total_participantes}\n")

    enviados = 0
    errores = 0
    sin_telefono = 0
    
    # Crear archivo de log
    log_file = open(r'C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_e28_asignacion.txt', 'w', encoding='utf-8')
    log_file.write(f"REPORTE ENVÍO SMS C1 EQUIPO 28\n")
    log_file.write("="*60 + "\n")

    for index, row in e28_df.iterrows():
        nombre_px = limpiar_nombre(row.get('Nombre', ''))
        tel_px = limpiar_telefono(row.get('Teléfono', ''))
        
        nombre_imo = limpiar_nombre(row.get('IMO', ''))
        tel_imo = limpiar_telefono(row.get('Tel. IMO', ''))
        
        if not tel_px or len(tel_px) < 9:
            msg_log = f"⚠️ OMITIDO: {nombre_px} - Sin teléfono de participante válido."
            print(msg_log)
            log_file.write(msg_log + "\n")
            sin_telefono += 1
            continue
            
        if not nombre_imo or not tel_imo:
            msg_log = f"⚠️ OMITIDO: {nombre_px} - Sin IMO o teléfono de IMO válido."
            print(msg_log)
            log_file.write(msg_log + "\n")
            sin_telefono += 1
            continue

        # Crear mensaje
        texto = f"Hola {nombre_px}, de CREAR. Tu coordinador (C) asignado para el C1 es {nombre_imo}. Por favor guarda su numero: {tel_imo}. Nos vemos pronto!"
        
        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_px, "mensaje": texto}
        
        # Modo Debug: mostrar el primer mensaje y hacer pausa
        if enviados == 0 and errores == 0 and sin_telefono == 0:
            print("\n--- EJEMPLO DE MENSAJE ---")
            print(f"Destinatario: {tel_px} ({nombre_px})")
            print(f"Mensaje: {texto}")
            print("--------------------------\n")
            time.sleep(2)

        print(f"Enviando SMS a {nombre_px} ({tel_px})... ", end="", flush=True)
        
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]", flush=True)
                log_file.write(f"[EXITO] {tel_px} - {nombre_px} -> Coordinador: {nombre_imo}\n")
                enviados += 1
            else:
                print(f"[ERROR HTTP {r.status_code}]", flush=True)
                log_file.write(f"[ERROR {r.status_code}] {tel_px} - {nombre_px}\n")
                errores += 1
        except Exception as e:
            print(f"[EXCEPCIÓN]", flush=True)
            log_file.write(f"[EXCEPCION] {tel_px} - {nombre_px}: {str(e)}\n")
            errores += 1
            
        # Pausa de 4 segundos para no saturar Macrodroid
        time.sleep(4)
        
    log_file.write("\n" + "="*60 + "\n")
    log_file.write(f"RESUMEN FINAL:\n")
    log_file.write(f"Total procesados: {total_participantes}\n")
    log_file.write(f"Enviados con éxito: {enviados}\n")
    log_file.write(f"Errores de envío: {errores}\n")
    log_file.write(f"Sin teléfono válido: {sin_telefono}\n")
    log_file.close()

    print("\n" + "="*60)
    print(f"  RESUMEN FINAL")
    print(f"  Total procesados: {total_participantes}")
    print(f"  Enviados éxito: {enviados}")
    print(f"  Errores: {errores}")
    print(f"  Omitidos (sin tel): {sin_telefono}")
    print("="*60)
    print("Reporte guardado en: reporte_sms_e28_asignacion.txt")

if __name__ == "__main__":
    ejecutar_envio()
