import sqlite3
import pandas as pd
import re
from datetime import datetime
from pathlib import Path

# Configuración de Rutas
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "torre_control.db"
LOG_DB = BASE_DIR / "caja_negra.db"

def registrar_auditoria(px_id, nombre, categoria, detalle, score, estado="PROCESADO"):
    conn = sqlite3.connect(LOG_DB)
    c = conn.cursor()
    c.execute("""
        INSERT INTO logs (timestamp, categoria, evento, detalle, estado) 
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "AUDITORIA_MASIVA", categoria, 
          f"ID:{px_id} | PX:{nombre} | Score:{score} | {detalle}", estado))
    conn.commit()
    conn.close()

def es_email_valido(email):
    if not email or pd.isna(email): return False
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", str(email)))

def auditar_sistema():
    print("--- INICIANDO OPERACIÓN DEPURACIÓN MASIVA CPSL ---")
    conn = sqlite3.connect(DB_PATH)
    
    # Cargar solo Diana y Joyce
    query = "SELECT * FROM participantes WHERE cc_nombre IN ('Diana Moscoso', 'Joyce Marín')"
    df = pd.read_sql_query(query, conn)
    
    stats = {
        "activos_reales": 0, "recuperables": 0, "invalidos": 0, "duplicados": 0,
        "emails_invalidos": 0, "rebotes_perm": 0, "cambios_nombre": 0, "sms_enviados": 0
    }
    
    lista_para_sms_validacion = []
    
    for idx, row in df.iterrows():
        score = 100
        motivos_descarte = []
        
        # 1. Validación de Identidad
        nombre_limpio = str(row['nombre']).strip()
        if len(nombre_limpio) < 3 or any(char.isdigit() for char in nombre_limpio):
            score -= 40
            motivos_descarte.append("Nombre dudoso/incompleto")
            
        # 2. Validación de Email
        if not es_email_valido(row['email']):
            score -= 30
            stats["emails_invalidos"] += 1
            motivos_descarte.append("Email inválido")
            
        # 3. Validación de Interés y Estado
        res_gestion = str(row['resultado_gestion']).upper()
        if any(x in res_gestion for x in ['NO INTERES', 'DEVOLU', 'REEMBOL', 'DESERTOR']):
            score = 0
            motivos_descarte.append("No interesado/Desertor")
            
        # 4. Clasificación
        if score >= 80:
            stats["activos_reales"] += 1
            estado_final = "ACTIVO_VALIDADO"
        elif score >= 40:
            stats["recuperables"] += 1
            estado_final = "DUDOSO_RECUPERABLE"
            lista_para_sms_validacion.append({
                "id": row['id'], "nombre": row['nombre'], "tel": row['telefono'], "cc": row['cc_nombre']
            })
        else:
            stats["invalidos"] += 1
            estado_final = "DESCARTADO_BASURA"

        # Registrar en Caja Negra
        registrar_auditoria(row['id'], row['nombre'], "CLASIFICACION_IA", 
                            f"Estado Final: {estado_final} | Motivos: {', '.join(motivos_descarte)}", score)
        
        # Actualizar DB Central con el Score y Estado
        conn.execute("""
            UPDATE participantes 
            SET observaciones = ?, 
                fecha_actualizacion = ?
            WHERE id = ?
        """, (f"AUDIT_SCORE_{score}_{estado_final}", datetime.now().strftime('%Y-%m-%d'), row['id']))

    conn.commit()
    conn.close()
    
    print(f"--- DEPURACIÓN FINALIZADA ---")
    print(f"Activos Reales: {stats['activos_reales']}")
    print(f"Recuperables (Para SMS): {len(lista_para_sms_validacion)}")
    print(f"Inválidos/Basura: {stats['invalidos']}")
    
    return lista_para_sms_validacion, stats

if __name__ == "__main__":
    auditar_sistema()
