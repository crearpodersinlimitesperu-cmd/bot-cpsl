"""
INTEGRADOR MAESTRO — Torre de Control CPSL Lima
================================================
Enriquece la DB SQLite con:
1. Verificación RENIEC (1,278 DNIs)
2. IMOs enroladores + teléfonos
3. Trayectoria y rangos históricos
4. Asignación de CC a los 1,921 huérfanos
5. Cascada de coherencia lógica
"""
import sqlite3
import pandas as pd
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = os.path.join(os.path.dirname(__file__), "torre_control.db")
CRM_DIR = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA"

# Mapeo oficial CC por Equipo (de full_derivaciones_cc.py)
CC_POR_EQUIPO = {
    "EQUIPO 27": "Joyce Marín",
    "EQUIPO 26": "Diana Moscoso",
    "EQUIPO 25": "Joyce Marín",
    "EQUIPO 24": "Diana Moscoso",
    "EQUIPO 23": "Joyce Marín",
    "EQUIPO 22": "Joyce Marín",
    "EQUIPO 21": "Joyce Marín",
    "EQUIPO 20": "Joyce Marín",
    "EQUIPO 19": "Diana Moscoso",
    "EQUIPO 18": "Diana Moscoso",
    "EQUIPO 17": "Diana Moscoso",
    "EQUIPO 16": "Diana Moscoso",
    "EQUIPO 15": "Diana Moscoso",
    "EQUIPO 14": "Diana Moscoso",
}

# Teléfonos oficiales de las CC
CC_TELEFONOS = {
    "Diana Moscoso": "51912379744",
    "Joyce Marín": "51991765740",
    "Zuley Urteaga": "51999888777",
}

def clean_phone(val):
    s = str(val).strip()
    if s in ('nan', 'None', 'NaN', ''): return ''
    try:
        n = int(float(s))
        return str(n)
    except:
        return re.sub(r'[^\d]', '', s)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def paso_1_agregar_columnas():
    """Agrega las columnas nuevas a la tabla participantes."""
    print("=" * 60)
    print("PASO 1: Agregando columnas nuevas a la DB")
    print("=" * 60)
    
    conn = get_db()
    nuevas = [
        ("reniec_nombres", "TEXT DEFAULT ''"),
        ("reniec_paterno", "TEXT DEFAULT ''"),
        ("reniec_materno", "TEXT DEFAULT ''"),
        ("verificado_reniec", "TEXT DEFAULT 'NO'"),
        ("max_rango", "TEXT DEFAULT ''"),
        ("historial_trayectoria", "TEXT DEFAULT ''"),
    ]
    
    for col_name, col_type in nuevas:
        try:
            conn.execute(f"ALTER TABLE participantes ADD COLUMN {col_name} {col_type}")
            print(f"  ✅ Columna '{col_name}' agregada")
        except sqlite3.OperationalError:
            print(f"  ⚪ Columna '{col_name}' ya existe")
    
    conn.commit()
    conn.close()

def paso_2_inyectar_reniec():
    """Cruza Mineria_DNIs.xlsx con participantes por DNI."""
    print("\n" + "=" * 60)
    print("PASO 2: Inyectando datos RENIEC (1,278 verificados)")
    print("=" * 60)
    
    mineria_path = os.path.join(CRM_DIR, "Mineria_DNIs.xlsx")
    if not os.path.exists(mineria_path):
        print("  ❌ No se encontró Mineria_DNIs.xlsx")
        return
    
    df_min = pd.read_excel(mineria_path, dtype=str)
    verificados = df_min[df_min['Estatus'] == 'VERIFICADO']
    print(f"  📊 {len(verificados)} DNIs verificados para cruzar")
    
    conn = get_db()
    actualizados = 0
    
    for _, row in verificados.iterrows():
        dni = str(row['DNI']).strip()
        reniec_nom = str(row.get('RENIEC_Nombres', '')).strip()
        reniec_pat = str(row.get('RENIEC_Paterno', '')).strip()
        reniec_mat = str(row.get('RENIEC_Materno', '')).strip()
        
        if not dni or dni == 'nan':
            continue
        
        # Buscar PX por identificación (DNI)
        result = conn.execute(
            "UPDATE participantes SET reniec_nombres=?, reniec_paterno=?, reniec_materno=?, verificado_reniec='SI' WHERE identificacion=?",
            (reniec_nom, reniec_pat, reniec_mat, dni)
        )
        if result.rowcount > 0:
            actualizados += result.rowcount
    
    conn.commit()
    conn.close()
    print(f"  ✅ {actualizados} participantes enriquecidos con RENIEC")

