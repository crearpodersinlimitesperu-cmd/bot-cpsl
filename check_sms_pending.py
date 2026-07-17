import sqlite3
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

def check_pending():
    if not os.path.exists(DB_PATH):
        print(f"Error: DB no encontrada en {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Verificar pendientes en la tabla de comunicaciones
    try:
        cursor.execute("SELECT COUNT(*) FROM comunicaciones WHERE estado = 'PENDIENTE' AND canal = 'SMS'")
        count = cursor.fetchone()[0]
        print(f"SMS Pendientes en tabla 'comunicaciones': {count}")
    except Exception as e:
        print(f"Error al consultar tabla 'comunicaciones': {e}")

    # Verificar participantes marcados como REBOTE
    try:
        cursor.execute("SELECT COUNT(*) FROM participantes WHERE email = 'REBOTE' AND telefono != ''")
        rebotes = cursor.fetchone()[0]
        print(f"Participantes marcados como 'REBOTE' con telefono: {rebotes}")
    except Exception as e:
        print(f"Error al consultar tabla 'participantes': {e}")

    conn.close()

if __name__ == "__main__":
    check_pending()
