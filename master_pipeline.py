import subprocess
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Configuración
BASE_DIR = Path(__file__).resolve().parent
LOG_DB = BASE_DIR / "caja_negra.db"

def registrar_log_master(evento, detalle, estado="OK"):
    try:
        conn = sqlite3.connect(LOG_DB)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'MASTER_PIPELINE', evento, detalle, estado))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error al registrar log: {e}")

def ejecutar_script(nombre_script):
    path_script = BASE_DIR / nombre_script
    print(f"Ejecutando: {nombre_script}...")
    try:
        # Usamos latin1 para evitar errores de decodificación con caracteres especiales de Windows
        result = subprocess.run([sys.executable, str(path_script)], capture_output=True, text=True, encoding='latin1')
        if result.returncode == 0:
            print(f"COMPLETADO: {nombre_script}")
            registrar_log_master(f"RUN_{nombre_script.upper()}", f"Ejecucion exitosa.", "SUCCESS")
            return True, result.stdout
        else:
            print(f"ERROR en {nombre_script}: {result.stderr}")
            registrar_log_master(f"ERROR_{nombre_script.upper()}", result.stderr[:200], "FAILED")
            return False, result.stderr
    except Exception as e:
        print(f"FALLO CRITICO al lanzar {nombre_script}: {e}")
        return False, str(e)

def main():
    print("="*60)
    print("  CREAR PODER SIN LIMITES GLOBAL - MASTER PIPELINE")
    print("="*60)
    
    start_time = datetime.now()
    pipeline = [
        "sanar_caja_negra.py",
        "sanar_logica_jerarquia.py",
        "actualizar_memoria_caja_negra.py",
        "sanar_imo_enrolados.py",
        "procesar_cambios_cupo.py",
        "rescate_imos.py",
        "agenda_mañana_8am.py"
    ]
    
    resultados = []
    
    for script in pipeline:
        success, output = ejecutar_script(script)
        resultados.append((script, "SUCCESS" if success else "FAILED"))
        if not success:
            print(f"DETENIENDO PIPELINE por fallo en {script}")
            break
            
    end_time = datetime.now()
    duracion = end_time - start_time
    
    print("\n" + "="*60)
    print(f"PIPELINE FINALIZADO - Duracion: {duracion}")
    for s, r in resultados:
        print(f"  [{r}] {s}")
    print("="*60)
    
    registrar_log_master("PIPELINE_COMPLETE", f"Pipeline ejecutado en {duracion}", "FINISHED")

if __name__ == "__main__":
    main()
