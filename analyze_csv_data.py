import pandas as pd
import os
import sys

# Asegurar UTF-8
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

def analyze_participants_csv(csv_path):
    print(f"\n--- ANALYZING CSV: {os.path.basename(csv_path)} ---")
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return
    
    try:
        # Intentar cargar con manejo de líneas malas
        df = pd.read_csv(csv_path, on_bad_lines='skip')
        print(f"Total records (valid): {len(df)}")
        
        print("\n[BY TYPE]")
        if 'Tipo' in df.columns:
            print(df['Tipo'].value_counts())
        
        print("\n[BY TEAM]")
        if 'Equipo' in df.columns:
            print(df['Equipo'].value_counts().head(10))
        
        print("\n[BY C1 STATUS]")
        if 'C1' in df.columns:
            print(df['C1'].value_counts())
        
        # Missing phones
        if 'Teléfono' in df.columns:
            missing_phones = df['Teléfono'].isna().sum()
            print(f"\nMissing phones: {missing_phones}")
        
        # IMO check
        if 'IMO' in df.columns:
            imos_count = df['IMO'].nunique()
            print(f"Unique IMOs: {imos_count}")
            
    except Exception as e:
        print(f"Error analyzing CSV: {e}")

analyze_participants_csv(r"C:\Users\josem\Downloads\participantes_2026-05-11.csv")
