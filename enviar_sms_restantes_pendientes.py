import os
import sys
import json
import time
import re
import requests

# Asegurar UTF-8 en consola
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# Configuración MacroDroid
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
MACRODROID_EVENT = "enviar_sms"
URL_TRIGGER = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"

DATA_FILE = r"C:\Users\josem\Downloads\bot-cpsl-review\scratch\sms_pendientes_calls_data.json"
PREV_LOG_FILE = r"C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_indicaciones_e28.txt"
NEW_LOG_FILE = r"C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_indicaciones_e28_fase2.txt"

def limpiar_telefono(tel_str):
    if not tel_str:
        return ""
    tel_clean = "".join(filter(str.isdigit, str(tel_str)))
    if len(tel_clean) > 9 and tel_clean.startswith("51"):
        tel_clean = tel_clean[2:]
    return tel_clean

def ejecutar_envio_completo():
    print("="*60)
    print("  EJECUCIÓN SMS - INDICACIONES C1 E28 (FASE 2: 1ra y 2da LLAMADA)")
    print("="*60)
    
    if not os.path.exists(DATA_FILE):
        print(f"Error: No existe el archivo de datos en {DATA_FILE}")
        return
        
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        participantes = json.load(f)
        
    # Cargar teléfonos ya enviados anteriormente para evitar duplicados
    enviados_previamente = set()
    if os.path.exists(PREV_LOG_FILE):
        with open(PREV_LOG_FILE, "r", encoding="utf-8") as lf:
            for line in lf:
                if "[EXITO]" in line:
                    match = re.search(r"\[EXITO\]\s*(\d+)", line)
                    if match:
                        enviados_previamente.add(match.group(1))
                        
    print(f"Total registros cargados de 1ra y 2da llamada pendientes: {len(participantes)}")
    print(f"Total números ya contactados previamente: {len(enviados_previamente)}")
    
    enviados = 0
    errores = 0
    sin_telefono = 0
    duplicados_omitidos = 0
    
    log_entries = []
    log_entries.append("REPORTE ENVÍO SMS INDICACIONES C1 EQUIPO 28 - PENDIENTES FASE 2")
    log_entries.append("="*60)
    
    for idx, px in enumerate(participantes):
        nombre_completo = f"{px.get('Nombre', '')} {px.get('Apellido', '')}".strip()
        nombre_pref = px.get("NombrePref", "").strip()
        tel_raw = px.get("Telefono", "")
        tel_clean = limpiar_telefono(tel_raw)
        
        cc_nombre = px.get("Coordinador", "")
        cc_tel = px.get("CC_Tel", "")
        
        # Validar teléfono
        if not tel_clean or len(tel_clean) != 9:
            msg = f"⚠️ OMITIDO: {nombre_completo} - Sin teléfono válido de 9 dígitos ({tel_raw})."
            print(msg)
            log_entries.append(msg)
            sin_telefono += 1
            continue
            
        # Validar duplicados
        if tel_clean in enviados_previamente:
            msg = f"ℹ️ OMITIDO (YA ENVIADO): {nombre_completo} ({tel_clean}) ya recibió el SMS en la fase 1."
            print(msg)
            duplicados_omitidos += 1
            continue
            
        # Mensaje Opción A
        mensaje = (
            f"Hola {nombre_pref}, de CREAR. Tu C1 E28 está listo para este 29, 30 y 31 de mayo en BTH Hotel Boutique Concept "
            f"(Av. Guardia Civil 727, San Borja). Registro: Viernes 9:00 AM (trae DNI físico, ropa cómoda y botella de agua). "
            f"Tu coordinadora asignada es {cc_nombre} (Tel: {cc_tel}). Comunícate urgente con ella para confirmar tu asistencia. ¡Te esperamos!"
        )
        
        # Imprimir primer ejemplo como debug
        if enviados == 0 and errores == 0 and sin_telefono == 0:
            print("\n--- VISTA PREVIA DEL PRIMER MENSAJE DE ESTA FASE ---")
            print(f"Destinatario: {tel_clean} ({nombre_completo})")
            print(f"Mensaje: {mensaje}")
            print(f"Longitud: {len(mensaje)} caracteres")
            print("----------------------------------------------------\n")
            time.sleep(2)
            
        print(f"[{idx+1}/{len(participantes)}] Enviando SMS a {nombre_pref} ({tel_clean})... ", end="", flush=True)
        
        params = {
            "numero": tel_clean,
            "mensaje": mensaje
        }
        
        try:
            r = requests.get(URL_TRIGGER, params=params, timeout=15)
            if r.status_code == 200:
                print("[OK]")
                log_entries.append(f"[EXITO] {tel_clean} - {nombre_completo} -> Coordinadora: {cc_nombre}")
                enviados += 1
            else:
                print(f"[ERROR HTTP {r.status_code}]")
                log_entries.append(f"[ERROR HTTP {r.status_code}] {tel_clean} - {nombre_completo}")
                errores += 1
        except Exception as e:
            print("[EXCEPCIÓN]")
            log_entries.append(f"[EXCEPCION] {tel_clean} - {nombre_completo}: {str(e)}")
            errores += 1
            
        # Pausa entre envíos
        time.sleep(4)
        
    # Escribir log
    log_entries.append("="*60)
    log_entries.append("RESUMEN FASE 2:")
    log_entries.append(f"Total procesados en esta lista: {len(participantes)}")
    log_entries.append(f"Enviados con éxito en esta fase: {enviados}")
    log_entries.append(f"Ya enviados en fase anterior: {duplicados_omitidos}")
    log_entries.append(f"Errores de envío: {errores}")
    log_entries.append(f"Sin teléfono válido: {sin_telefono}")
    
    with open(NEW_LOG_FILE, "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_entries) + "\n")
        
    print("\n" + "="*60)
    print("  RESUMEN FINAL FASE 2")
    print(f"  Total procesados: {len(participantes)}")
    print(f"  Enviados éxito: {enviados}")
    print(f"  Omitidos (ya enviados anteriormente): {duplicados_omitidos}")
    print(f"  Omitidos (sin tel): {sin_telefono}")
    print(f"  Errores: {errores}")
    print("="*60)
    print(f"Reporte de esta fase guardado en: {NEW_LOG_FILE}")

if __name__ == "__main__":
    ejecutar_envio_completo()
