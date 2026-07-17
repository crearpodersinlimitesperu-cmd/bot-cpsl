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

DATA_FILE = r"C:\Users\josem\Downloads\bot-cpsl-review\scratch\sms_pendientes_data.json"
LOG_FILE = r"C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_indicaciones_e28.txt"

def limpiar_telefono(tel_str):
    if not tel_str:
        return ""
    # Dejar solo dígitos
    tel_clean = "".join(filter(str.isdigit, str(tel_str)))
    # Si tiene código de país 51 al inicio y mide más de 9 dígitos, quitar el 51
    if len(tel_clean) > 9 and tel_clean.startswith("51"):
        tel_clean = tel_clean[2:]
    return tel_clean

def ejecutar_envio_sms():
    print("="*60)
    print("  EJECUCIÓN DE ENVÍO SMS - INDICACIONES C1 E28 PENDIENTES")
    print("="*60)
    
    if not os.path.exists(DATA_FILE):
        print(f"Error: No existe el archivo de datos preparados en {DATA_FILE}")
        return
        
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        participantes = json.load(f)
        
    print(f"Total registros cargados: {len(participantes)}")
    
    enviados = 0
    errores = 0
    sin_telefono = 0
    
    log_entries = []
    log_entries.append("REPORTE ENVÍO SMS INDICACIONES C1 EQUIPO 28 - PENDIENTES")
    log_entries.append("="*60)
    
    for idx, px in enumerate(participantes):
        nombre_completo = f"{px.get('Nombre', '')} {px.get('Apellido', '')}".strip()
        nombre_pref = px.get("NombrePref", "").strip()
        tel_raw = px.get("Telefono", "")
        tel_clean = limpiar_telefono(tel_raw)
        
        cc_nombre = px.get("Coordinador", "")
        cc_tel = px.get("CC_Tel", "")
        
        # Validar teléfono del participante
        if not tel_clean or len(tel_clean) != 9:
            msg = f"⚠️ OMITIDO: {nombre_completo} - Sin teléfono válido de 9 dígitos ({tel_raw})."
            print(msg)
            log_entries.append(msg)
            sin_telefono += 1
            continue
            
        # Mensaje Opción A (Aprobado)
        mensaje = (
            f"Hola {nombre_pref}, de CREAR. Tu C1 E28 está listo para este 29, 30 y 31 de mayo en BTH Hotel Boutique Concept "
            f"(Av. Guardia Civil 727, San Borja). Registro: Viernes 9:00 AM (trae DNI físico, ropa cómoda y botella de agua). "
            f"Tu coordinadora asignada es {cc_nombre} (Tel: {cc_tel}). Comunícate urgente con ella para confirmar tu asistencia. ¡Te esperamos!"
        )
        
        # Imprimir primer ejemplo como debug
        if enviados == 0 and errores == 0 and sin_telefono == 0:
            print("\n--- VISTA PREVIA DEL PRIMER MENSAJE ---")
            print(f"Destinatario: {tel_clean} ({nombre_completo})")
            print(f"Mensaje: {mensaje}")
            print(f"Longitud: {len(mensaje)} caracteres")
            print("---------------------------------------\n")
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
            
        # Pausa entre envíos para no saturar MacroDroid
        time.sleep(4)
        
    # Escribir log
    log_entries.append("="*60)
    log_entries.append("RESUMEN FINAL:")
    log_entries.append(f"Total procesados: {len(participantes)}")
    log_entries.append(f"Enviados con éxito: {enviados}")
    log_entries.append(f"Errores de envío: {errores}")
    log_entries.append(f"Sin teléfono válido: {sin_telefono}")
    
    with open(LOG_FILE, "w", encoding="utf-8") as lf:
        lf.write("\n".join(log_entries) + "\n")
        
    print("\n" + "="*60)
    print("  RESUMEN FINAL")
    print(f"  Total procesados: {len(participantes)}")
    print(f"  Enviados éxito: {enviados}")
    print(f"  Errores: {errores}")
    print(f"  Omitidos (sin tel): {sin_telefono}")
    print("="*60)
    print(f"Reporte de envío guardado en: {LOG_FILE}")

if __name__ == "__main__":
    ejecutar_envio_sms()
