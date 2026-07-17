import pandas as pd
from pathlib import Path

# Ruta
FILE_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\Productividad_Web.xlsx")

def refinar_final():
    print("--- REFINANDO LISTADO FINAL DE CONTACTO C1 ---")
    df = pd.read_excel(FILE_PATH)
    
    # Identificar columna de Gestion
    gest_col = [c for c in df.columns if 'GESTI' in str(c).upper()][0]
    
    # Filtrar Diana y Joyce
    df_cc = df[df['CC_Reportada'].isin(['DIANA', 'JOYCE'])]
    
    # Exclusiones estrictas
    exclusiones = ['CONFIRMADO', 'NO INTERESA', 'DEVOLUCION', 'YA ASISTIO', 'REBOTE', 'DUPLICADO']
    
    def es_valido(val):
        v = str(val).upper()
        if pd.isna(val) or v == 'NAN' or v == '':
            return True # Son los nuevos
        for ex in exclusiones:
            if ex in v:
                return False
        return True

    df_cc['EsValido'] = df_cc[gest_col].apply(es_valido)
    df_final = df_cc[df_cc['EsValido'] == True]
    
    # Guardar
    output_path = "LISTA_FINAL_C1_PARA_CONTACTO.csv"
    df_final.to_csv(output_path, index=False)
    
    print(f"\nAUDITORIA COMPLETADA:")
    print(f"Total Inicial: {len(df_cc)}")
    print(f"Total Aptos (Refinado): {len(df_final)}")
    print(f"Archivo generado: {output_path}")

if __name__ == "__main__":
    refinar_final()
