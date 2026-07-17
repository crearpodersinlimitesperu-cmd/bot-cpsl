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

COORDINADORAS = {
    'jmarin': {'nombre': 'Joyce', 'telefono': '933599903'},
    'dmoscoso': {'nombre': 'Diana', 'telefono': '912379744'},
}

def limpiar_telefono(tel_str):
    if pd.isna(tel_str):
        return ""
    tel_clean = "".join(filter(str.isdigit, str(tel_str)))
    if len(tel_clean) > 9 and tel_clean.startswith("51"):
        tel_clean = tel_clean[2:]
    if tel_clean == "0":
        return ""
    return tel_clean

def cargar_imos_solo_telefono():
    """Carga IMOs que NO tienen correo pero SÍ tienen teléfono."""
    files = [
        r'C:\Users\josem\Downloads\reporte_equipos.xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (1).xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (2).xlsx',
        r'C:\Users\josem\Downloads\reporte_equipos (3).xlsx',
    ]
    dfs = []
    for f in files:
        dfs.append(pd.read_excel(f))
    df_reportes = pd.concat(dfs, ignore_index=True)
    df_reportes['id_clean'] = df_reportes['Identificación'].astype(str).str.strip().str.replace('.0', '', regex=False)

    csv_path = r'C:\Users\josem\Downloads\bot-cpsl-review\Asignados_Aptos_Joyce_Diana_Final.csv'
    df_aptos = pd.read_csv(csv_path)
    df_aptos['equipo_num'] = df_aptos['NombreEquipo'].str.extract(r'(\d+)').astype(float)
    df_aptos = df_aptos[df_aptos['equipo_num'].isin([25, 26, 27])].copy()
    df_aptos['imo_id_clean'] = df_aptos['IdentificacionIMO'].astype(str).str.strip().str.replace('.0', '', regex=False)

    imo_ids = df_aptos['imo_id_clean'].unique()

    # Primero encontrar los que tienen correo
    imo_info = {}
    imo_como_px = df_reportes[df_reportes['id_clean'].isin(imo_ids)]
    for _, row in imo_como_px.iterrows():
        imo_id = row['id_clean']
        if imo_id not in imo_info:
            correo = row.get('Correo', None)
            tel = row.get('TelefonoMovil', None)
            nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip().title()
            if correo and pd.notna(correo) and '@' in str(correo):
                imo_info[imo_id] = {'nombre': nombre, 'correo': str(correo).strip(), 'telefono': str(tel).strip() if pd.notna(tel) else ''}

    # Para los que faltan, buscar por participante en reportes
    for _, apto in df_aptos.iterrows():
        imo_id = apto['imo_id_clean']
        if imo_id in imo_info:
            continue
        px_id = str(apto.get('Identificación', '')).strip().replace('.0', '')
        if not px_id:
            continue
        match = df_reportes[df_reportes['id_clean'] == px_id]
        if len(match) > 0:
            row = match.iloc[0]
            nombre_imo = str(row.get('NombreIMO', '')).strip().title()
            tel_imo = str(row.get('TelefonoIMO', '')).strip()
            if nombre_imo and nombre_imo != 'Nan':
                imo_info[imo_id] = {'nombre': nombre_imo, 'correo': '', 'telefono': tel_imo if tel_imo != 'nan' else ''}

    # Intentar encontrar correo para los que solo tienen teléfono
    for imo_id, info in imo_info.items():
        if info['correo']:
            continue
        match = df_reportes[df_reportes['id_clean'] == imo_id]
        if len(match) > 0:
            for _, row in match.iterrows():
                correo = row.get('Correo', None)
                if correo and pd.notna(correo) and '@' in str(correo):
                    info['correo'] = str(correo).strip()
                    nombre = f"{row.get('NombreCompleto', '')} {row.get('ApellidoCompleto', '')}".strip().title()
                    if nombre:
                        info['nombre'] = nombre
                    break

    # Filtrar SOLO los que NO tienen correo pero SÍ tienen teléfono
    solo_tel = {k: v for k, v in imo_info.items() if not v['correo'] and v['telefono'] and v['telefono'] != 'nan'}
    return solo_tel, df_aptos

