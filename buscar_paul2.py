import sqlite3

conn = sqlite3.connect(r"C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db")
c = conn.cursor()

# Wide search
queries = [
    "SELECT id, nombre, apellido, telefono, email, equipo, imo, tel_imo, identificacion FROM participantes WHERE nombre LIKE '%PAUL%' AND apellido LIKE '%VARGAS%'",
    "SELECT id, nombre, apellido, telefono, email, equipo, imo, tel_imo, identificacion FROM participantes WHERE apellido LIKE '%VALENTIN%'",
    "SELECT id, nombre, apellido, telefono, email, equipo, imo, tel_imo, identificacion FROM participantes WHERE nombre LIKE '%YHONADAN%'",
    "SELECT id, nombre, apellido, telefono, email, equipo, imo, tel_imo, identificacion FROM participantes WHERE nombre LIKE '%PAUL%' AND equipo LIKE '%28%'",
]

for q in queries:
    c.execute(q)
    rows = c.fetchall()
    if rows:
        print(f"\nQuery: {q.split('WHERE')[1].strip()}")
        for r in rows:
            print(f"  ID:{r[0]} | {r[1]} {r[2]} | Tel:{r[3]} | Email:{r[4]} | Eq:{r[5]} | IMO:{r[6]} | TelIMO:{r[7]} | DNI:{r[8]}")

conn.close()
