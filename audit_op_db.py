import sqlite3
import pandas as pd
import os

def audit_db():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    if not os.path.exists(db_path):
        print(f"Error: {db_path} no encontrado.")
        return

    conn = sqlite3.connect(db_path)
    
    print("--- AUDITORÍA DE BASE DE DATOS CPSL ---")
    
    # 1. Totales
    total = pd.read_sql_query('SELECT count(id) FROM participantes', conn).iloc[0,0]
    print(f"Total participantes en DB: {total}")

    # 2. Distribución de Coordinadores
    ccs = pd.read_sql_query('SELECT cc_nombre, count(id) FROM participantes GROUP BY cc_nombre', conn)
    print("\nDistribución por Coordinadora:")
    print(ccs)

    # 3. Estados Críticos
    graduados = pd.read_sql_query("SELECT count(id) FROM participantes WHERE estado = 'GRADUADO_COMPLETO'", conn).iloc[0,0]
    pendientes = pd.read_sql_query("SELECT count(id) FROM participantes WHERE es_pendiente_real = 'SI'", conn).iloc[0,0]
    print(f"\nGraduados (Excluidos): {graduados}")
    print(f"Pendientes Reales (Campaña): {pendientes}")

    # 4. Consistencia C1/C2
    c1c2 = pd.read_sql_query("SELECT c1, c2, count(id) FROM participantes GROUP BY c1, c2", conn)
    print("\nEstado Asistencia C1/C2:")
    print(c1c2)

    # 5. Auditoría de IMOs
    imos_vacios = pd.read_sql_query("SELECT count(id) FROM participantes WHERE (imo IS NULL OR imo = '' OR imo = '-') AND es_pendiente_real = 'SI'", conn).iloc[0,0]
    print(f"\nPendientes sin IMO asignado: {imos_vacios}")

    # 6. Auditoría de Correos
    emails_vacios = pd.read_sql_query("SELECT count(id) FROM participantes WHERE (email IS NULL OR email = '') AND es_pendiente_real = 'SI'", conn).iloc[0,0]
    print(f"Pendientes sin Email: {emails_vacios}")

    conn.close()

if __name__ == "__main__":
    audit_db()
