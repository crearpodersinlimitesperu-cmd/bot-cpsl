import sqlite3
import os

DB = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'

def check():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print(f"Tables in {DB}:", cursor.fetchall())
    
    # Check for 'logs' table
    try:
        cursor.execute("SELECT * FROM logs LIMIT 5")
        print("Logs content:", cursor.fetchall())
    except Exception as e:
        print("Error reading logs table:", e)
        
    conn.close()

if __name__ == "__main__":
    check()
