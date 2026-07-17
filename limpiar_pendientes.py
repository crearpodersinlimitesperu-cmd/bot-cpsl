"""
LIMPIEZA QUIRÚRGICA DE PENDIENTES C1
=====================================
Cruza datos de IMO + Gestión_Llamadas + Cambios de Cupo
para marcar los registros NO REALES y recalcular pendientes reales.
"""
import sqlite3, pandas as pd, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "torre_control.db"
CRM_DIR = r"C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def paso_1_agregar_campo_resultado():
    """Agrega campo resultado_gestion a participantes."""
    print("PASO 1: Preparando campo resultado_gestion...")
    conn = get_db()
    try:
        conn.execute("ALTER TABLE participantes ADD COLUMN resultado_gestion TEXT DEFAULT ''")
        print("  ✅ Campo 'resultado_gestion' creado")
    except:
        print("  ⚪ Ya existe")
    try:
        conn.execute("ALTER TABLE participantes ADD COLUMN es_pendiente_real TEXT DEFAULT 'SI'")
        print("  ✅ Campo 'es_pendiente_real' creado")
    except:
        print("  ⚪ Ya existe")
    try:
        conn.execute("ALTER TABLE participantes ADD COLUMN tiene_cambio_cupo TEXT DEFAULT 'NO'")
        print("  ✅ Campo 'tiene_cambio_cupo' creado")
    except:
        print("  ⚪ Ya existe")
    conn.commit()
    conn.close()

def paso_2_inyectar_gestion_llamadas():
    """Cruza Gestion_Llamadas.xlsx con participantes por nombre+equipo."""
    print("\nPASO 2: Cruzando Gestión de Llamadas...")
    path = os.path.join(CRM_DIR, "Gestion_Llamadas.xlsx")
    if not os.path.exists(path):
        print("  ❌ No encontrado")
        return
    
    df = pd.read_excel(path, dtype=str)
    conn = get_db()
    
    actualizados = 0
    for _, row in df.iterrows():
        nombres = str(row.get('Nombres', '')).strip().upper()
        apellidos = str(row.get('Apellidos', '')).strip().upper()
        resultado = str(row.get('Ultima_Gestion', '') or row.get('Primera_Llamada', '')).strip().upper()
        
        if not nombres or not resultado:
            continue
        
        r = conn.execute(
            "UPDATE participantes SET resultado_gestion=? WHERE UPPER(TRIM(nombre)) LIKE ? AND UPPER(TRIM(apellido)) LIKE ? AND c1='NO'",
            (resultado, f"%{nombres}%", f"%{apellidos}%")
        )
        if r.rowcount > 0:
            actualizados += r.rowcount
    
    conn.commit()
    conn.close()
    print(f"  ✅ {actualizados} PX actualizados con resultado de gestión")

def paso_3_marcar_cambios_cupo():
    """Marca PX con cambio de cupo."""
    print("\nPASO 3: Marcando cambios de cupo...")
    master = pd.read_csv(os.path.join(CRM_DIR, "Master_Participantes_Limpio.csv"), dtype=str)
    cambios = master[master['Ident. Cambio Cupo'].notna() & (master['Ident. Cambio Cupo'] != '-') & (master['Ident. Cambio Cupo'].str.strip() != '')]
    
    conn = get_db()
    marcados = 0
    for _, row in cambios.iterrows():
        ident = str(row.get('Identificación', '')).strip()
        if ident:
            r = conn.execute(
                "UPDATE participantes SET tiene_cambio_cupo='SI', es_pendiente_real='NO', resultado_gestion='CAMBIO_CUPO' WHERE identificacion=? AND c1='NO'",
                (ident,)
            )
            marcados += r.rowcount
    
    conn.commit()
    conn.close()
    print(f"  ✅ {marcados} PX marcados como CAMBIO DE CUPO")

