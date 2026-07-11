import sqlite3
import json
from datetime import datetime

DB_PATH = r'C:\Users\josem\Downloads\bot-cpsl-review\caja_negra.db'

def actualizar_memoria_corporativa():
    print("--- INICIANDO ACTUALIZACIÓN DE MEMORIA CORPORATIVA EN CAJA NEGRA ---")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Crear tabla de memoria si no existe
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memoria_corporativa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bloque TEXT UNIQUE,
            contenido TEXT,
            metadata TEXT,
            ultima_actualizacion TEXT
        )
    ''')

    # 2. Definir Bloques con Trazabilidad (Metadata)
    bloques = [
        {
            "bloque": "FILOSOFIA_Y_CULTURA",
            "contenido": "5 Pilares: Impecabilidad, Liderazgo Consciente, Excelencia Operativa, Servicio WOW, Integridad Total. Accountability Saludable ('Nada se justifica, todo se responde'). Estándar Irrazonable (visión + disciplina). Identidad Cuántica (metáfora de expansión).",
            "meta": {
                "fuente": "Manual Corporativo 2026 / Instrucción Usuario",
                "fecha_creacion": "2026-05-11",
                "version": "1.0",
                "aprobado_por": "Dirección Global",
                "aplica_a": "Todas las sedes",
                "vigencia": "2026-12-31",
                "tags": ["filosofía", "cultura"]
            }
        },
        {
            "bloque": "ESTRUCTURA_Y_RUTAS",
            "contenido": "Ruta: Participante -> Aliado -> Capitán -> Coordinación. Ratio 1:6 innegociable. Roles: Gerente (Compliance), Coordinador (CEO Salón), Capitán (Táctico), Quantum Team (Respuesta Rápida).",
            "meta": {
                "fuente": "Manual Global de Colaboradores 2026",
                "fecha_creacion": "2026-05-11",
                "version": "1.0",
                "aprobado_por": "Gerencia Global",
                "aplica_a": "Staff Operativo",
                "vigencia": "2026-12-31",
                "tags": ["estructura", "rrhh"]
            }
        },
        {
            "bloque": "SEGURIDAD_Y_CONFIDENCIALIDAD",
            "contenido": "Caída Confianza (4.5m, equipo certificado). Vuelos (pulseritas, 1:2). Caminata Fuego (Responsiva, Hombre Fuego). Datos nunca en canales no seguros.",
            "meta": {
                "fuente": "Manual Operativo C1/C2 2026",
                "fecha_creacion": "2026-05-11",
                "version": "1.1",
                "aprobado_por": "Dirección de Seguridad",
                "aplica_a": "Coordinadores/Capitanes",
                "vigencia": "2026-06-30",
                "tags": ["seguridad", "compliance"]
            }
        },
        {
            "bloque": "KPIS_Y_BONOS",
            "contenido": "Conversión C1->C2->MJ. Bono Ciclo de Oro (90% graduación MJ + 90% enrolamiento). Metas 2026 sedes LATAM.",
            "meta": {
                "fuente": "Manual Operativo / Plan Estratégico 2026",
                "fecha_creacion": "2026-05-11",
                "version": "1.0",
                "aprobado_por": "Dirección Comercial",
                "aplica_a": "Sedes",
                "vigencia": "2026-12-31",
                "tags": ["KPI", "bonos"]
            }
        },
        {
            "bloque": "CALENDARIO_GLOBAL",
            "contenido": "Reglas de Interfaz: 1. Siempre orden cronológico. 2. Orden de Sedes exacto: QUITO C1, QUITO C2, GUAYAQUIL, LIMA, CUENCA, MEDELLÍN, CDMX. 3. Sin duplicados en DB, unificación mediante deduplicate_db.py. 4. Estética de Equipos: Asteriscos (ej: 21*22*23) se formatean con espacios (21 22 23). El calendario debe ser automático y vivo (polling/sync cada 30s).",
            "meta": {
                "fuente": "Instrucción de Dirección Global - Ecosistema",
                "fecha_creacion": "2026-07-11",
                "version": "1.0",
                "aprobado_por": "Dirección Global",
                "aplica_a": "Desarrolladores y Plataforma",
                "vigencia": "Indefinida",
                "tags": ["calendario", "interfaz", "sincronización"]
            }
        }
    ]

    ahora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for b in bloques:
        cursor.execute('''
            INSERT OR REPLACE INTO memoria_corporativa (bloque, contenido, metadata, ultima_actualizacion)
            VALUES (?, ?, ?, ?)
        ''', (b['bloque'], b['contenido'], json.dumps(b['meta']), ahora))
    
    # Registrar la actualización en el log general de la Caja Negra
    cursor.execute('''
        INSERT INTO logs (timestamp, categoria, evento, detalle, estado)
        VALUES (?, ?, ?, ?, ?)
    ''', (ahora, 'SYSTEM', 'AUDITORIA_INTEGRACION', 'Integración de 4 bloques de memoria corporativa con trazabilidad completa.', 'COMPLETO'))

    conn.commit()
    conn.close()
    print("Actualización de Memoria Corporativa completada con éxito.")

if __name__ == "__main__":
    actualizar_memoria_corporativa()
