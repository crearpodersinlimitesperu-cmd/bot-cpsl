import os, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('bot_whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Inject _en_entrenamiento at top
entrenamiento_code = '''
# ==========================================
# CALENDARIO DE ENTRENAMIENTOS LIMA
# ==========================================
def _en_entrenamiento():
    """Verifica si estamos en fechas de entrenamiento según el json del calendario."""
    try:
        import os, json
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=-5))
        hoy = datetime.now(tz).strftime("%Y-%m-%d")
        cal_path = "/data/calendario_entrenamientos.json" if os.path.exists("/data") else "calendario_entrenamientos.json"
        if os.path.exists(cal_path):
            with open(cal_path, "r", encoding="utf-8") as f:
                eventos = json.load(f)
                for ev in eventos:
                    if ev["inicio"] <= hoy <= ev["fin"]:
                        return ev["nombre"]
    except Exception as e:
        pass
    return None

def ahora(): return datetime.now(TZ_LIMA)
'''

if '_en_entrenamiento' not in content:
    content = content.replace('def ahora(): return datetime.now(TZ_LIMA)', entrenamiento_code)

# 2. Inject check inside flujo
old_flujo = '''        s = get_s(tel)

        # ── GERENTE JOSÉ — menú ejecutivo (L1) ─────────────────
        if tel == "51919563284":
            _flujo_gerente(tel, up, texto)
            return'''

new_flujo = '''        s = get_s(tel)

        # ── GERENTE JOSÉ — menú ejecutivo (L1) ─────────────────
        if tel == "51919563284":
            _flujo_gerente(tel, up, texto)
            return

        # ── AUTO-RESPUESTA DE ENTRENAMIENTO ────────────────────
        p = s.get("p") or perfil_crm(tel)
        s["p"] = p
        
        if p.get("tipo") in ("PX", "IMO", "NUEVO") and not s.get("notificado_entrenamiento"):
            evento_actual = _en_entrenamiento()
            if evento_actual:
                wa(tel, f"⚠️ *Aviso automático:*\\nActualmente todo el equipo se encuentra en el entrenamiento presencial *{evento_actual}*.\\n\\n_Nuestro tiempo de respuesta será mayor al habitual. Agradecemos tu paciencia. 🙏_", "SIS")
                s["notificado_entrenamiento"] = True
                set_s(tel, s)'''

if old_flujo in content:
    content = content.replace(old_flujo, new_flujo)
    print("Flujo modificado con auto-respuesta.")
else:
    print("No se encontro old_flujo")

with open('bot_whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch aplicado con éxito.")
