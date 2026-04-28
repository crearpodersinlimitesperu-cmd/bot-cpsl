import os
import json
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from io import StringIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ====== CONFIGURACION ======
CREARPSL_USER = os.getenv("CREARPSL_USER", "jsanchez")
CREARPSL_PASS = os.getenv("CREARPSL_PASS", "crearpsl25")
SHEET_CRM_ID = os.getenv("SHEET_CRM_ID", "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y")

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

URL_LOGIN = "https://crearpslglobal.com/admin/login.php"
URL_AUTH = "https://crearpslglobal.com/admin/iniciar_sesion.php"

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_json = os.environ.get("GOOGLE_CREDENTIALS")
    if creds_json:
        info = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
        return gspread.authorize(creds)
    elif os.path.exists("credenciales.json"):
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        return gspread.authorize(creds)
    return None

def push_to_sheet(client, sh, sheet_name, df):
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=30)
    
    ws.clear()
    if not df.empty:
        # Convert all to string and handle NaN
        df = df.fillna("").astype(str)
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    print(f"✅ Uploaded {len(df)} rows to {sheet_name}")

def iterar_reporte(s, url, table_index=1):
    # Fetch initial to get dropdown options
    r = s.get(url, headers=HEADERS)
    soup = BeautifulSoup(r.text, 'html.parser')
    
    eq_select = soup.find('select', id='cbnEquipo')
    cc_select = soup.find('select', {'id': ['IdCoordinador', 'cbnCoordinador']})
    
    if not eq_select or not cc_select:
        return pd.DataFrame()

    equipos = [opt['value'] for opt in eq_select.find_all('option') if opt.get('value')]
    ccs = [opt['value'] for opt in cc_select.find_all('option') if opt.get('value')]
    
    cc_name_attr = cc_select.get('name')
    
    all_dfs = []
    for eq in equipos:
        for cc in ccs:
            data = {
                'cbnEquipo': eq,
                cc_name_attr: cc,
                'userId': CREARPSL_USER,
                'invoice_btn': 'Consultar'
            }
            res = s.post(url, data=data, headers=HEADERS)
            try:
                dfs = pd.read_html(StringIO(res.text), flavor='lxml')
                if len(dfs) > table_index:
                    df = dfs[table_index]
                    # Drop last row if it's "Total"
                    if not df.empty and str(df.iloc[-1, 0]).strip().lower() == 'total':
                        df = df.iloc[:-1]
                    
                    if not df.empty:
                        df['Filter_Eq'] = eq
                        df['Filter_CC'] = cc
                        all_dfs.append(df)
            except Exception as e:
                pass
            time.sleep(0.1) # Be nice to the server
            
    if all_dfs:
        return pd.concat(all_dfs, ignore_index=True)
    return pd.DataFrame()

def iniciar_sync():
    print("🚀 Iniciando Sincronizador OMNI CrearPSL...")
    s = requests.Session()
    s.headers.update(HEADERS)
    
    s.get(URL_LOGIN)
    r_auth = s.post(URL_AUTH, data={'usuario': CREARPSL_USER, 'password': CREARPSL_PASS, 'ingresar': ''})
    
    if "iniciar_sesion.php" in r_auth.url or "login" in r_auth.url:
        print("❌ Fallo en el login.")
        # Try alternative
        r_auth = s.post(URL_AUTH, data={'usuario': CREARPSL_USER, 'clave': CREARPSL_PASS, 'ingresar': ''})
    
    client = conectar_sheets()
    if not client:
        print("❌ No se pudo conectar a Google Sheets.")
        return
    
    sh = client.open_by_key(SHEET_CRM_ID)
    
    # 1. Participantes
    print("Fetching Participantes...")
    try:
        r = s.get('https://crearpslglobal.com/admin/datosparticipante.php?mostrar=todos')
        dfs = pd.read_html(StringIO(r.text), flavor='lxml')
        push_to_sheet(client, sh, 'CREARPSL_PARTICIPANTES', dfs[0])
    except Exception as e: print("Error Participantes:", e)

    # 2. Asignaciones C1
    print("Fetching Asignaciones C1...")
    try:
        r = s.get('https://crearpslglobal.com/admin/listar_asignaciones.php')
        dfs = pd.read_html(StringIO(r.text), flavor='lxml')
        push_to_sheet(client, sh, 'CREARPSL_ASIGNACIONES_C1', dfs[0])
    except Exception as e: print("Error Asignaciones C1:", e)

    # 3. Asignaciones C2
    print("Fetching Asignaciones C2...")
    try:
        r = s.get('https://crearpslglobal.com/admin/listar_asignacionesc2.php')
        dfs = pd.read_html(StringIO(r.text), flavor='lxml')
        push_to_sheet(client, sh, 'CREARPSL_ASIGNACIONES_C2', dfs[0])
    except Exception as e: print("Error Asignaciones C2:", e)

    # 4. Detalle Gestion
    print("Fetching Gestion Llamadas...")
    try:
        df_gestion = iterar_reporte(s, 'https://crearpslglobal.com/admin/reporte_detallegestion.php', table_index=1)
        push_to_sheet(client, sh, 'CREARPSL_GESTION', df_gestion)
    except Exception as e: print("Error Gestion:", e)

    # 5. Cierre Factura
    print("Fetching Cierre Factura...")
    try:
        df_fac = iterar_reporte(s, 'https://crearpslglobal.com/admin/reporte_cierrefactura.php', table_index=1)
        push_to_sheet(client, sh, 'CREARPSL_FACTURAS', df_fac)
    except Exception as e: print("Error Facturas:", e)

    # 6. Resultados C1
    print("Fetching Llamadas C1...")
    try:
        df_c1 = iterar_reporte(s, 'https://crearpslglobal.com/admin/resultado_llamadas.php', table_index=1)
        push_to_sheet(client, sh, 'CREARPSL_LLAMADAS_C1', df_c1)
    except Exception as e: print("Error Llamadas C1:", e)

    # 7. Resultados C2
    print("Fetching Llamadas C2...")
    try:
        df_c2 = iterar_reporte(s, 'https://crearpslglobal.com/admin/resultado_llamadasc2.php', table_index=1)
        push_to_sheet(client, sh, 'CREARPSL_LLAMADAS_C2', df_c2)
    except Exception as e: print("Error Llamadas C2:", e)
    
    print("🏁 Sincronizacion completada.")

def iniciar_thread():
    import threading
    def worker():
        while True:
            try:
                iniciar_sync()
            except Exception as e:
                print(f"Error general sync: {e}")
            time.sleep(1800)
    t = threading.Thread(target=worker, daemon=True)
    t.start()

if __name__ == "__main__":
    iniciar_sync()
