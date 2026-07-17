import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

def api(path):
    r = urllib.request.urlopen('http://localhost:10000' + path)
    return json.loads(r.read())

print('=== SALUD SISTEMA ===')
s = api('/api/salud')
for k,v in s.items():
    print(f'  {k}: {v}')

print('\n=== KPIs ===')
st = api('/api/stats')
for k,v in st.items():
    print(f'  {k}: {v}')

print('\n=== DUPLICADOS ===')
d = api('/api/duplicados')
print(f'  Total: {d["total"]}')

print('\n=== PENDIENTES (debe excluir graduados) ===')
p = api('/api/pendientes?entrenamiento=C1')
print(f'  Pendientes C1 Diana/Joyce: {len(p)}')

print('\n=== TEST BLOQUEO LINID ===')
try:
    # Buscar un PX de Linid
    linid_px = api('/api/buscar?q=Linid')
    if linid_px:
        px_id = linid_px[0]["id"]
        try:
            r = urllib.request.urlopen(f'http://localhost:10000/api/preview_plantilla?tipo=PENDIENTE_C1&px_id={px_id}')
            print('  ERROR: Deberia haber sido bloqueado!')
        except urllib.error.HTTPError as e:
            body = json.loads(e.read())
            print(f'  BLOQUEADO correctamente: {body["error"][:80]}')
    else:
        print('  No se encontraron PX de Linid en busqueda')
except Exception as e:
    print(f'  Error: {e}')

print('\n=== CAJA NEGRA (trazabilidad) ===')
cn = api('/api/caja_negra')
print(f'  Registros: {len(cn)}')
for r in cn[:5]:
    print(f'  [{r["tipo"]}] {r["accion"]}: {r["detalle"][:60]}')
