import pandas as pd
from pathlib import Path

# Ruta
FILE_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\Productividad_Web.xlsx")

def analizar_poblacion():
    print("--- INICIANDO ANALISIS DE POBLACION OBJETIVO C1 ---")
    df = pd.read_excel(FILE_PATH)
    
    # Identificar columna de Resultado Gestion (posicion 9 usualmente)
    gest_col = [c for c in df.columns if 'GESTI' in str(c).upper()][0]
    asig_col = [c for c in df.columns if 'ASIG' in str(c).upper()][0]
    
    print(f"Columna de Gestion: {gest_col}")
    
    # Filtrar Diana y Joyce
    df_cc = df[df['CC_Reportada'].isin(['DIANA', 'JOYCE'])]
    
    # Criterio: 
    # 1. Resultado Gestion es NaN (Sin contacto)
    # 2. Resultado Gestion es 'No Contesta', 'Siguiente', 'Por Confirmar'
    # 3. Y que NO sea 'Confirmado', 'No Interesa', 'Devolucion'
    
    # Excluir negativos
    exclusiones = ['CONFIRMADO', 'NO INTERESA', 'DEVOLUCION', 'REBOTE', 'DUPLICADO']
    
    def es_apto_contacto(val):
        v = str(val).upper()
        if pd.isna(val) or v == 'NAN' or v == '':
            return True
        if any(ex in v for ex in exclusiones):
            return False
        return True # Si no esta en exclusiones, es apto (No contesta, etc)

    df_cc['EsApto'] = df_cc[gest_col].apply(es_apto_contacto)
    
    # Filtrar por los que SI son aptos
    target = df_cc[df_cc['EsApto'] == True]
    
    print(f"\nRESUMEN DIANA/JOYCE:")
    print(f"Total Asignados: {len(df_cc)}")
    print(f"Aptos para Contactar: {len(target)}")
    
    print("\nDesglose por Estado de Gestión:")
    print(target[gest_col].value_counts(dropna=False).to_string())
    
    # Guardar listado final
    target.to_csv("LISTA_CONTACTO_URGENTE_C1.csv", index=False)
    print(f"\nArchivo generado con {len(target)} registros: LISTA_CONTACTO_URGENTE_C1.csv")

if __name__ == "__main__":
    analizar_poblacion()
