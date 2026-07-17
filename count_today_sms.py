import sqlite3
import time

def count_sms():
    conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db')
    cursor = conn.cursor()
    
    print("--- REPORTE DE SMS (Caja Negra) ---")
    
    # Todos los SMS
    cursor.execute("SELECT evento, COUNT(*) FROM logs WHERE evento LIKE '%SMS%' GROUP BY evento")
    detalles = cursor.fetchall()
    for ev, cnt in detalles:
        print(f" - {ev}: {cnt}")
    
    # Total
    cursor.execute("SELECT COUNT(*) FROM logs WHERE evento LIKE '%SMS%'")
    total = cursor.fetchone()[0]
    print(f"\nTotal Histórico de SMS: {total}")
    
    conn.close()

if __name__ == "__main__":
    count_sms()
