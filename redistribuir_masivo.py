import sqlite3
import pandas as pd

def redistribuir():
    print("--- REDISTRIBUCIÓN MASIVA A JOYCE Y DIANA ---")
    
    file_path = r'C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Asignaciones_Web.xlsx'
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    
    df = pd.read_excel(file_path)
    # Algunos DNIs pueden venir como float
    dnis = df['ClienteId'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip().tolist()
    dnis = [d for d in dnis if d and d != 'nan']
    
    # Round-robin: Mitad para Diana, Mitad para Joyce
    coordinators = ['Diana Moscoso', 'Joyce Marín']
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    actualizados_diana = 0
    actualizados_joyce = 0
    
    for i, dni in enumerate(dnis):
        cc = coordinators[i % 2]
        cursor.execute("UPDATE participantes SET cc_nombre = ? WHERE identificacion = ?", (cc, dni))
        
        if cursor.rowcount > 0:
            if cc == 'Diana Moscoso':
                actualizados_diana += 1
            else:
                actualizados_joyce += 1

    conn.commit()
    conn.close()
    
    print(f"Total procesados del Excel: {len(dnis)}")
    print(f"Actualizados a Diana Moscoso: {actualizados_diana}")
    print(f"Actualizados a Joyce Marín: {actualizados_joyce}")
    print("Redistribución completa.")

if __name__ == "__main__":
    redistribuir()