def paso_4_marcar_no_interesados():
    """Marca como NO pendiente real a los que tienen resultado NO INTERESA, DEVOLUCIÓN, etc."""
    print("\nPASO 4: Marcando no-reales por resultado de gestión...")
    conn = get_db()
    
    # Marcar los que ya tienen resultado de gestión
    resultados_no_reales = ['NO INTERESA', 'NO CONTESTAN', 'DEVOLUCIÓN', 'DEVOLACION', 'CANCELADO', 'BAJA']
    
    total_marcados = 0
    for resultado in resultados_no_reales:
        r = conn.execute(
            "UPDATE participantes SET es_pendiente_real='NO' WHERE c1='NO' AND UPPER(resultado_gestion) LIKE ?",
            (f"%{resultado}%",)
        )
        if r.rowcount > 0:
            print(f"  ✅ '{resultado}': {r.rowcount} PX marcados NO pendiente real")
            total_marcados += r.rowcount
    
    # Los desertores también
    r = conn.execute("""
        UPDATE participantes SET es_pendiente_real='NO', resultado_gestion='DESERTOR'
        WHERE c1='NO' AND id IN (
            SELECT p.id FROM participantes p
            INNER JOIN desertores d ON UPPER(TRIM(p.nombre || ' ' || p.apellido)) = UPPER(TRIM(d.nombre))
        )
    """)
    if r.rowcount > 0:
        print(f"  ✅ DESERTORES cruzados: {r.rowcount} PX marcados NO pendiente real")
        total_marcados += r.rowcount
    
    # Los graduados mal clasificados (c1=NO pero maestria=SI o c2=SI) - forzar corrección
    r2 = conn.execute("UPDATE participantes SET c1='SI', es_pendiente_real='NO' WHERE c1='NO' AND (c2='SI' OR maestria='SI')")
    if r2.rowcount > 0:
        print(f"  ✅ Graduados mal clasificados: {r2.rowcount} PX corregidos c1→SI")
    
    conn.commit()
    
    # REPORTE FINAL
    print("\n" + "=" * 60)
    print("REPORTE DE PENDIENTES C1")
    print("=" * 60)
    
    total_c1_no = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO'").fetchone()[0]
    reales = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI'").fetchone()[0]
    no_reales = conn.execute("SELECT COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='NO'").fetchone()[0]
    
    print(f"\n  Total C1=NO:          {total_c1_no}")
    print(f"  ✅ PENDIENTES REALES: {reales}")
    print(f"  ❌ NO REALES:         {no_reales}")
    
    print(f"\n  Desglose NO REALES:")
    for row in conn.execute("SELECT resultado_gestion, COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='NO' GROUP BY resultado_gestion ORDER BY COUNT(*) DESC"):
        print(f"    {row[0] or '(sin resultado)'}: {row[1]}")
    
    print(f"\n  Desglose REALES por resultado:")
    for row in conn.execute("SELECT resultado_gestion, COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI' GROUP BY resultado_gestion ORDER BY COUNT(*) DESC"):
        print(f"    {row[0] or 'SIN GESTIONAR'}: {row[1]}")
    
    print(f"\n  Pendientes REALES por CC:")
    for row in conn.execute("SELECT cc_nombre, COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI' GROUP BY cc_nombre ORDER BY COUNT(*) DESC"):
        print(f"    {row[0] or '(vacío)'}: {row[1]}")
    
    print(f"\n  Pendientes REALES por Equipo:")
    for row in conn.execute("SELECT equipo, COUNT(*) FROM participantes WHERE c1='NO' AND es_pendiente_real='SI' GROUP BY equipo ORDER BY COUNT(*) DESC"):
        print(f"    {row[0]}: {row[1]}")
    
    # Registrar en caja negra
    from datetime import datetime
    conn.execute("""
        INSERT INTO caja_negra (timestamp, tipo, accion, detalle, canal, px_nombre, px_telefono, resultado)
        VALUES (?, 'LIMPIEZA', 'PURGA_PENDIENTES', ?, '', '', '', 'OK')
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), f"Pendientes reales: {reales}/{total_c1_no}. Descartados: {no_reales} (NO INTERESA, NC, CAMBIO CUPO, DESERTORES)"))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    paso_1_agregar_campo_resultado()
    paso_2_inyectar_gestion_llamadas()
    paso_3_marcar_cambios_cupo()
    paso_4_marcar_no_interesados()
