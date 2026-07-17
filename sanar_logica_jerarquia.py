import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"

def audit_and_fix_logic():
    print("--- INICIANDO AUDITORIA DE LOGICA Y JERARQUIA ---")
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()

    # 1. Regla: MJ Graduate -> C1=SI, C2=SI
    cursor.execute("UPDATE participantes SET c1='SI', c2='SI' WHERE maestria='SI' AND (c1='NO' OR c2='NO')")
    fixed_mj = cursor.rowcount
    
    # 2. Regla: C2 Participant -> C1=SI
    cursor.execute("UPDATE participantes SET c1='SI' WHERE c2='SI' AND c1='NO'")
    fixed_c2 = cursor.rowcount
    
    print(f"Jerarquía corregida: {fixed_mj} graduados MJ y {fixed_c2} participantes C2.")

    # 3. Regla: Estandarización de Diana Moscoso Robles
    # Unificamos a 'Diana Yesenia Moscoso Robles' (el nombre más completo)
    cursor.execute("""
        UPDATE participantes 
        SET nombre = 'DIANA YESENIA', apellido = 'MOSCOSO ROBLES' 
        WHERE (nombre LIKE '%DIANA%' AND apellido LIKE '%MOSCOSO%')
           OR (nombre = 'DIANA' AND apellido = 'MOSCOSO ROBLES')
    """)
    fixed_names = cursor.rowcount
    print(f"Nombres unificados para Diana Moscoso: {fixed_names}")

    # 4. Regla: Relaciones IMO específicas
    # Antony Altamirano -> IMO: Diana Moscoso
    # Diana Moscoso -> IMO: Rosmery de Paz
    
    # Buscamos a Antony Altamirano para asegurar que su IMO sea Diana
    cursor.execute("""
        UPDATE participantes 
        SET imo = 'DIANA YESENIA MOSCOSO ROBLES', tel_imo = '924105061'
        WHERE (nombre LIKE '%ANTONY%' AND apellido LIKE '%ALTAMIRANO%')
    """)
    
    # Buscamos a Diana Moscoso para asegurar que su IMO sea Rosmery de Paz
    cursor.execute("""
        UPDATE participantes 
        SET imo = 'ROSMERY DE PAZ'
        WHERE (nombre LIKE '%DIANA%' AND apellido LIKE '%MOSCOSO%')
    """)
    
    conn.commit()
    conn.close()
    print("--- LOGICA DE JERARQUIA Y RELACIONES ACTUALIZADA ---")

if __name__ == "__main__":
    audit_and_fix_logic()