def paso_3_inyectar_imo_trayectoria():
    """Cruza Master_Participantes_Limpio.csv para IMO, trayectoria y rangos."""
    print("\n" + "=" * 60)
    print("PASO 3: Inyectando IMOs, trayectoria y rangos")
    print("=" * 60)
    
    master_path = os.path.join(CRM_DIR, "Master_Participantes_Limpio.csv")
    if not os.path.exists(master_path):
        print("  ❌ No se encontró Master_Participantes_Limpio.csv")
        return
    
    df = pd.read_csv(master_path, dtype=str)
    print(f"  📊 {len(df)} registros en Master Limpio")
    print(f"  📊 {len(df['IMO'].dropna().unique())} IMOs únicos")
    
    conn = get_db()
    imo_updated = 0
    tray_updated = 0
    
    for _, row in df.iterrows():
        identificacion = str(row.get('Identificación', '')).strip()
        if not identificacion or identificacion == 'nan':
            continue
        
        # IMO y Tel IMO
        imo = str(row.get('IMO', '')).strip()
        tel_imo = clean_phone(row.get('Tel. IMO', ''))
        rango = str(row.get('Max Rango Historico', '')).strip()
        trayectoria = str(row.get('Historial Trayectoria', '')).strip()
        
        updates = []
        params = []
        
        if imo and imo != 'nan':
            updates.append("imo=?")
            params.append(imo)
        if tel_imo:
            updates.append("tel_imo=?")
            params.append(tel_imo)
        if rango and rango != 'nan':
            updates.append("max_rango=?")
            params.append(rango)
        if trayectoria and trayectoria != 'nan':
            updates.append("historial_trayectoria=?")
            params.append(trayectoria)
        
        if updates:
            params.append(identificacion)
            sql = f"UPDATE participantes SET {', '.join(updates)} WHERE identificacion=?"
            result = conn.execute(sql, params)
            if result.rowcount > 0:
                if imo and imo != 'nan':
                    imo_updated += result.rowcount
                if trayectoria and trayectoria != 'nan':
                    tray_updated += result.rowcount
    
    conn.commit()
    conn.close()
    print(f"  ✅ {imo_updated} PX con IMO enrolador actualizado")
    print(f"  ✅ {tray_updated} PX con trayectoria inyectada")

def paso_4_asignar_cc_huerfanos():
    """Asigna CC a los 1,921 PX sin coordinadora usando el mapeo por equipo."""
    print("\n" + "=" * 60)
    print("PASO 4: Asignando CC a PX huérfanos por equipo")
    print("=" * 60)
    
    conn = get_db()
    
    # Contar huérfanos antes
    antes = conn.execute("SELECT COUNT(*) FROM participantes WHERE cc_nombre IS NULL OR cc_nombre=''").fetchone()[0]
    print(f"  📊 PX sin CC antes: {antes}")
    
    total_asignados = 0
    for equipo, cc in CC_POR_EQUIPO.items():
        tel_cc = CC_TELEFONOS.get(cc, '')
        result = conn.execute(
            "UPDATE participantes SET cc_nombre=?, cc_tel=?, cc_asignada=? WHERE equipo=? AND (cc_nombre IS NULL OR cc_nombre='')",
            (cc, tel_cc, cc.split()[0].upper(), equipo)
        )
        if result.rowcount > 0:
            print(f"  ✅ {equipo} → {cc}: {result.rowcount} PX asignados")
            total_asignados += result.rowcount
    
    # Verificar cuántos quedan sin CC
    despues = conn.execute("SELECT COUNT(*) FROM participantes WHERE cc_nombre IS NULL OR cc_nombre=''").fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"\n  📊 Total asignados: {total_asignados}")
    print(f"  📊 PX sin CC después: {despues}")
    print(f"  📊 Reducción: {antes} → {despues} ({antes - despues} asignados)")

