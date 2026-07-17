import sqlite3

def check_schema():
    conn = sqlite3.connect(r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(logs)")
    columns = cursor.fetchall()
    print("Schema for table 'logs' in 'caja_negra.db':")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()
