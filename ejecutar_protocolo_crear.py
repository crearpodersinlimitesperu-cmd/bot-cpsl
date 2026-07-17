import pandas as pd
import sqlite3
import os
import json
import requests
import time
from pathlib import Path
from datetime import datetime

# Configuración Gateway
MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
EVENT_NAME = "enviar_sms"

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"
GRADUADOS_XLSX = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\GRADUADOS LIMA.xlsx")

def registrar_log(categoria, evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def auditar_graduados_mj():
    print("--- 1. AUDITORIA DE GRADUADOS MJ ---")
    if not GRADUADOS_XLSX.exists(): return 0
    try:
        df = pd.read_excel(GRADUADOS_XLSX, sheet_name='GRADUADOS ')
        df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
        excel_names = []
        for col in df.columns:
            vals = df[col].dropna().astype(str).str.strip().str.upper()
            for v in vals:
                if len(v) > 5 and ' ' in v and not any(x in v for x in ['FECHA', 'EQUIPO', 'TOTAL']):
                    excel_names.append(v)
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        db_px = pd.read_sql("SELECT id, nombre, apellido FROM participantes", conn)
        db_px['FULL_NAME'] = (db_px['nombre'] + ' ' + db_px['apellido']).str.strip().str.upper()
        
        cursor.execute("UPDATE participantes SET maestria = 'NO'")
        ids_to_mj = set()
        for ex_name in excel_names:
            matches = db_px[db_px['FULL_NAME'].apply(lambda x: ex_name in x or x in ex_name)]
            for px_id in matches['id']: ids_to_mj.add(int(px_id))
        
        if ids_to_mj:
            cursor.execute(f"UPDATE participantes SET maestria = 'SI', c1 = 'SI', c2 = 'SI' WHERE id IN ({','.join(map(str, ids_to_mj))})")
        conn.commit()
        conn.close()
        return len(ids_to_mj)
    except: return 0

def ejecutar_envio_sms_real():
    print("--- 2. EJECUCION REAL DE ENVIO SMS (GATEWAY ACTIVO) ---")
    agenda_path = BASE_DIR / "sms_manana_8am.json"
    if not agenda_path.exists():
        print("No hay agenda.")
        return 0
    
    with open(agenda_path, "r", encoding='utf-8') as f:
        agenda = json.load(f)
    
    conn_log = sqlite3.connect(LOG_DB)
    try:
        rebotes = pd.read_sql("SELECT detalle FROM logs WHERE categoria='BOUNCE'", conn_log)
        rebotes_list = rebotes['detalle'].str.lower().tolist()
    except: rebotes_list = []
    conn_log.close()
    
    envios_ok = 0
    url_base = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{EVENT_NAME}"
    
    for msg in agenda:
        tel = str(msg['telefono']).replace('.0', '')
        # Limpiar telefono (solo ultimos 9 digitos)
        tel = "".join(c for c in tel if c.isdigit())[-9:]
        texto = msg['mensaje']
        
        if any(r in tel or r in texto.lower() for r in rebotes_list):
            continue
            
        print(f"Despachando a {tel}...")
        try:
            r = requests.get(url_base, params={'numero': tel, 'mensaje': texto}, timeout=15)
            if r.status_code == 200:
                envios_ok += 1
                # Pequeña pausa para no saturar el buffer del telefono
                time.sleep(4)
            else:
                print(f"Error Gateway: {r.status_code}")
        except Exception as e:
            print(f"Error conexion: {e}")
            break # Si falla la red, paramos
            
    registrar_log('SMS', 'DESPACHO_MASIVO', f"Enviados {envios_ok} SMS reales via MacroDroid.", "EXITO")
    return envios_ok

if __name__ == "__main__":
    grad = auditar_graduados_mj()
    envios = ejecutar_envio_sms_real()
    print(f"\nSincronizados: {grad} MJ")
    print(f"Enviados Reales: {envios} SMS")
