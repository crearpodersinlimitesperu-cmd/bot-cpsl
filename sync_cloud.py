import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import os
import json

# CONFIGURACIÓN MAESTRA
SHEET_ID = "1IoCYs1qfOTdn3XWyeK64jsUfAXOFgv3Wa6uJBM-lR2Y"
HIST_COLS = ['Fecha','Hora','Coordinadora','Seccion','Estado','Cantidad','Raw']

def conectar_sheets():
    """Conexión a Google Sheets. Soporta credenciales.json local o env var GOOGLE_CREDENTIALS."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    try:
        # Opción 1: Variable de entorno (Render)
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if creds_json:
            info = json.loads(creds_json)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(info, scope)
            return gspread.authorize(creds)
        # Opción 2: Archivo local
        if os.path.exists("credenciales.json"):
            creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
            return gspread.authorize(creds)
        return None
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        return None

def _get_hist_worksheet(client):
    """Obtiene o crea la pestaña HISTORIAL en el Sheets."""
    sh = client.open_by_key(SHEET_ID)
    try:
        return sh.worksheet("HISTORIAL")
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(title="HISTORIAL", rows="5000", cols="10")
        ws.update('A1:G1', [HIST_COLS])
        return ws

def load_history_cloud():
    """Carga el historial de reportes desde Google Sheets."""
    client = conectar_sheets()
    if not client:
        return pd.DataFrame(columns=HIST_COLS)
    try:
        ws = _get_hist_worksheet(client)
        data = ws.get_all_records()
        if data:
            df = pd.DataFrame(data)
            for col in HIST_COLS:
                if col not in df.columns:
                    df[col] = ""
            return df[HIST_COLS]
        return pd.DataFrame(columns=HIST_COLS)
    except Exception as e:
        print(f"❌ Error cargando historial cloud: {e}")
        return pd.DataFrame(columns=HIST_COLS)

def save_history_cloud(df_hist):
    """Guarda el historial completo en Google Sheets (pestaña HISTORIAL)."""
    client = conectar_sheets()
    if not client:
        return False
    try:
        ws = _get_hist_worksheet(client)
        ws.clear()
        if df_hist.empty:
            ws.update('A1:G1', [HIST_COLS])
        else:
            df_out = df_hist[HIST_COLS].fillna("").astype(str)
            ws.update([HIST_COLS] + df_out.values.tolist())
        return True
    except Exception as e:
        print(f"❌ Error guardando historial cloud: {e}")
        return False

def sincronizar_mineria_a_cloud(archivo_excel="Mineria_DNIs.xlsx"):
    """Sube los datos minados de RENIEC a la pestaña 'MINERIA' del Sheets."""
    client = conectar_sheets()
    if not client: return
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("MINERIA")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title="MINERIA", rows="1000", cols="20")
        if os.path.exists(archivo_excel):
            df = pd.read_excel(archivo_excel).fillna("")
            ws.clear()
            ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        print(f"❌ Error sincronizando minería: {e}")

def sincronizar_productividad_a_cloud(archivo_excel="Productividad_Web.xlsx"):
    """Sube los datos de Productividad a la pestaña 'PRODUCTIVIDAD' del Sheets."""
    client = conectar_sheets()
    if not client: return
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("PRODUCTIVIDAD")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title="PRODUCTIVIDAD", rows="1000", cols="20")
        if os.path.exists(archivo_excel):
            df = pd.read_excel(archivo_excel).fillna("")
            # Subir data nueva
            ws.clear()
            ws.update([df.columns.values.tolist()] + df.values.tolist())
            print(f"✅ Sincronizados {len(df)} registros de Productividad a la nube.")
    except Exception as e:
        print(f"❌ Error sincronizando productividad: {e}")

def sincronizar_asignaciones_a_cloud(archivo_excel="Asignaciones_Web.xlsx"):
    """Sube los datos de Asignaciones a la pestaña 'ASIGNACIONES' del Sheets."""
    client = conectar_sheets()
    if not client: return
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("ASIGNACIONES")
        except gspread.exceptions.WorksheetNotFound:
            ws = sh.add_worksheet(title="ASIGNACIONES", rows="2000", cols="20")
        if os.path.exists(archivo_excel):
            df = pd.read_excel(archivo_excel).fillna("")
            ws.clear()
            ws.update([df.columns.values.tolist()] + df.values.tolist())
            print(f"✅ Sincronizados {len(df)} registros de Asignaciones a la nube.")
    except Exception as e:
        print(f"❌ Error sincronizando asignaciones: {e}")

def actualizar_dato_maestro(dni, columna, nuevo_valor):
    """Edita una celda específica en el Master de Google Sheets."""
    client = conectar_sheets()
    if not client: return
    try:
        sh = client.open_by_key(SHEET_ID)
        ws = sh.get_worksheet(0)
        celda = ws.find(str(dni))
        if celda:
            headers = ws.row_values(1)
            if columna in headers:
                col_idx = headers.index(columna) + 1
                ws.update_cell(celda.row, col_idx, nuevo_valor)
    except Exception as e:
        print(f"❌ Error actualizando Sheets: {e}")

def load_productividad_cloud():
    """Carga los datos de PRODUCTIVIDAD desde Google Sheets."""
    client = conectar_sheets()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("PRODUCTIVIDAD")
            data = ws.get_all_records()
            if data:
                return pd.DataFrame(data)
        except gspread.exceptions.WorksheetNotFound:
            pass
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error cargando productividad cloud: {e}")
        return pd.DataFrame()

def load_asignaciones_cloud():
    """Carga los datos de ASIGNACIONES desde Google Sheets."""
    client = conectar_sheets()
    if not client: return pd.DataFrame()
    try:
        sh = client.open_by_key(SHEET_ID)
        try:
            ws = sh.worksheet("ASIGNACIONES")
            data = ws.get_all_records()
            if data:
                return pd.DataFrame(data)
        except gspread.exceptions.WorksheetNotFound:
            pass
        return pd.DataFrame()
    except Exception as e:
        print(f"❌ Error cargando asignaciones cloud: {e}")
        return pd.DataFrame()

