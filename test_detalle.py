import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

r = urllib.request.urlopen('http://localhost:10000/api/buscar?q=Carlos')
d = json.loads(r.read())
p = d[0]
print(f"PX: {p['nombre']} {p['apellido']}")

r2 = urllib.request.urlopen(f"http://localhost:10000/api/participante/{p['id']}")
d2 = json.loads(r2.read())
px = d2['participante']
print(f"RENIEC: {px.get('reniec_nombres','')} {px.get('reniec_paterno','')} {px.get('reniec_materno','')}")
print(f"Verificado: {px.get('verificado_reniec','')}")
print(f"IMO: {px.get('imo','')}")
print(f"CC: {px.get('cc_nombre','')}")
print(f"Equipo: {px.get('equipo','')}")
print(f"Rango: {px.get('max_rango','')}")
print(f"Trayectoria: {px.get('historial_trayectoria','')}")
print(f"Alertas: {d2.get('alertas',[])}")
