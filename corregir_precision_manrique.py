import sqlite3
from pathlib import Path

DB_PATH = Path("torre_control.db")

def corregir_precision():
    print("--- REALIZANDO AJUSTE QUIRURGICO DE PRECISION ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Revertir todo lo que no sea ID 670 o ID 400 que se haya marcado como graduado en este proceso
    query = """
        UPDATE participantes 
        SET c1 = 'NO', 
            observaciones = NULL 
        WHERE (nombre LIKE '%ERIKA%' OR apellido LIKE '%ANTICONA%') 
          AND id NOT IN (400, 670) 
          AND observaciones LIKE '%GRADUADO_REAL_%'
    """
    
    try:
        c.execute(query)
        conn.commit()
        print(f"Registros revertidos por precaucion: {c.rowcount}")
    except Exception as e:
        print(f"Error en la correccion: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    corregir_precision()
