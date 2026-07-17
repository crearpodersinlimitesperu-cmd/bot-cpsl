import sqlite3
import pandas as pd
import json
import os

def run_comprehensive_audit():
    db_path = r'C:\Users\josem\Downloads\bot-cpsl-review\torre_control.db'
    caja_negra_path = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'
    
    report = {}
    
    try:
        conn = sqlite3.connect(db_path)
        
        # 1. Total Participantes
        report['total_participantes'] = int(pd.read_sql("SELECT COUNT(*) as count FROM participantes", conn).iloc[0]['count'])
        
        # 2. Distribución de Estados
        report['estados'] = pd.read_sql("SELECT estado, COUNT(*) as count FROM participantes GROUP BY estado ORDER BY count DESC", conn).to_dict('records')
        
        # 3. Nombres Duplicados (Riesgo Crítico de Identidad)
        dup_names = pd.read_sql("""
            SELECT nombre, apellido, COUNT(*) as count 
            FROM participantes 
            GROUP BY nombre, apellido 
            HAVING count > 1 
            ORDER BY count DESC
        """, conn)
        report['nombres_duplicados'] = len(dup_names)
        report['top_nombres_duplicados'] = dup_names.head(5).to_dict('records')
        
        # 4. Emails Duplicados
        dup_emails = pd.read_sql("""
            SELECT email, COUNT(*) as count 
            FROM participantes 
            WHERE email IS NOT NULL AND email != ''
            GROUP BY email 
            HAVING count > 1 
            ORDER BY count DESC
        """, conn)
        report['emails_duplicados'] = len(dup_emails)
        
        # 5. Teléfonos Duplicados
        dup_phones = pd.read_sql("""
            SELECT telefono, COUNT(*) as count 
            FROM participantes 
            WHERE telefono IS NOT NULL AND telefono != ''
            GROUP BY telefono 
            HAVING count > 1 
            ORDER BY count DESC
        """, conn)
        report['telefonos_duplicados'] = len(dup_phones)
        
        # 6. Registros sin Email o Teléfono (Datos Inválidos)
        missing_data = pd.read_sql("""
            SELECT 
                SUM(CASE WHEN email IS NULL OR email = '' THEN 1 ELSE 0 END) as sin_email,
                SUM(CASE WHEN telefono IS NULL OR telefono = '' THEN 1 ELSE 0 END) as sin_telefono
            FROM participantes
        """, conn).iloc[0]
        report['sin_email'] = int(missing_data['sin_email'])
        report['sin_telefono'] = int(missing_data['sin_telefono'])
        
        # 7. Asignación de Coordinadoras (Regla Operativa)
        report['asignaciones'] = pd.read_sql("""
            SELECT cc_nombre, COUNT(*) as count 
            FROM participantes 
            GROUP BY cc_nombre
        """, conn).to_dict('records')
        
        conn.close()
        
        # 8. Estado de la Caja Negra
        if os.path.exists(caja_negra_path):
            conn_cn = sqlite3.connect(caja_negra_path)
            report['caja_negra_eventos'] = int(pd.read_sql("SELECT COUNT(*) as count FROM logs", conn_cn).iloc[0]['count'])
            report['caja_negra_tipos'] = pd.read_sql("SELECT evento, COUNT(*) as count FROM logs GROUP BY evento", conn_cn).to_dict('records')
            conn_cn.close()
        else:
            report['caja_negra_eventos'] = 0
            
    except Exception as e:
        report['error'] = str(e)
        
    with open(r'C:\Users\josem\Downloads\bot-cpsl-review\audit_results.json', 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_comprehensive_audit()
