import pandas as pd
import os
import collections

def main():
    aptos_path = r"c:\Users\josem\Downloads\Asignados_Aptos_Joyce_Diana_Final.csv"
    if not os.path.exists(aptos_path):
        print("File not found")
        return
        
    df = pd.read_csv(aptos_path, encoding='utf-8-sig')
    domains = collections.Counter()
    suspicious = []
    
    for e in df['Correo'].dropna():
        e_str = str(e).strip().lower()
        if '@' in e_str:
            domain = e_str.split('@')[1]
            domains[domain] += 1
            
            # check suspicious
            if domain not in ['gmail.com', 'hotmail.com', 'yahoo.com', 'yahoo.es', 'outlook.com', 'live.com', 'icloud.com']:
                suspicious.append(e_str)
                
    print("Top domains:")
    for d, c in domains.most_common(10):
        print(f"{d}: {c}")
        
    print("\nSuspicious or rare domains:")
    for s in suspicious:
        print(s)

if __name__ == "__main__":
    main()
