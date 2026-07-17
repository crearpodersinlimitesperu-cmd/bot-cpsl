"""
Módulo para la validación de la estructura del repositorio cloud.
Verifica la existencia de archivos críticos y configuraciones específicas.
"""
from pathlib import Path

def validate_repo():
    """
    Verifica la integridad del repositorio cloud comprobando archivos críticos,
    configuración de gateway y cron jobs.
    """
    print("--- VALIDANDO REPOSITORIO CLOUD ---")
    repo_path = Path("crear-poder-sin-limites-cloud")
    critical_files = [
        "requirements.txt",
        "config/render.yaml",
        "src/main.py",
        "src/pipeline.py",
        "src/database.py",
        "src/sms_gateway.py",
        ".env.example"
    ]

    missing = []
    for f in critical_files:
        if not (repo_path / f).exists():
            missing.append(f)

    if missing:
        print(f"❌ ERROR: Faltan archivos: {', '.join(missing)}")
    else:
        print("✅ ESTRUCTURA: Perfecta.")

    # Check MacroDroid in gateway
    gateway_content = (repo_path / "src/sms_gateway.py").read_text()
    if "MACRODROID_DEVICE_ID" in gateway_content:
        print("✅ SMS GATEWAY: Configurado para MacroDroid (Híbrido).")
    else:
        print("⚠️ SMS GATEWAY: No se detecta configuración de MacroDroid.")

    # Check Render YAML
    render_content = (repo_path / "config/render.yaml").read_text()
    if "0 13 * * *" in render_content:
        print("✅ SCHEDULER: Cron Jobs a las 8am (Lima) configurados.")

if __name__ == "__main__":
    validate_repo()
