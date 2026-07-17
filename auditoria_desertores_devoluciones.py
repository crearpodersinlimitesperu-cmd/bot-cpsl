import pandas as pd
import os
import shutil

# Rutas
PATH_C1 = r'C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1'
PATH_C2 = r'C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2'

def buscar_desertores_y_devoluciones():
    equipos = range(22, 28)
    reporte = []
    
    # Archivos a procesar
    archivos = []
    for e in equipos:
        archivos.append((f"C1 E{e}", os.path.join(PATH_C1, f"ALIADOS CAPÍTULO UNO EQUIPO {e}.xlsx")))
        archivos.append((f"C2 E{e}", os.path.join(PATH_C2, f"ALIADOS C2 EQUIPO {e}.xlsx")))

    for tag, path in archivos:
        if not os.path.exists(path):
            # Intentar con nombres alternativos si falló (acentos, etc)
            continue
            
        print(f"Procesando {tag}...")
        temp_file = f"temp_{tag.replace(' ', '_')}.xlsx"
        try:
            shutil.copy2(path, temp_file)
            df = pd.read_excel(temp_file, sheet_name='PX')
            
            # Normalizar columnas
            df.columns = [str(c).strip().upper() for c in df.columns]
            
            status_col = 'STATUS' if 'STATUS' in df.columns else None
            nombre_col = 'NOMBRES' if 'NOMBRES' in df.columns else None
            apellido_col = 'APELLIDOS' if 'APELLIDOS' in df.columns else None
            motivo_col = 'MOTIVO' if 'MOTIVO' in df.columns else ('OBSERVACIONES' if 'OBSERVACIONES' in df.columns else None)

            if not status_col or not nombre_col:
                continue

            # Filtrar desertores
            df['STATUS_CLEAN'] = df[status_col].fillna('').astype(str).str.strip().str.upper()
            desertores = df[df['STATUS_CLEAN'].str.contains('DESERTOR', na=False)]
            
            for _, row in desertores.iterrows():
                nombre = f"{row.get(nombre_col, '')} {row.get(apellido_col, '')}".strip()
                motivo = row.get(motivo_col, '') if motivo_col else "N/A"
                
                # Buscar si hay mención de devolución
                es_devolucion = "SI" if "DEVOL" in str(motivo).upper() or "REEMBOL" in str(motivo).upper() else "NO"
                
                reporte.append({
                    "Equipo": tag,
                    "Nombre": nombre,
                    "Motivo": motivo,
                    "Devolucion": es_devolucion
                })
            
            os.remove(temp_file)
        except Exception as e:
            print(f"Error en {tag}: {e}")
            if os.path.exists(temp_file): os.remove(temp_file)

    return pd.DataFrame(reporte)

if __name__ == "__main__":
    df_final = buscar_desertores_y_devoluciones()
    if not df_final.empty:
        print(f"\nSe encontraron {len(df_final)} desertores en total.")
        print("\nCasos con posible DEVOLUCIÓN detectada en el Excel:")
        print(df_final[df_final['Devolucion'] == 'SI'][['Equipo', 'Nombre', 'Motivo']])
        
        # Guardar reporte completo
        df_final.to_csv("auditoria_desertores_total.csv", index=False)
        print("\nReporte completo guardado en 'auditoria_desertores_total.csv'")
    else:
        print("No se encontraron desertores en los archivos procesados.")
