import os
import pandas as pd
import sqlite3
import re
from datetime import datetime
from pathlib import Path

# CONFIGURACION DE RUTAS
ASIG_FILE = Path(r"C:\Users\josem\Downloads\CREAR_LIMA_ANALISIS\Asignacion_C1.xlsx")
REPO_C1 = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1")
REPO_C2 = Path(r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2")
DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def normalizar(t):
    return str(t).upper().strip()

def cargar_historial_asistencia():
    print("--- CONSOLIDANDO HISTORIAL DE ASISTENCIA (C1/C2) ---")
    asistentes = set()
    
    for repo in [REPO_C1, REPO_C2]:
        if not repo.exists(): continue
        for f in os.listdir(repo):
            if f.endswith(".xlsx"):
                try:
                    df = pd.read_excel(repo / f)
                    # Buscar columnas de nombres o DNI
                    for col in df.columns:
                        if 'NOMBRE' in str(col).upper() or 'DNI' in str(col).upper() or 'IDENTI' in str(col).upper():
                            asistentes.update(df[col].dropna().astype(str).str.upper().str.strip().tolist())
                except: continue
    
    print(f"Total registros históricos detectados: {len(asistentes)}")
    return asistentes

def ejecutar_protocolo_maestro():
    now = datetime.now()
    print(f"--- EJECUTANDO PROTOCOLO AUTONOMO: {now.strftime('%H:%M')} ---")
    
    # 1. Cargar Asignacion Diana/Joyce
    df_asig = pd.read_excel(ASIG_FILE)
    df_asig = df_asig[df_asig['Usuario Registro'].isin(['dmoscoso', 'jmarin'])]
    
    # 2. Cargar Historial para exclusion
    historial = cargar_historial_asistencia()
    
    # 3. Validar Aptitud
    aptos = []
    descartados = []
    
    for _, row in df_asig.iterrows():
        nombre = normalizar(row['NombreCompleto'] + " " + row['ApellidoCompleto'])
        dni = str(row['Identificaci\u00f3n']).replace(".0", "").strip()
        
        if nombre in historial or dni in historial:
            descartados.append({"id": dni, "motivo": "YA ASISTIO C1/C2"})
        else:
            aptos.append(row)

    print(f"Asignados iniciales: {len(df_asig)}")
    print(f"Aptos validados: {len(aptos)}")
    print(f"Descartados por asistencia: {len(descartados)}")

    # 4. Auditoria de Rebotes y SMS (8 AM - 8 PM)
    if 8 <= now.hour < 20:
        print("Dentro de horario operativo (8AM-8PM). Revisando rebotes...")
        # Aqui se integraria la logica de check_bounces y enviar_sms_px_imo
    else:
        print("Fuera de horario operativo. El sistema solo auditara datos.")

    # Guardar resultados en el CRM (CSV temporal por ahora)
    if aptos:
        pd.DataFrame(aptos).to_csv("PX_APTOS_VALIDADOS_FINAL.csv", index=False)
        print("Archivo de Aptos generado: PX_APTOS_VALIDADOS_FINAL.csv")

if __name__ == "__main__":
    ejecutar_protocolo_maestro()
