import os
import json
from datetime import datetime
from database import SessionLocal, Usuario, TrazabilidadPX, LogEnvio

class DashboardEngine:
    """
    Generates the Strategic Impact Dashboard for CREAR GLOBAL.
    Translates raw behavioral data into executive insights.
    """
    def __init__(self):
        self.base_dir = os.path.dirname(__file__)
        self.output_path = os.path.join(self.base_dir, "dashboard_estrategico.html")

    def get_analytics_data(self):
        db = SessionLocal()
        try:
            participants = db.query(Usuario).filter(Usuario.tipo == "PX").all()
            total_px = len(participants)
            
            # Emotional Scoring Aggregates
            avg_score = sum(px.px_score for px in participants) / total_px if total_px > 0 else 0
            high_engagement = len([px for px in participants if (px.px_score or 0) >= 100])
            
            # Journey Stages
            stages = {}
            for px in participants:
                stage = px.journey_stage or "NEW"
                stages[stage] = stages.get(stage, 0) + 1
            
            # At-Risk Detection
            at_risk = [px for px in participants if px.journey_stage == "AT_RISK" or (px.px_score or 0) < 5]
            
            # Dispatch Stats
            logs = db.query(LogEnvio).limit(100).all()
            total_sent = len([l for l in logs if l.status_code == 200])
            
            return {
                "total_px": total_px,
                "avg_score": round(avg_score, 1),
                "high_engagement": high_engagement,
                "stages": stages,
                "at_risk_count": len(at_risk),
                "at_risk_list": [{"nombre": px.nombre, "score": px.px_score, "last": str(px.last_interaction)[:16]} for px in at_risk[:5]],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        finally:
            db.close()

    def generate_html(self):
        data = self.get_analytics_data()
        
        # Journey Stage breakdown for JS
        stages_labels = list(data['stages'].keys())
        stages_values = list(data['stages'].values())

        html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CREAR Experience Cloud™ — Strategic Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --navy: #1a1a2e;
            --gold: #b49632;
            --white: #ffffff;
            --gray-bg: #f8f9fa;
            --text-dark: #333333;
            --text-light: #999999;
        }}
        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--gray-bg);
            color: var(--text-dark);
            margin: 0;
            padding: 0;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .header {{
            background-color: var(--navy);
            width: 100%;
            padding: 40px 0;
            color: var(--white);
            text-align: center;
            border-bottom: 5px solid var(--gold);
        }}
        .header h1 {{ margin: 0; font-size: 28px; letter-spacing: 2px; text-transform: uppercase; }}
        .header p {{ margin: 10px 0 0; font-size: 14px; color: var(--gold); letter-spacing: 4px; font-weight: 300; }}
        
        .container {{ width: 90%; max-width: 1200px; padding: 40px 0; }}
        
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .kpi-card {{
            background: var(--white);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
            text-align: center;
        }}
        .kpi-card .value {{ font-size: 42px; font-weight: 800; color: var(--navy); }}
        .kpi-card .label {{ font-size: 12px; color: var(--text-light); text-transform: uppercase; letter-spacing: 2px; margin-top: 10px; }}
        
        .main-grid {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
        }}
        .chart-box, .risk-box {{
            background: var(--white);
            padding: 30px;
            border-radius: 12px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.05);
        }}
        .box-title {{ font-size: 18px; font-weight: 600; margin-bottom: 20px; color: var(--navy); border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        
        .risk-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .risk-item:last-child {{ border: none; }}
        .risk-name {{ font-weight: 600; font-size: 14px; }}
        .risk-score {{ color: #e74c3c; font-weight: 800; }}
        
        .footer {{ margin-top: 40px; padding: 20px; color: var(--text-light); font-size: 10px; letter-spacing: 1px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>CREAR Experience Cloud™</h1>
        <p>Strategic Transformation Dashboard</p>
    </div>

    <div class="container">
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="value">{data['total_px']}</div>
                <div class="label">Almas en el Sistema</div>
            </div>
            <div class="kpi-card">
                <div class="value">{data['avg_score']}</div>
                <div class="label">Score Emocional Promedio</div>
            </div>
            <div class="kpi-card">
                <div class="value">{data['high_engagement']}</div>
                <div class="label">High Engagement (Score > 100)</div>
            </div>
            <div class="kpi-card">
                <div class="value" style="color: #e74c3c;">{data['at_risk_count']}</div>
                <div class="label">Alertas de Atención Prioritaria</div>
            </div>
        </div>

        <div class="main-grid">
            <div class="chart-box">
                <div class="box-title">Distribución por Etapa del Journey</div>
                <canvas id="journeyChart"></canvas>
            </div>
            <div class="risk-box">
                <div class="box-title">Detección de Riesgo de Deserción</div>
                <div id="riskList">
                    {"".join([f'<div class="risk-item"><div class="risk-name">{px["nombre"]}</div><div class="risk-score">{px["score"]} PTS</div></div>' for px in data['at_risk_list']])}
                </div>
                <p style="font-size: 11px; color: var(--text-light); margin-top: 20px; text-align: center;">Acción Recomendada: Contacto por Coordinador</p>
            </div>
        </div>
    </div>

    <div class="footer">
        © 2026 CREAR GLOBAL | GENERADO: {data['timestamp']} | REPORTE INSTITUCIONAL DE ALTA FIDELIDAD
    </div>

    <script>
        const ctx = document.getElementById('journeyChart').getContext('2d');
        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(stages_labels)},
                datasets: [{{
                    label: 'Participantes',
                    data: {json.dumps(stages_values)},
                    backgroundColor: '#1a1a2e',
                    borderColor: '#b49632',
                    borderWidth: 2,
                    borderRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{ beginAtZero: true, grid: {{ display: false }} }},
                    x: {{ grid: {{ display: false }} }}
                }},
                plugins: {{
                    legend: {{ display: false }}
                }}
            }}
        }});
    </script>
</body>
</html>
        """
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        return self.output_path

if __name__ == "__main__":
    engine = DashboardEngine()
    path = engine.generate_html()
    print(f"Dashboard estratégico generado: {path}")
