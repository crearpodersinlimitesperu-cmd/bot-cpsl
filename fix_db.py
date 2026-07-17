import sqlite3

def fix_db():
    print("--- APLICANDO CORRECCIONES A BD ---")
    conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db')
    cursor = conn.cursor()

    # 1. Eliminar (excluir de campañas) a los que ya hicieron C1 y C2
    cursor.execute("UPDATE participantes SET es_pendiente_real = 'NO', estado = 'GRADUADO_COMPLETO' WHERE c1 = 'SI' AND c2 = 'SI'")
    graduados = cursor.rowcount
    print(f"Participantes marcados como completados (C1 y C2 = SI): {graduados}")

    # 2. Reasignar los casos restantes de Zuley a Diana y Joyce equitativamente
    cursor.execute("SELECT id FROM participantes WHERE cc_nombre LIKE '%zuley%'")
    zuley_cases = [row[0] for row in cursor.fetchall()]
    
    coordinators = ['Diana Moscoso', 'Joyce Marín']
    act_diana = 0
    act_joyce = 0
    
    for i, pid in enumerate(zuley_cases):
        cc = coordinators[i % 2]
        cursor.execute("UPDATE participantes SET cc_nombre = ? WHERE id = ?", (cc, pid))
        if cc == 'Diana Moscoso':
            act_diana += 1
        else:
            act_joyce += 1

    print(f"Casos restantes de Zuley reasignados: {len(zuley_cases)}")
    print(f"   -> Diana: {act_diana}")
    print(f"   -> Joyce: {act_joyce}")

    conn.commit()
    conn.close()
    print("Correcciones guardadas exitosamente.")

if __name__ == "__main__":
    fix_db()
