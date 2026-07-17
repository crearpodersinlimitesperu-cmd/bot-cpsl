import sqlite3
import pandas as pd
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'

def audit_db():
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        return
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("--- TORRE_CONTROL.DB SUMMARY ---")
    for table in tables:
        t_name = table[0]
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {t_name}")
            count = cursor.fetchone()[0]
            print(f"Table: {t_name:20} | Rows: {count}")
        except:
            print(f"Table: {t_name:20} | Error reading count")
            
    # Check for participants with REBOTE
    cursor.execute("SELECT COUNT(*) FROM participantes WHERE email = 'REBOTE'")
    rebotes = cursor.fetchone()[0]
    print(f"\nParticipantes con REBOTE: {rebotes}")
    
    conn.close()

if __name__ == "__main__":
    audit_db()
