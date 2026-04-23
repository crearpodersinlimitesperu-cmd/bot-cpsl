import os, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('casos_derivados.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''
def casos_cerrados(cc_key=None, limite=15):
    """Retorna los ultimos casos cerrados (archivados), opcionalmente filtrado por CC."""
    with _lk:
        casos = _cargar()
    cerrados = [c for c in casos.values() if c["estado"] == "CERRADO"]
    if cc_key:
        cerrados = [c for c in cerrados if c["cc_key"] == cc_key]
    return sorted(cerrados, key=lambda x: x.get("ts_cierre") or "", reverse=True)[:limite]
'''
if 'def casos_cerrados' not in content:
    content += new_func
    with open('casos_derivados.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('casos_cerrados added')
else:
    print('casos_cerrados already exists')