def paso_5_cascada_coherencia():
    """Aplica la cascada de coherencia lógica: Graduado → MJ → C2 → C1."""
    print("\n" + "=" * 60)
    print("PASO 5: Cascada de Coherencia Lógica")
    print("=" * 60)
    
    conn = get_db()
    
    # Si tiene C2=SI, debe tener C1=SI
    r1 = conn.execute("UPDATE participantes SET c1='SI' WHERE c2='SI' AND c1='NO'")
    print(f"  ✅ C2=SI → C1=SI forzado: {r1.rowcount} PX")
    
    # Si tiene maestria=SI, debe tener C1=SI y C2=SI
    r2 = conn.execute("UPDATE participantes SET c1='SI', c2='SI' WHERE maestria='SI' AND (c1='NO' OR c2='NO')")
    print(f"  ✅ MJ=SI → C1+C2=SI forzado: {r2.rowcount} PX")
    
    # Actualizar estado a ACTIVO si C1=SI
    r3 = conn.execute("UPDATE participantes SET estado='ACTIVO' WHERE c1='SI' AND estado='PENDIENTE'")
    print(f"  ✅ Estado ACTIVO actualizado: {r3.rowcount} PX")
    
    conn.commit()
    conn.close()

def paso_6_registrar_integracion():
    """Registra la integración en la Caja Negra."""
    print("\n" + "=" * 60)
    print("PASO 6: Registrando en Caja Negra")
    print("=" * 60)
    
    conn = get_db()
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Stats finales
    total = conn.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
    con_cc = conn.execute("SELECT COUNT(*) FROM participantes WHERE cc_nombre != '' AND cc_nombre IS NOT NULL").fetchone()[0]
    con_reniec = conn.execute("SELECT COUNT(*) FROM participantes WHERE verificado_reniec='SI'").fetchone()[0]
    con_imo = conn.execute("SELECT COUNT(*) FROM participantes WHERE imo != '' AND imo IS NOT NULL AND imo != 'nan'").fetchone()[0]
    
    conn.execute("""
        INSERT INTO caja_negra (timestamp, tipo, accion, detalle, canal, px_nombre, px_telefono, resultado)
        VALUES (?, 'INTEGRACION', 'ENRIQUECIMIENTO_TOTAL', ?, '', '', '', 'OK')
    """, (now, f"Integración Ecosistema: {con_reniec} RENIEC, {con_imo} IMOs, {con_cc}/{total} con CC"))
    
    conn.commit()
    
    print(f"\n{'='*60}")
    print(f"  INTEGRACIÓN COMPLETADA")
    print(f"{'='*60}")
    print(f"  Total PX:           {total}")
    print(f"  Con CC asignada:    {con_cc} ({con_cc*100//total}%)")
    print(f"  Con RENIEC:         {con_reniec}")
    print(f"  Con IMO enrolador:  {con_imo}")
    
    # Distribución CC final
    print(f"\n  Distribución CC final:")
    for row in conn.execute("SELECT cc_nombre, COUNT(*) as cnt FROM participantes GROUP BY cc_nombre ORDER BY cnt DESC").fetchall():
        print(f"    {row[0] or '(vacío)'}: {row[1]}")
    
    conn.close()

if __name__ == "__main__":
    paso_1_agregar_columnas()
    paso_2_inyectar_reniec()
    paso_3_inyectar_imo_trayectoria()
    paso_4_asignar_cc_huerfanos()
    paso_5_cascada_coherencia()
    paso_6_registrar_integracion()
