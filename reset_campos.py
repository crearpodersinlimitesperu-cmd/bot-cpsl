import sqlite3
conn = sqlite3.connect('torre_control.db')
conn.execute("UPDATE participantes SET resultado_gestion='', es_pendiente_real='SI', tiene_cambio_cupo='NO'")
conn.commit()
print('Campos reseteados')
conn.close()
