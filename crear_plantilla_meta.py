"""
crear_plantilla_meta.py — Crea la plantilla de WhatsApp en Meta
================================================================
Ejecutar UNA VEZ para registrar la plantilla "seguimiento_imo_nc"
en la cuenta de Meta Business.

Necesita: WA_TOKEN y WABA_ID como variables de entorno.
Para obtener WABA_ID, ve a business.facebook.com > WhatsApp > Configuracion > ID de la cuenta.
"""
import os, requests, json

WA_TOKEN = os.environ.get("WA_TOKEN", "")
WABA_ID = os.environ.get("WABA_ID", "")  # ID de la cuenta de WhatsApp Business
PHONE_ID = os.environ.get("WA_PHONE_ID", "1085205258006361")

TEMPLATE_NAME = "seguimiento_imo_nc"
TEMPLATE = {
    "name": TEMPLATE_NAME,
    "language": "es",
    "category": "UTILITY",
    "components": [
        {
            "type": "HEADER",
            "format": "TEXT",
            "text": "Seguimiento de participantes"
        },
        {
            "type": "BODY",
            "text": "Hola {{1}},\n\nSomos del equipo CREAR Lima. Los siguientes enrolados tuyos no contestan nuestras llamadas para el C1 E27:\n\n{{2}}\n\nTotal: {{3}} participantes\n\nTu coordinadora: {{4}}\nContactala: wa.me/{{5}}\n\nPor favor, responde con el nombre y situacion de cada participante.\nEj: \"Juan Perez - ya confirmo, asistira\"\n\nGracias por tu apoyo!",
            "example": {
                "body_text": [
                    ["Maria", "1. Juan Perez\n2. Ana Garcia", "2", "Diana Moscoso", "51912379744"]
                ]
            }
        },
        {
            "type": "FOOTER",
            "text": "CREAR Poder Sin Limites Peru"
        }
    ]
}


def crear_plantilla():
    if not WA_TOKEN:
        print("ERROR: Falta WA_TOKEN. Configura la variable de entorno.")
        return
    if not WABA_ID:
        print("ERROR: Falta WABA_ID.")
        print("Para obtenerlo:")
        print("  1. Ve a https://business.facebook.com")
        print("  2. WhatsApp > Configuracion")
        print("  3. Copia el 'ID de la cuenta de WhatsApp Business'")
        print("  4. SET WABA_ID=tu_id_aqui")
        return

    url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates"
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }

    print(f"Creando plantilla '{TEMPLATE_NAME}'...")
    r = requests.post(url, headers=headers, json=TEMPLATE, timeout=30)

    if r.status_code in (200, 201):
        data = r.json()
        print(f"EXITO! Template creada.")
        print(f"  ID: {data.get('id', 'N/A')}")
        print(f"  Status: {data.get('status', 'N/A')}")
        print(f"  La plantilla sera revisada por Meta (puede tardar minutos a horas).")
        print(f"\n  Una vez aprobada, configurar en Render:")
        print(f"    WA_TEMPLATE_IMO=seguimiento_imo_nc")
        print(f"    TEMPLATE_IMO_APROBADA=true")
    else:
        print(f"ERROR {r.status_code}: {r.text}")
        if "already exists" in r.text.lower():
            print("La plantilla ya existe. Puedes verificarla en Meta Business Suite.")


def listar_plantillas():
    """Lista las plantillas existentes."""
    if not WA_TOKEN or not WABA_ID:
        print("Faltan WA_TOKEN o WABA_ID")
        return

    url = f"https://graph.facebook.com/v19.0/{WABA_ID}/message_templates"
    headers = {"Authorization": f"Bearer {WA_TOKEN}"}
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        templates = r.json().get("data", [])
        print(f"Plantillas existentes ({len(templates)}):")
        for t in templates:
            print(f"  - {t['name']} [{t.get('status','?')}] ({t.get('language','?')})")
    else:
        print(f"Error: {r.text[:200]}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        listar_plantillas()
    else:
        crear_plantilla()
