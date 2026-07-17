import pandas as pd, sys
sys.stdout.reconfigure(encoding='utf-8')
m = pd.read_excel(r'C:\Users\josem\Downloads\CONTROL_SISTEMA_CREARLIMA\Mineria_DNIs.xlsx', dtype=str)
print(f'Total: {len(m)}')
verif = m[m['Estatus'] == 'VERIFICADO']
print(f'Verificados RENIEC: {len(verif)}')
nf = m[m['Estatus'] == 'NO_ENCONTRADO']
print(f'No encontrados: {len(nf)}')
print(f'Columnas: {list(m.columns)}')
print(verif.head(3).to_string())
