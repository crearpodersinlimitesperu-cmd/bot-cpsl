import sqlite3
from pathlib import Path

DB_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")

def inyectar_datos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Datos de Cesar Mirko
    query = """
        UPDATE participantes 
        SET email = 'mirkogarces@hotmail.com', 
            identificacion = '10620405', 
            observaciones = 'VALIDADO_ETL_B001-2113_GRADUADO_REAL' 
        WHERE id = 1749
    """
    
    try:
        c.execute(query)
        conn.commit()
        print("SISTEMA ACTUALIZADO: Cesar Mirko Garcés Romero validado con éxito.")
    except Exception as e:
        print(f"Error en la actualización: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    inyectar_datos()
