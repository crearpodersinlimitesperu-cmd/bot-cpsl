import pandas as pd
import os
import glob
import sqlite3

print("--- 1. ANALISIS DE EXCEL C1 ---")
path_c1 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C1\ALIADOS CAPÍTULO UNO EQUIPO 27.xlsx"
try:
    df_c1 = pd.read_excel(path_c1)
    print("Columnas C1:", df_c1.columns.tolist())
    print(df_c1.head(2))
except Exception as e:
    print("Error leyendo C1:", e)

print("\n--- 2. ANALISIS DE EXCEL C2 ---")
path_c2 = r"C:\Users\josem\OneDrive - QUANTUM COACHING TECHNOLOGY BVS CIA. LTDA\CREAR LIMA\PORCENTAJE ALIADOS C2\ALIADOS C2 EQUIPO 26.xlsx"
try:
    df_c2 = pd.read_excel(path_c2)
    print("Columnas C2:", df_c2.columns.tolist())
    print(df_c2.head(2))
except Exception as e:
    print("Error leyendo C2:", e)

print("\n--- 3. REVISANDO ESTADO DE ZULEY ---")
try:
    conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db')
    zuley_df = pd.read_sql_query("SELECT id, nombre, apellido, cc_nombre, estado, resultado_gestion FROM participantes WHERE cc_nombre LIKE '%zuley%' LIMIT 10", conn)
    print(f"Total casos Zuley (muestra de 10):\n{zuley_df}")
    
    # Check total count
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM participantes WHERE cc_nombre LIKE '%zuley%'")
    print(f"Total casos asignados a Zuley en DB: {cursor.fetchone()[0]}")
    conn.close()
except Exception as e:
    print("Error BD Zuley:", e)
