import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def api(path):
    r = urllib.request.urlopen('http://localhost:10000' + path)
    return json.loads(r.read())

print('=== VERIFICACIÓN POST-INTEGRACIÓN ===\n')

# 1. Stats
s = api('/api/stats')
print(f"Total PX:           {s['total_participantes']}")
print(f"C1 Completado:      {s['c1_completado']}")
print(f"C2 Completado:      {s['c2_completado']}")
print(f"MJ Completado:      {s.get('mj_completado', 'N/A')}")
print(f"RENIEC Verificados: {s.get('verificados_reniec', 'N/A')}")
print(f"IMOs Únicos:        {s.get('imos_unicos', 'N/A')}")
print(f"Con CC Asignada:    {s['con_cc_asignada']}")
print(f"Duplicados Tel:     {s['duplicados_tel']}")

# 2. Salud
h = api('/api/salud')
print(f"\nSin CC:             {h['sin_cc']}")
print(f"Estado:             {h['estado']}")

# 3. Buscar un PX con RENIEC para verificar
px = api('/api/buscar?q=Juan Carlos')
if px:
    detalle = api(f"/api/participante/{px[0]['id']}")
    p = detalle['participante']
    print(f"\n=== DETALLE PX: {p['nombre']} {p['apellido']} ===")
    print(f"  RENIEC: {p.get('reniec_nombres','')} {p.get('reniec_paterno','')} {p.get('reniec_materno','')}")
    print(f"  Verificado: {p.get('verificado_reniec','')}")
    print(f"  IMO: {p.get('imo','')}")
    print(f"  CC: {p.get('cc_nombre','')}")
    print(f"  Equipo: {p.get('equipo','')}")
    print(f"  Rango: {p.get('max_rango','')}")
    print(f"  Trayectoria: {p.get('historial_trayectoria','')}")
    if detalle.get('alertas'):
        print(f"  Alertas: {detalle['alertas']}")

# 4. Verificar distribución CC
print('\n=== DISTRIBUCIÓN CC FINAL ===')
# Usar endpoint salud que ya tiene los datos
import sqlite3
conn = sqlite3.connect('torre_control.db')
for row in conn.execute("SELECT cc_nombre, COUNT(*) FROM participantes GROUP BY cc_nombre ORDER BY COUNT(*) DESC"):
    print(f"  {row[0] or '(vacío)'}: {row[1]}")
conn.close()
