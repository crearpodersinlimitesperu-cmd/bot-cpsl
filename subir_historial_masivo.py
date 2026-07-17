import os, json, time, logging
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Configuración
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("Sync_Masivo")

CREDS_PATH = r"C:\Users\josem\Downloads\bot-cpsl-review\credenciales.json"
SHEET_ID = "1NqEgzCkixVhMn3VLhsy_GVWwYBfwLQ1rwdHVcKTRyjo"
EXCEL_PATH = r"C:\Users\josem\Downloads\Asignacion_C1.xlsx"

def main():
    if not os.path.exists(CREDS_PATH):
        log.error(f"Credenciales no encontradas en {CREDS_PATH}")
        return

    log.info("Autenticando con Google Sheets...")
    creds = service_account.Credentials.from_service_account_file(
        CREDS_PATH, scopes=['https://www.googleapis.com/auth/spreadsheets'])
    service = build('sheets', 'v4', credentials=creds)

    # Verificar si la pestaña existe, si no, crearla
    spreadsheet = service.spreadsheets().get(spreadsheetId=SHEET_ID).execute()
    sheet_names = [s['properties']['title'] for s in spreadsheet['sheets']]
    
    if "LOG_INTERACCIONES" not in sheet_names:
        log.info("Creando pestaña 'LOG_INTERACCIONES'...")
        body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': 'LOG_INTERACCIONES'
                    }
                }
            }]
        }
        service.spreadsheets().batchUpdate(spreadsheetId=SHEET_ID, body=body).execute()
        # Agregar encabezados
        headers = [["Fecha", "Direccion", "Telefono", "Nombre", "Tipo", "Staff", "Mensaje", "Evento", "Estado"]]
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID, range="LOG_INTERACCIONES!A1",
            valueInputOption="RAW", body={'values': headers}
        ).execute()
    df = pd.read_excel(EXCEL_PATH)
    df_filtrado = df[df['Usuario Registro'].isin(['jmarin', 'dmoscoso'])]
    
    rows = []
    fecha_envio = "03/05/2026 14:00:00" # Hora aproximada del envío
    mensaje_template = "¡Hola! Soy el asistente virtual de Crear Lima... reactivar tu entrenamiento... Equipo 28... (Plantilla reactivacion_c1_e28)"
    
    log.info(f"Preparando {len(df_filtrado)} filas...")
    
    for idx, row in df_filtrado.iterrows():
        tel = str(row.get('TelefonoMovil', '')).strip()
        if not tel.startswith("51"): tel = "51" + tel
        
        nombre = str(row.get('NombreCompleto', ''))
        staff = "Diana" if row['Usuario Registro'] == 'dmoscoso' else "Joyce"
        
        rows.append([
            fecha_envio,
            "SALIDA",
            tel,
            nombre,
            "PX",
            staff,
            mensaje_template,
            "C1 E28",
            "ENVIADO"
        ])

    # Subir en bloques de 100 para evitar errores
    batch_size = 100
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        body = {'values': batch}
        try:
            service.spreadsheets().values().append(
                spreadsheetId=SHEET_ID,
                range="LOG_INTERACCIONES!A:I",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body
            ).execute()
            log.info(f"✅ Bloque {i//batch_size + 1} subido ({len(batch)} filas)")
        except Exception as e:
            log.error(f"❌ Error subiendo bloque {i//batch_size + 1}: {e}")

    log.info("--- SINCRONIZACIÓN FINALIZADA ---")

if __name__ == "__main__":
    main()
