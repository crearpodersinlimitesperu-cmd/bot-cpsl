import re
from pathlib import Path

LOG_PATH = Path(r"C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff\.system_generated\logs\overview.txt")
OUTPUT_PATH = Path(r"C:\Users\josem\Downloads\bot-cpsl-review\HISTORIAL_INSTRUCCIONES_300.txt")

def extraer_instrucciones():
    print("--- EXTRAYENDO ULTIMAS 300 INSTRUCCIONES ---")
    if not LOG_PATH.exists():
        print("Error: No se encontro el archivo de logs.")
        return

    instrucciones = []
    
    # Leer el log y buscar patrones de mensajes de usuario
    with open(LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
        # Buscamos lineas que representen entradas de usuario
        # Segun el sistema, el overview tiene un formato especifico
        # Vamos a capturar el texto entre bloques de usuario
        content = f.read()
        
        # Intentar capturar bloques de mensaje de usuario
        # Nota: El formato puede variar, pero buscaremos la estructura de dialogo
        matches = re.findall(r'user: (.*?)(?=\n[a-z]+:|\Z)', content, re.DOTALL)
        
        for m in matches:
            clean_m = m.strip()
            if clean_m:
                instrucciones.append(clean_m)

    # Tomar las ultimas 300
    ultimas_300 = instrucciones[-300:]
    
    print(f"Total instrucciones encontradas: {len(instrucciones)}")
    print(f"Escribiendo las ultimas {len(ultimas_300)} en el documento...")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
        out.write("====================================================\n")
        out.write("      COMPENDIO DE INSTRUCCIONES ESTRATEGICAS CPSL\n")
        out.write("      (ULTIMAS 300 INDICACIONES DETECTADAS)\n")
        out.write("====================================================\n\n")
        
        for i, inst in enumerate(ultimas_300, 1):
            out.write(f"INSTRUCCION {i}:\n")
            out.write(f"{inst}\n")
            out.write("-" * 50 + "\n\n")

    print(f"Archivo generado exitosamente: {OUTPUT_PATH}")

if __name__ == "__main__":
    extraer_instrucciones()
