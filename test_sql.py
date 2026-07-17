"""
Script de prueba para verificar la ejecución de comandos SQL en la base de datos torre_control.
Actualiza un registro y verifica el cambio.
"""
import sqlite3
from pathlib import Path

def test_sql():
    """Ejecuta una actualización de prueba y muestra el resultado."""
    db = Path("torre_control.db")
    conn = sqlite3.connect(db)
    c = conn.cursor()
    # Test query
    tel = "927928029"
    c.execute("UPDATE participantes SET email='SQL_SUCCESS' WHERE telefono LIKE ?", (f"%{tel}",))
    print(f"Filas afectadas: {c.rowcount}")
    conn.commit()

    c.execute("SELECT nombre, email FROM participantes WHERE telefono LIKE ?", (f"%{tel}",))
    print(f"Resultado: {c.fetchone()}")
    conn.close()

if __name__ == "__main__":
    test_sql()
