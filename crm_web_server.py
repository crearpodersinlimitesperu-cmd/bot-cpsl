from flask import Flask, render_template, jsonify, request
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR))

# --- DASHBOARD DATA API ---

@app.route('/')
def index():
    return render_template('crm_dashboard.html')

@app.route('/api/dashboard-stats', methods=['GET'])
def get_dashboard_stats():
    """Pulls REAL data from torre_control.db to power the dashboard."""
    import sqlite3
    TC_DB = str(BASE_DIR / "torre_control.db")
    CN_DB = str(BASE_DIR / "caja_negra.db")
    try:
        conn = sqlite3.connect(TC_DB)
        c = conn.cursor()

        # Core counts from torre_control.db
        total = c.execute("SELECT COUNT(*) FROM participantes").fetchone()[0]
        activos = c.execute("SELECT COUNT(*) FROM participantes WHERE estado='ACTIVO'").fetchone()[0]
        # Graduados son los que tienen el estado de GRADUADO_COMPLETO
        graduados = c.execute("SELECT COUNT(*) FROM participantes WHERE estado='GRADUADO_COMPLETO'").fetchone()[0]
        pendientes = c.execute("SELECT COUNT(*) FROM participantes WHERE estado='PENDIENTE'").fetchone()[0]

        # Desertores: check if table exists
        try:
            desertores = c.execute("SELECT COUNT(*) FROM desertores").fetchone()[0]
        except:
            desertores = c.execute("SELECT COUNT(*) FROM participantes WHERE estado LIKE '%DESERTOR%'").fetchone()[0]

        c1_si = c.execute("SELECT COUNT(*) FROM participantes WHERE c1='SI'").fetchone()[0]
        c2_si = c.execute("SELECT COUNT(*) FROM participantes WHERE c2='SI'").fetchone()[0]

        # Email bounce / hygiene
        try:
            bounces = c.execute("SELECT COUNT(*) FROM participantes WHERE estado_respuesta_sms='EMAIL_BOUNCED'").fetchone()[0]
            replied = c.execute("SELECT COUNT(*) FROM participantes WHERE estado_respuesta_sms='RECEIVED_EMAIL'").fetchone()[0]
        except:
            bounces = 0
            replied = 0

        # Per coordinator
        r_cc = c.execute(
            "SELECT cc_nombre, COUNT(*) as total FROM participantes "
            "WHERE cc_nombre IS NOT NULL GROUP BY cc_nombre ORDER BY total DESC LIMIT 5"
        ).fetchall()
        por_cc = [{"name": row[0], "total": row[1]} for row in r_cc]

        # Per equipo (top 7 active)
        r_eq = c.execute(
            "SELECT equipo, COUNT(*) as total FROM participantes "
            "WHERE estado='ACTIVO' GROUP BY equipo ORDER BY total DESC LIMIT 7"
        ).fetchall()
        por_equipo = [{"equipo": row[0], "total": row[1]} for row in r_eq]

        conn.close()

        # Activity from caja_negra.db (if available)
        actividad = []
        try:
            conn2 = sqlite3.connect(CN_DB)
            r_cb = conn2.execute(
                "SELECT timestamp, accion, px_nombre, canal, resultado FROM caja_negra "
                "ORDER BY timestamp DESC LIMIT 10"
            ).fetchall()
            actividad = [
                {
                    "timestamp": str(row[0])[:16] if row[0] else "—",
                    "accion": row[1],
                    "px_nombre": row[2],
                    "canal": row[3],
                    "resultado": row[4]
                }
                for row in r_cb
            ]
            conn2.close()
        except:
            pass

        # Conversion rates
        tasa_c1 = round((c1_si / total) * 100, 1) if total > 0 else 0
        tasa_c2 = round((c2_si / total) * 100, 1) if total > 0 else 0
        tasa_graduados = round((graduados / total) * 100, 1) if total > 0 else 0
        tasa_desercion = round((desertores / total) * 100, 1) if total > 0 else 0

        return jsonify({
            "status": "success",
            "kpis": {
                "total_participantes": total,
                "activos": activos,
                "graduados": graduados,
                "pendientes": pendientes,
                "desertores": desertores,
                "c1_completados": c1_si,
                "c2_completados": c2_si,
                "email_bounces": bounces,
                "email_replied": replied,
                "tasa_c1": tasa_c1,
                "tasa_c2": tasa_c2,
                "tasa_graduados": tasa_graduados,
                "tasa_desercion": tasa_desercion,
            },
            "por_coordinadora": por_cc,
            "por_equipo": por_equipo,
            "actividad_reciente": actividad
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# --- OPERATIONS API ---

@app.route('/api/hygiene', methods=['POST'])
def run_hygiene():
    try:
        from crear_hygiene_core import EmailHygiene
        hygiene = EmailHygiene()
        fixed, invalid = hygiene.sanitize_database()
        return jsonify({
            "status": "success",
            "message": f"Escaneo completado. {fixed} correos corregidos, {invalid} en cuarentena.",
            "data": {"fixed": fixed, "invalid": invalid}
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/watchtower', methods=['POST'])
def run_watchtower():
    try:
        from crear_alert_system import ExperienceWatchtower
        watchtower = ExperienceWatchtower()
        alerts = watchtower.scan_for_risks()
        watchtower.trigger_coordinator_notifications(alerts)
        return jsonify({
            "status": "success",
            "message": f"Escaneo completado. {len(alerts)} alertas de riesgo generadas."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/logistics', methods=['POST'])
def run_logistics():
    try:
        import test_logistics
        test_logistics.test_logistics_flight_tracking()
        return jsonify({
            "status": "success",
            "message": "Sincronización de vuelos ejecutada. Correos y SMS enviados."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/analytics', methods=['POST'])
def run_analytics():
    try:
        import check_health
        check_health.check_phase1_health()
        return jsonify({
            "status": "success",
            "message": "Análisis de Fase 1 completado exitosamente."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/buscar', methods=['GET'])
def buscar_participante():
    """Buscador 360° dinámico — busca por palabras clave en cualquier orden en los campos del participante."""
    q = request.args.get('q', '').strip()
    if len(q) < 2:
        return jsonify({"status": "error", "message": "Mínimo 2 caracteres"}), 400

    try:
        words = q.split()
        if not words:
            return jsonify({"status": "success", "total": 0, "results": []})

        import sqlite3 as _sqlite3
        db_path = os.path.join(str(BASE_DIR), 'torre_control.db')
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        c = conn.cursor()

        clauses = []
        params = []
        
        # Blob de campos a buscar en minúsculas
        search_blob = """
            (LOWER(COALESCE(nombre, '')) || ' ' || 
             LOWER(COALESCE(apellido, '')) || ' ' || 
             LOWER(COALESCE(telefono, '')) || ' ' || 
             LOWER(COALESCE(email, '')) || ' ' || 
             LOWER(COALESCE(equipo, '')) || ' ' || 
             LOWER(COALESCE(imo, '')) || ' ' || 
             LOWER(COALESCE(identificacion, '')) || ' ' ||
             LOWER(COALESCE(estado, '')) || ' ' ||
             LOWER(COALESCE(maestria, '')))
        """

        for w in words:
            w_clause = f"{search_blob} LIKE ?"
            w_param = f"%{w.lower()}%"
            
            if w.isdigit():
                # Coincidencia de DNI ignorando ceros iniciales
                w_clause = f"({w_clause} OR REPLACE(LTRIM(COALESCE(identificacion,''), '0'), ' ', '') = REPLACE(LTRIM(?, '0'), ' ', ''))"
                params.extend([w_param, w])
            else:
                params.append(w_param)
                
            clauses.append(w_clause)

        where_sql = " AND ".join(clauses)

        # Criterios de ordenamiento:
        # 1. Coincidencia exacta de la frase en nombre+apellido
        # 2. Coincidencia de todas las palabras buscadas en nombre+apellido (en cualquier orden, con espacios de por medio)
        # 3. Alfabético por nombre
        full_name_sql = "(LOWER(COALESCE(nombre, '')) || ' ' || LOWER(COALESCE(apellido, '')))"
        name_order_clauses = " AND ".join([f"{full_name_sql} LIKE ?" for _ in words])
        
        order_sql = f"""
            CASE WHEN {full_name_sql} LIKE ? THEN 0 ELSE 1 END,
            CASE WHEN {name_order_clauses} THEN 0 ELSE 1 END,
            nombre ASC
        """

        # Parámetros del ordenamiento
        params.append(f"%{q.lower()}%")
        for w in words:
            params.append(f"%{w.lower()}%")

        query = f"""
            SELECT id, nombre, apellido, nombre_preferido, telefono, email,
                   equipo, imo, tel_imo, cc_nombre, cc_tel,
                   c1, c2, maestria, identificacion, estado,
                   resultado_gestion, tiene_cambio_cupo, observaciones,
                   fecha_registro, fecha_actualizacion
            FROM participantes
            WHERE {where_sql}
            ORDER BY {order_sql}
            LIMIT 50
        """

        c.execute(query, tuple(params))
        rows = c.fetchall()
        results = [dict(r) for r in rows]
        conn.close()

        return jsonify({
            "status": "success",
            "total": len(results),
            "results": results
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/run-op', methods=['POST'])
def run_op():
    """Ejecuta operaciones del sistema desde el dashboard."""
    data = request.json
    op = data.get('op')
    try:
        import subprocess
        if op == 'sync_global':
            subprocess.Popen(['python', 'scraper_asistencia_todos.py'])
            return jsonify({"status": "success", "message": "Scraper global iniciado en segundo plano. Tomará unos minutos."})
        elif op == 'sync_e28':
            subprocess.Popen(['python', 'scraper_asistencia_real_e28.py'])
            return jsonify({"status": "success", "message": "Scraper E28 iniciado en segundo plano."})
        else:
            return jsonify({"status": "error", "message": "Operación desconocida"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/fusionar', methods=['POST'])
def fusionar_perfiles():
    """Fusiona dos perfiles homónimos, consolidando datos en el principal y borrando el duplicado."""
    data = request.json
    id_principal = data.get('id_principal')
    id_duplicado = data.get('id_duplicado')
    
    if not id_principal or not id_duplicado or id_principal == id_duplicado:
        return jsonify({"status": "error", "message": "IDs no válidos para la fusión."}), 400
        
    try:
        import sqlite3 as _sqlite3
        db_path = os.path.join(str(BASE_DIR), 'torre_control.db')
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        c = conn.cursor()
        
        c.execute("SELECT * FROM participantes WHERE id = ?", (id_principal,))
        principal = c.fetchone()
        c.execute("SELECT * FROM participantes WHERE id = ?", (id_duplicado,))
        duplicado = c.fetchone()
        
        if not principal or not duplicado:
            conn.close()
            return jsonify({"status": "error", "message": "Uno de los participantes no existe."}), 404
            
        p_dict = dict(principal)
        d_dict = dict(duplicado)
        
        # Consolidar datos en principal
        update_fields = {}
        for key in d_dict.keys():
            if key in ['id', 'fecha_registro', 'fecha_actualizacion']:
                continue
            p_val = p_dict.get(key)
            d_val = d_dict.get(key)
            
            is_empty_p = p_val is None or str(p_val).strip() == "" or str(p_val).strip().upper() == "N/A"
            is_empty_d = d_val is None or str(d_val).strip() == "" or str(d_val).strip().upper() == "N/A"
            
            if is_empty_p and not is_empty_d:
                update_fields[key] = d_val
            elif key in ['c1', 'c2', 'maestria', 'tiene_cambio_cupo'] and p_val == 'NO' and d_val == 'SI':
                update_fields[key] = 'SI'
            elif key == 'estado' and p_val == 'PENDIENTE' and d_val == 'ACTIVO':
                update_fields[key] = 'ACTIVO'
                
        # Guardar cambios del principal si hay algo nuevo
        if update_fields:
            set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
            params = list(update_fields.values()) + [id_principal]
            c.execute(f"UPDATE participantes SET {set_clause}, fecha_actualizacion = CURRENT_TIMESTAMP WHERE id = ?", params)
            
        # Re-enrutar enrolados
        nombre_dup = f"{d_dict.get('nombre', '')} {d_dict.get('apellido', '')}".strip()
        nombre_pri = f"{p_dict.get('nombre', '')} {p_dict.get('apellido', '')}".strip()
        if nombre_dup and nombre_pri:
            c.execute("UPDATE participantes SET imo = ? WHERE imo = ?", (nombre_pri, nombre_dup))
            
        # Actualizar relaciones en la tabla 'relaciones' para evitar registros huérfanos
        c.execute("UPDATE relaciones SET px_id = ? WHERE px_id = ?", (id_principal, id_duplicado))
        c.execute("UPDATE relaciones SET relacionado_id = ?, nombre_relacionado = ? WHERE relacionado_id = ?", 
                  (id_principal, nombre_pri, id_duplicado))
            
        # Eliminar el registro duplicado
        c.execute("DELETE FROM participantes WHERE id = ?", (id_duplicado,))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "status": "success",
            "message": f"Fusión exitosa. El perfil '{nombre_dup}' (ID {id_duplicado}) fue fusionado con '{nombre_pri}' (ID {id_principal}) y eliminado.",
            "campos_actualizados": list(update_fields.keys())
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/participante/<int:px_id>', methods=['GET'])
def detalle_participante(px_id):
    """Ficha completa de un participante por ID, incluyendo sus enrolados y relaciones históricas."""
    try:
        import sqlite3 as _sqlite3
        db_path = os.path.join(str(BASE_DIR), 'torre_control.db')
        conn = _sqlite3.connect(db_path)
        conn.row_factory = _sqlite3.Row
        c = conn.cursor()

        c.execute("SELECT * FROM participantes WHERE id = ?", (px_id,))
        row = c.fetchone()

        if not row:
            conn.close()
            return jsonify({"status": "error", "message": "Participante no encontrado"}), 404

        part_dict = dict(row)

        # Buscar enrolados de la tabla participantes (campo imo coincidencia difusa)
        nombre_completo = f"{part_dict.get('nombre', '')} {part_dict.get('apellido', '')}".strip()
        enrolados = []
        if nombre_completo:
            n1 = f"%{part_dict.get('nombre', '')}%{part_dict.get('apellido', '')}%"
            n2 = f"%{part_dict.get('apellido', '')}%{part_dict.get('nombre', '')}%"
            c.execute("""
                SELECT id, nombre, apellido, equipo, identificacion, estado, c1, c2, maestria
                FROM participantes
                WHERE (imo LIKE ? OR imo LIKE ?) AND id != ?
                ORDER BY nombre ASC
            """, (n1, n2, px_id))
            enrolados = [dict(r) for r in c.fetchall()]

        # Buscar relaciones directas (de la tabla 'relaciones')
        # Estas indican quién es el Aliado C1, C2 o IMO de este participante
        c.execute("""
            SELECT r.relacionado_id, r.nombre_relacionado, r.tipo, r.contexto
            FROM relaciones r
            WHERE r.px_id = ?
        """, (px_id,))
        directas = c.fetchall()
        
        rel_c1 = []
        rel_c2 = []
        rel_imo = None
        
        for r in directas:
            t = r['tipo']
            info = {
                "relacionado_id": r['relacionado_id'],
                "nombre": r['nombre_relacionado'],
                "contexto": r['contexto']
            }
            if t == 'ALIADO_C1':
                rel_c1.append(info)
            elif t == 'ALIADO_C2':
                rel_c2.append(info)
            elif t == 'IMO':
                rel_imo = info

        # Buscar relaciones recíprocas (de la tabla 'relaciones')
        # Estas indican quién tiene a este participante como Aliado C1, Aliado C2 o IMO
        c.execute("""
            SELECT r.px_id, p.nombre, p.apellido, r.tipo, r.contexto
            FROM relaciones r
            JOIN participantes p ON r.px_id = p.id
            WHERE r.relacionado_id = ?
        """, (px_id,))
        reciprocas = c.fetchall()
        
        c1_de = []
        c2_de = []
        imo_de = []
        
        for r in reciprocas:
            t = r['tipo']
            info = {
                "id": r['px_id'],
                "nombre": f"{r['nombre']} {r['apellido']}".strip(),
                "contexto": r['contexto']
            }
            if t == 'ALIADO_C1':
                c1_de.append(info)
            elif t == 'ALIADO_C2':
                c2_de.append(info)
            elif t == 'IMO':
                imo_de.append(info)

        # Buscar trayectoria de apoyo/staff en la tabla 'trayectoria_staff'
        try:
            c.execute("""
                SELECT rol, capitulo, equipo_evento, sheet_name
                FROM trayectoria_staff
                WHERE px_id = ?
                ORDER BY equipo_evento DESC, capitulo ASC
            """, (px_id,))
            historial_staff = [dict(r) for r in c.fetchall()]
        except Exception as e_staff:
            import traceback
            traceback.print_exc()
            historial_staff = []

        conn.close()

        return jsonify({
            "status": "success",
            "participante": part_dict,
            "enrolados": enrolados,
            "rel_c1": rel_c1,
            "rel_c2": rel_c2,
            "rel_imo": rel_imo,
            "c1_de": c1_de,
            "c2_de": c2_de,
            "imo_de": imo_de,
            "historial_staff": historial_staff
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

def is_already_running(script_name):
    import os
    try:
        import psutil
        my_pid = os.getpid()
        my_ppid = os.getppid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                if name and 'python' in name.lower():
                    pid = proc.info['pid']
                    cmdline = proc.info['cmdline']
                    if cmdline:
                        cmdline_str = " ".join(cmdline)
                        if pid != my_pid and pid != my_ppid and script_name in cmdline_str:
                            return True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return False
    except:
        return False

if __name__ == '__main__':
    if is_already_running("crm_web_server.py"):
        print("[ERROR] El servidor web CRM ya se encuentra en ejecución en otro proceso.")
        sys.exit(1)
    app.run(host='0.0.0.0', port=5000, debug=False)
