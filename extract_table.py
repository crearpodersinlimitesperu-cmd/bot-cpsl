import json
import pandas as pd

log_path = r'C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\.system_generated\logs\overview.txt'
output_csv = r'C:\Users\josem\Downloads\bot-cpsl-review\asignaciones_pasted.csv'

data = []
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            entry = json.loads(line)
            if entry.get('type') == 'USER_INPUT' and 'mercedesniquin567@gmail.com' in entry.get('content', ''):
                content = entry['content']
                # Split by newline
                lines = content.split('\n')
                for cl in lines:
                    parts = cl.strip().split('\t')
                    if len(parts) >= 8 and parts[0] in ['kdelgado', 'lvalencia', 'jmarin', 'dmoscoso', 'zurteaga', 'jsanchez']:
                        data.append(parts)
        except:
            pass

df = pd.DataFrame(data)
if not df.empty:
    df = df.iloc[:, :8] # Take first 8 columns
    df.columns = ['usuario', 'equipo', 'identificacion', 'nombre', 'apellido', 'telefono', 'email', 'imo']
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"Extracted {len(df)} rows to {output_csv}")
else:
    print("No data extracted.")
