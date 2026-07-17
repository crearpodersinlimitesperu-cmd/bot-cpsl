import os
import pandas as pd

search_dir = r"c:\Users\josem\Downloads"

def search_files():
    found_files = []
    for root, dirs, files in os.walk(search_dir):
        if 'node_modules' in root or '.git' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.csv'):
                path = os.path.join(root, file)
                try:
                    df = pd.read_csv(path, nrows=1, on_bad_lines='skip', encoding='utf-8')
                    if 'IdentificacionIMO' in df.columns or 'Usuario Actual' in df.columns:
                        found_files.append((path, 'csv'))
                except Exception as e:
                    pass
            elif file.endswith('.xlsx'):
                path = os.path.join(root, file)
                try:
                    df = pd.read_excel(path, nrows=1)
                    if 'IdentificacionIMO' in df.columns or 'Usuario Actual' in df.columns:
                        found_files.append((path, 'xlsx'))
                except Exception as e:
                    pass
    
    for f in found_files:
        print(f"Found in: {f[0]}")

if __name__ == '__main__':
    search_files()
