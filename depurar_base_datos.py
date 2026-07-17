import sqlite3
from pathlib import Path
from datetime import datetime

# Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

def registrar_log(categoria, evento, detalle, estado="OK"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("INSERT INTO logs (timestamp, categoria, evento, detalle, estado) VALUES (?, ?, ?, ?, ?)",
              (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), categoria, evento, detalle, estado))
    conn.commit()
    conn.close()

def depurar_duplicados():
    print("--- INICIANDO DEPURACIÓN Y CLARIFICACIÓN DE DB ---")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. Identificar números con más de un registro
    c.execute("SELECT telefono, COUNT(*) as c FROM participantes WHERE telefono != '' AND telefono IS NOT NULL GROUP BY telefono HAVING c > 1")
    dups = c.fetchall()
    print(f"Detectados {len(dups)} números con duplicidad.")
    
    eliminados = 0
    
    for tel, count in dups:
        # Obtener todos los registros de ese teléfono, ordenados por:
        # 1. Tiene C2 (Sentado)
        # 2. Tiene C1 (Sentado)
        # 3. ID más alto (más reciente)
        c.execute("""
            SELECT id, nombre, apellido, c1, c2 
            FROM participantes 
            WHERE telefono = ? 
            ORDER BY 
                (CASE WHEN c2='SI' THEN 2 WHEN c1='SI' THEN 1 ELSE 0 END) DESC,
                id DESC
        """, (tel,))
        
        records = c.fetchall()
        # El primero es nuestro "Registro Maestro"
        master_id = records[0][0]
        
        # Eliminar los demás
        for r in records[1:]:
            c.execute("DELETE FROM participantes WHERE id = ?", (r[0],))
            eliminados += 1
            
    conn.commit()
    conn.close()
    
    msg = f"Depuración finalizada. Se eliminaron {eliminados} registros duplicados. La base de datos está ahora clarificada y optimizada."
    print(msg)
    registrar_log("MANTENIMIENTO", "DEPURACION_DUPLICADOS", msg)

if __name__ == "__main__":
    depurar_duplicados()
