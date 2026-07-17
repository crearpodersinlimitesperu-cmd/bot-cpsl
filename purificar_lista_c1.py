import sqlite3
from pathlib import Path

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"

def purificar():
    print("--- PURIFICANDO LISTA DE REZAGADOS C1 ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Query purificada
    query = """
        SELECT nombre, apellido, telefono, resultado_gestion 
        FROM participantes 
        WHERE c1 = 'NO' 
          AND es_pendiente_real = 'SI' 
          AND cc_nombre IN ('Diana Moscoso', 'Joyce Marín')
          AND telefono != ''
          AND (resultado_gestion IS NULL 
               OR (resultado_gestion NOT LIKE '%INTERES%' 
                   AND resultado_gestion NOT LIKE '%DEVOLU%' 
                   AND resultado_gestion NOT LIKE '%REEMBOL%' 
                   AND resultado_gestion NOT LIKE '%DESERTOR%'
                   AND resultado_gestion NOT LIKE '%NO DESEA%'))
    """
    
    c.execute(query)
    aptos = c.fetchall()
    conn.close()
    
    print(f"Total Aptos Reales detectados: {len(aptos)}")
    if aptos:
        print("\nEjemplos de Aptos (Primeros 5):")
        for a in aptos[:5]:
            print(f"- {a[0]} {a[1]} ({a[2]}) | Gestión previa: {a[3] or 'Ninguna'}")
    
    return len(aptos)

if __name__ == "__main__":
    purificar()
