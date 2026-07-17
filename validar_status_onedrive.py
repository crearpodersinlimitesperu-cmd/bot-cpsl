import os
import glob
import re
import time
import pandas as pd

# Normalización de nombres (según la documentación de CREAR)
def norm(name):
    if pd.isna(name):
        return ""
    n = str(name).upper().strip()
    for a, b in [("Á","A"),("É","E"),("Í","I"),("Ó","O"),("Ú","U")]:
        n = n.replace(a, b)
    return re.sub(r'\s+', ' ', n)

def ejecutar_auditoria():
    print(f"=== INICIANDO AUDITORÍA AUTOMÁTICA DE STATUS ONEDRIVE: {time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    dir_c1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1"
    dir_c2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2"

    files_c1 = glob.glob(os.path.join(dir_c1, "*.xlsx"))
    files_c2 = glob.glob(os.path.join(dir_c2, "*.xlsx"))

    print(f"Archivos C1 en OneDrive: {len(files_c1)}")
    print(f"Archivos C2 en OneDrive: {len(files_c2)}")

    onedrive_px = {}

    def procesar_carpeta(files, capitulo):
        for fpath in files:
            fname = os.path.basename(fpath)
            # Ignorar archivos temporales de Excel
            if fname.startswith("~$"):
                continue
            try:
                xls = pd.ExcelFile(fpath)
                for sheet in xls.sheet_names:
                    df = pd.read_excel(fpath, sheet_name=sheet)
                    
                    # Normalizar nombres de columnas a mayúsculas
                    cols = [str(c).strip().upper() for c in df.columns]
                    df.columns = cols
                    
                    col_nombre = None
                    col_apellido = None
                    col_status = None
                    
                    # Identificar columnas de nombres y estados
                    for col in cols:
                        c_low = col.lower()
                        if "nombre" in c_low or "px" in c_low or "participante" in c_low:
                            if not col_nombre: col_nombre = col
                        elif "apellido" in c_low:
                            if not col_apellido: col_apellido = col
                        elif "status" in c_low or "estado" in c_low or "resultado" in c_low:
                            if not col_status: col_status = col
                    
                    for idx, row in df.iterrows():
                        n = str(row.get(col_nombre, "")).strip() if col_nombre else ""
                        a = str(row.get(col_apellido, "")).strip() if col_apellido else ""
                        status = str(row.get(col_status, "")).strip() if col_status else ""
                        
                        # Respaldo si no hay columnas explícitas
                        if not n and not a:
                            parts = [str(x).strip() for x in row.values if pd.notnull(x) and isinstance(x, str) and len(str(x).strip()) > 2]
                            if len(parts) >= 2:
                                n = parts[0]
                                a = " ".join(parts[1:])
                        
                        if not n:
                            continue
                            
                        nombre_completo = (n + " " + a).strip()
                        key = norm(nombre_completo)
                        
                        if len(key) < 5:
                            continue
                            
                        info = {
                            "Nombre_OneDrive": nombre_completo,
                            "Status_OneDrive": status,
                            "Origen_Archivo": fname,
                            "Pestaña": sheet,
                            "Capitulo": capitulo
                        }
                        
                        # Si ya está registrado, dar preferencia a estados que representen inactividad (deserción)
                        if key in onedrive_px:
                            prev_status = str(onedrive_px[key]["Status_OneDrive"]).upper()
                            new_status = status.upper()
                            if any(x in new_status for x in ["DESERTOR", "DEVOLUCION", "SENTADO", "RETIRADO", "NO"]):
                                onedrive_px[key] = info
                        else:
                            onedrive_px[key] = info
            except Exception as e:
                print(f"Error procesando archivo C1/C2 '{fname}' en pestaña '{sheet if 'sheet' in locals() else 'N/A'}': {e}")

    # Procesar ambas carpetas en todas sus pestañas
    procesar_carpeta(files_c1, "C1")
    procesar_carpeta(files_c2, "C2")

    print(f"Total participantes únicos procesados en OneDrive: {len(onedrive_px)}")

    # Listas maestras locales para contrastar
    prod_path = r"C:\Users\josem\Downloads\productividad_coordinador.xlsx"
    rep_path = r"C:\Users\josem\Downloads\reporte_equipos.xlsx"

    discrepancias = []

    # 1. Validar contra productividad_coordinador.xlsx
    if os.path.exists(prod_path):
        print("Auditando contra productividad_coordinador.xlsx...")
        try:
            xls_prod = pd.ExcelFile(prod_path)
            for sheet in xls_prod.sheet_names:
                df_prod = pd.read_excel(prod_path, sheet_name=sheet)
                for idx, row in df_prod.iterrows():
                    nom = str(row.get("NombreCompleto", "")).strip()
                    ape = str(row.get("ApellidoCompleto", "")).strip()
                    if not nom and not ape:
                        nom = str(row.get("Nombre", "")).strip()
                        ape = str(row.get("Apellido", "")).strip()
                    
                    nombre_master = (nom + " " + ape).strip()
                    key_master = norm(nombre_master)
                    
                    if key_master in onedrive_px:
                        px_od = onedrive_px[key_master]
                        status_od = px_od["Status_OneDrive"].upper()
                        asistencia_master = str(row.get("Asistencia", "")).upper()
                        gestion_master = str(row.get("Resultado Gestión", "")).upper()
                        
                        es_des_od = any(x in status_od for x in ["DESERTOR", "DEVOLUCION", "RETIRADO", "NO", "SENTADO"])
                        es_des_master = any(x in asistencia_master or x in gestion_master for x in ["DESERTOR", "DEVOLUCION", "RETIRADO", "RETIRAR", "EXCLUIDO"])
                        
                        if es_des_od and not es_des_master:
                            discrepancias.append({
                                "Participante": nombre_master,
                                "DNI": row.get("ClienteId", ""),
                                "Fuente_Master": f"Productividad - {sheet}",
                                "Status_Master": f"Asist: {row.get('Asistencia', 'VACÍA')} / Gest: {row.get('Resultado Gestión', 'VACÍA')}",
                                "Status_OneDrive": px_od["Status_OneDrive"],
                                "Archivo_OneDrive": px_od["Origen_Archivo"],
                                "Pestaña_OneDrive": px_od["Pestaña"],
                                "Capítulo": px_od["Capitulo"],
                                "Detalle_Alerta": "Marcado como inactivo/desertor en OneDrive pero activo en Productividad"
                            })
        except Exception as e_prod:
            print(f"Error al leer archivo de productividad: {e_prod}")

    # 2. Validar contra reporte_equipos.xlsx
    if os.path.exists(rep_path):
        print("Auditando contra reporte_equipos.xlsx...")
        try:
            xls_rep = pd.ExcelFile(rep_path)
            for sheet in xls_rep.sheet_names:
                if sheet in ["25", "26", "27", "28"]:
                    df_rep = pd.read_excel(rep_path, sheet_name=sheet)
                    for idx, row in df_rep.iterrows():
                        nom = str(row.get("NombreCompleto", "")).strip()
                        ape = str(row.get("ApellidoCompleto", "")).strip()
                        
                        nombre_master = (nom + " " + ape).strip()
                        key_master = norm(nombre_master)
                        
                        if key_master in onedrive_px:
                            px_od = onedrive_px[key_master]
                            status_od = px_od["Status_OneDrive"].upper()
                            asistencia_master = str(row.get("Asistencia", "")).upper()
                            
                            es_des_od = any(x in status_od for x in ["DESERTOR", "DEVOLUCION", "RETIRADO", "NO", "SENTADO"])
                            es_des_master = any(x in asistencia_master for x in ["DESERTOR", "DEVOLUCION", "RETIRADO", "RETIRAR"])
                            
                            if es_des_od and not es_des_master:
                                discrepancias.append({
                                    "Participante": nombre_master,
                                    "DNI": row.get("Identificación", ""),
                                    "Fuente_Master": f"Reporte Equipos - {sheet}",
                                    "Status_Master": f"Asist: {row.get('Asistencia', 'VACÍA')}",
                                    "Status_OneDrive": px_od["Status_OneDrive"],
                                    "Archivo_OneDrive": px_od["Origen_Archivo"],
                                    "Pestaña_OneDrive": px_od["Pestaña"],
                                    "Capítulo": px_od["Capitulo"],
                                    "Detalle_Alerta": "Marcado como inactivo/desertor en OneDrive pero activo en Reporte Equipos"
                                })
        except Exception as e_rep:
            print(f"Error al leer archivo de reporte equipos: {e_rep}")

    # Guardar reporte de discrepancias en Excel
    df_disc = pd.DataFrame(discrepancias)
    output_reporte = r"C:\Users\josem\Downloads\Discrepancias_Status_OneDrive.xlsx"
    try:
        df_disc.to_excel(output_reporte, index=False)
        print(f"Reporte de discrepancias generado con éxito: {len(df_disc)} discrepancias en {output_reporte}")
    except Exception as e_out:
        print(f"Error al escribir el reporte de discrepancias: {e_out}")

    # Actualizar la lista local de exclusiones (Excluidos_OneDrive_C1_C2.csv)
    excluidos_onedrive = []
    for key, px in onedrive_px.items():
        status_upper = str(px["Status_OneDrive"]).upper()
        if any(x in status_upper for x in ["DESERTOR", "DEVOLUCION", "SENTADO", "RETIRADO", "NO"]):
            excluidos_onedrive.append({
                "NombreCompleto": px["Nombre_OneDrive"],
                "Status_OneDrive": px["Status_OneDrive"],
                "Fuente": px["Origen_Archivo"]
            })
            
    df_excluidos = pd.DataFrame(excluidos_onedrive)
    excluidos_path = r"C:\Users\josem\Downloads\bot-cpsl-review\Excluidos_OneDrive_C1_C2.csv"
    try:
        df_excluidos.to_csv(excluidos_path, index=False, encoding='utf-8-sig')
        print(f"Archivo de exclusiones actualizado en: {excluidos_path} ({len(df_excluidos)} registros)")
    except Exception as e_excl:
        print(f"Error al guardar el archivo de exclusiones: {e_excl}")

    print("=== AUDITORÍA FINALIZADA ===\n")

if __name__ == "__main__":
    ejecutar_auditoria()
