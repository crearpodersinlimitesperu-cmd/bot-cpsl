import sqlite3
import pandas as pd
import os

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
ARTIFACT_DIR = r'C:\Users\josem\.gemini\antigravity\brain\f50a7b8d-9862-41dc-8e0a-ca81eb8aaeff'
OUT_FILE = os.path.join(ARTIFACT_DIR, 'reporte_comunicaciones.md')

def generar_reporte():
    conn = sqlite3.connect(DB_PATH)
    
    # SMS
    sms_df = pd.read_sql("SELECT timestamp, evento, detalle FROM logs WHERE evento LIKE '%SMS%' ORDER BY timestamp DESC LIMIT 60", conn)
    
    # Respuestas
    resp_df = pd.read_sql("SELECT timestamp, evento, detalle FROM logs WHERE evento LIKE '%RESPUESTA%' ORDER BY timestamp DESC LIMIT 60", conn)
    
    conn.close()
    
    with open(OUT_FILE, 'w', encoding='utf-8') as f:
        f.write("# Reporte de Comunicaciones (Caja Negra)\n\n")
        
        f.write("## 📱 SMS Enviados (Rebotes)\n")
        f.write("Últimos SMS procesados por el sistema:\n\n")
        if not sms_df.empty:
            f.write("| Fecha/Hora | Evento | Detalle |\n")
            f.write("|---|---|---|\n")
            for _, row in sms_df.iterrows():
                f.write(f"| {row['timestamp']} | {row['evento']} | {row['detalle']} |\n")
        else:
            f.write("No hay registros de SMS en la Caja Negra.\n")
            
        f.write("\n## 📧 Respuestas Recibidas (Actualizaciones)\n")
        f.write("Respuestas procesadas por la Inteligencia Artificial / Bot:\n\n")
        if not resp_df.empty:
            f.write("| Fecha/Hora | Evento | Detalle |\n")
            f.write("|---|---|---|\n")
            for _, row in resp_df.iterrows():
                f.write(f"| {row['timestamp']} | {row['evento']} | {row['detalle']} |\n")
        else:
            f.write("No hay registros de Respuestas procesadas en la Caja Negra.\n")
            
    print("Reporte generado exitosamente.")

if __name__ == '__main__':
    generar_reporte()
