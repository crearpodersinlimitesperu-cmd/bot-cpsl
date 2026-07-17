import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8')

r = urllib.request.urlopen('http://localhost:10000/api/stats')
d = json.loads(r.read())

print("=== KPIs FINALES ===")
print(f"  Total PX:           {d['total_participantes']}")
print(f"  C1 Completado:      {d['c1_completado']}")
print(f"  C1 Pendientes REAL: {d['c1_pendiente']}")
print(f"  C1 Descartados:     {d.get('c1_descartados', 'N/A')}")
print(f"  C2 Completado:      {d['c2_completado']}")
print(f"  MJ Completado:      {d.get('mj_completado', 'N/A')}")
print(f"  RENIEC Verificados: {d.get('verificados_reniec', 'N/A')}")
print(f"  IMOs:               {d.get('imos_unicos', 'N/A')}")
print(f"  Con CC:             {d['con_cc_asignada']}")

r2 = urllib.request.urlopen('http://localhost:10000/api/pendientes?entrenamiento=C1')
pend = json.loads(r2.read())
print(f"\n  Pendientes C1 REALES (Joyce+Diana): {len(pend)}")
