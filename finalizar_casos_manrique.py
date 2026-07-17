import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path("torre_control.db")

def finalizar_casos():
    print("--- FINALIZANDO DEPURACION CASO MANRIQUE ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Actualizar Oscar Leiva (ID 400)
    c.execute("UPDATE participantes SET c1 = 'SI', observaciones = 'GRADUADO_REAL_E26_CONFIRMADO_CAROLINA' WHERE id = 400")
    print(f"Oscar Leiva (ID 400) actualizado: {c.rowcount}")
    
    # 2. Buscar a Erika Anticona
    c.execute("SELECT id, nombre, apellido FROM participantes WHERE nombre LIKE '%ERIKA%' OR apellido LIKE '%ANTICONA%'")
    erika_res = c.fetchall()
    print(f"\nBusqueda Erika Anticona: {erika_res}")
    
    for row in erika_res:
        eid = row[0]
        c.execute("UPDATE participantes SET c1 = 'SI', observaciones = 'GRADUADO_REAL_E27_CONFIRMADO_CAROLINA' WHERE id = ?", (eid,))
        print(f"Erika Anticona (ID {eid}) actualizada: {c.rowcount}")

    conn.commit()
    conn.close()
    print("\nPROCESO COMPLETADO.")

if __name__ == "__main__":
    finalizar_casos()
