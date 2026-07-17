import sqlite3
import pandas as pd
from database import SessionLocal, Usuario, TrazabilidadPX, init_db
from datetime import datetime

OLD_DB = "torre_control.db"
NEW_DB = "caja_negra.db"

def migrar_memoria():
    print("--- INICIANDO MIGRACION FORENSE A CAJA NEGRA PRO ---")
    conn_old = sqlite3.connect(OLD_DB)
    db_new = SessionLocal()
    
    try:
        # 1. Cargar Participantes
        df_px = pd.read_sql_query("SELECT * FROM participantes", conn_old)
        print(f"Migrando {len(df_px)} registros de participantes...")
        
        for _, row in df_px.iterrows():
            # Crear Usuario
            u = Usuario(
                id=row['id'],
                nombre=f"{row['nombre']} {row['apellido']}",
                telefono=str(row['telefono']),
                email=str(row['email']),
                tipo="PX",
                cc_asignada=row['cc_nombre'],
                graduado=(row['c1'] == 'SI' or row['c2'] == 'SI'),
                created_at=datetime.utcnow()
            )
            db_new.merge(u) # Usar merge para evitar duplicados si ya existen
            
            # Inyectar trazabilidad si tiene un estado especial (e.g. rebote detectado)
            # Nota: En la DB anterior el estado de rebote se manejaba en observaciones o logs externos
            # Pero ya tenemos la lista de 498 rebotes en PATRONES_MAESTROS_2AÑOS.csv
            
        db_new.commit()
        print("   [OK] Usuarios migrados.")

        # 2. Inyectar Rebotes Historicos (498) en Trazabilidad
        try:
            df_rebotes = pd.read_csv("PATRONES_MAESTROS_2AÑOS.csv")
            rebotes = df_rebotes[df_rebotes['Tipo'] == 'REBOTE']
            print(f"Inyectando {len(rebotes)} eventos de rebote en la Trazabilidad 360...")
            
            for _, row in rebotes.iterrows():
                email = str(row['Email']).lower().strip()
                # Buscar al usuario por email para vincular la trazabilidad
                usuario = db_new.query(Usuario).filter(Usuario.email == email).first()
                if usuario:
                    t = TrazabilidadPX(
                        px_id=usuario.id,
                        canal="EMAIL",
                        tipo_evento="BOUNCE",
                        contenido=f"Rebote historico detectado: {row['Muestra']}",
                        metadatos='{"fuente": "AUDITORIA_FORENSE_2AÑOS"}',
                        timestamp=datetime.utcnow()
                    )
                    db_new.add(t)
            
            db_new.commit()
            print("   [OK] Trazabilidad de rebotes inyectada.")
            
        except Exception as e:
            print(f"   [!] Advertencia al inyectar rebotes: {e}")

    except Exception as e:
        print(f"Error critico en migracion: {e}")
        db_new.rollback()
    finally:
        conn_old.close()
        db_new.close()
        print("--- MIGRACION FINALIZADA ---")

if __name__ == "__main__":
    migrar_memoria()
