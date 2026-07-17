import pandas as pd
from pathlib import Path

# Rutas
APTOS_FILE = Path("PX_APTOS_VALIDADOS_FINAL.csv")
PROD_FILE = Path("Productividad_Web.xlsx")

def auditar_voluntad():
    print("--- AUDITORIA DE VOLUNTAD Y RECHAZOS (DIANA/JOYCE) ---")
    if not APTOS_FILE.exists() or not PROD_FILE.exists():
        print("Archivos necesarios no encontrados.")
        return

    df_aptos = pd.read_csv(APTOS_FILE)
    df_prod = pd.read_excel(PROD_FILE)
    
    # Identificar columnas
    email_col_asig = 'Correo'
    dni_col_asig = 'Identificaci\u00f3n'
    
    gest_col_prod = [c for c in df_prod.columns if 'GESTI' in str(c).upper()][0]
    email_col_prod = 'Correo'
    dni_col_prod = 'Identificaci\u00f3n' if 'Identificaci\u00f3n' in df_prod.columns else df_prod.columns[3]

    # Normalizar llaves
    df_aptos['dni_key'] = df_aptos[dni_col_asig].astype(str).str.replace(".0", "", regex=False).str.strip()
    df_prod['dni_key'] = df_prod[dni_col_prod].astype(str).str.replace(".0", "", regex=False).str.strip()
    
    # Filtrar rechazos en el portal
    exclusiones = ['NO INTERESA', 'DEVOLUCION', 'NO QUIERE', 'REBOTE', 'NO LLAMAR']
    df_rechazos = df_prod[df_prod[gest_col_prod].astype(str).str.upper().str.contains('|'.join(exclusiones), na=False)]
    
    rechazos_dnis = set(df_rechazos['dni_key'].tolist())
    
    # Cruce
    final_aptos = []
    descartados = []
    
    for _, row in df_aptos.iterrows():
        if row['dni_key'] in rechazos_dnis:
            descartados.append(row)
        else:
            final_aptos.append(row)
            
    print(f"Aptos Iniciales: {len(df_aptos)}")
    print(f"Descartados por Rechazo previo (Portal): {len(descartados)}")
    print(f"Participantes 100% LIMPIOS para contactar: {len(final_aptos)}")
    
    if final_aptos:
        df_final = pd.DataFrame(final_aptos)
        df_final.to_csv("PX_LISTOS_PARA_CONTACTO_FINAL.csv", index=False)
        print("Reporte generado: PX_LISTOS_PARA_CONTACTO_FINAL.csv")

if __name__ == "__main__":
    auditar_voluntad()