def ejecutar():
    print("="*70)
    print("  ENVÍO DE SMS A IMOS (SIN CORREO) - APTOS E25/E26/E27")
    print("="*70)

    imos_solo_tel, df_aptos = cargar_imos_solo_telefono()
    print(f"IMOs con solo teléfono a contactar: {len(imos_solo_tel)}")

    enviados = 0
    errores = 0
    omitidos = 0

    log = open(r'C:\Users\josem\Downloads\bot-cpsl-review\reporte_sms_imos_aptos.txt', 'w', encoding='utf-8')
    log.write("REPORTE DE SMS A IMOS (SIN CORREO) - APTOS E25/E26/E27\n")
    log.write("="*70 + "\n\n")

    for imo_id, info in sorted(imos_solo_tel.items()):
        nombre_imo = info['nombre'].split()[0].title() if info['nombre'] else 'IMO'
        tel_imo = limpiar_telefono(info['telefono'])

        if not tel_imo or len(tel_imo) < 9:
            log.write(f"[OMITIDO] DNI {imo_id} - {info['nombre']} - Tel inválido: {info['telefono']}\n")
            omitidos += 1
            continue

        # Participantes de este IMO
        pxs = df_aptos[df_aptos['imo_id_clean'] == imo_id]
        if len(pxs) == 0:
            continue

        # Determinar coordinadora(s)
        coords_set = set()
        for _, px in pxs.iterrows():
            coord_key = str(px['Usuario Registro']).strip().lower()
            coord = COORDINADORAS.get(coord_key)
            if coord:
                coords_set.add((coord['nombre'], coord['telefono']))

        coords_txt = " y ".join([f"{c[0]} ({c[1]})" for c in coords_set])
        n_px = len(pxs)

        mensaje = (
            f"Hola {nombre_imo}, de CREAR PSL. "
            f"Tu{'s' if n_px > 1 else ''} {n_px} enrolado{'s' if n_px > 1 else ''} "
            f"esta{'n' if n_px > 1 else ''} APTO{'S' if n_px > 1 else ''} y 100% pagado{'s' if n_px > 1 else ''}. "
            f"Necesitamos que lo{'s' if n_px > 1 else ''} contactes HOY y le{'s' if n_px > 1 else ''} pidas que "
            f"escriban a su coordinadora {coords_txt} para confirmar asistencia al C1 "
            f"(29-31 mayo, Hotel BTH, San Borja, 9AM). "
            f"Tu llamado personal hace la diferencia. Responde LISTO cuando confirmen."
        )

        url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{MACRODROID_EVENT}"
        params = {"numero": tel_imo, "mensaje": mensaje}

        if enviados == 0 and errores == 0 and omitidos == 0:
            print(f"\n--- EJEMPLO DE MENSAJE ---")
            print(f"Destinatario: {tel_imo} ({info['nombre']})")
            print(f"Mensaje: {mensaje}")
            print(f"--------------------------\n")

        print(f"SMS a {info['nombre']} ({tel_imo}) [{n_px} PXs]... ", end="", flush=True)
        try:
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                print("[OK]", flush=True)
                log.write(f"[EXITO] {tel_imo} - {info['nombre']} ({n_px} PXs) -> {coords_txt}\n")
                enviados += 1
            else:
                print(f"[ERROR HTTP {r.status_code}]", flush=True)
                log.write(f"[ERROR] {tel_imo} - {info['nombre']}: HTTP {r.status_code}\n")
                errores += 1
        except Exception as e:
            print(f"[EXCEPCION]", flush=True)
            log.write(f"[EXCEPCION] {tel_imo} - {info['nombre']}: {e}\n")
            errores += 1

        time.sleep(4)

    log.write(f"\n{'='*70}\nRESUMEN: Enviados={enviados} | Errores={errores} | Omitidos={omitidos}\n")
    log.close()

    print(f"\n{'='*70}")
    print(f"  RESUMEN: Enviados={enviados} | Errores={errores} | Omitidos={omitidos}")
    print(f"{'='*70}")
    print("Reporte: reporte_sms_imos_aptos.txt")

if __name__ == "__main__":
    ejecutar()
