import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('bot_whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Re-write CONFIRMAR_CASO and add NOTA_CASO
old_confirm = '''    elif st == "CONFIRMAR_CASO":
        tel_caso = s.get("caso_confirmando","")
        if up == "1":
            cerrar_caso(tel_caso, f"Resuelto por {nom_full}")
            wa(tel, "✅ Caso cerrado — registrado en el sistema.", f"SIS→{nom}")
            wa(JOSE_TEL,
               f"✅ *Caso cerrado* — {nom_full}\\n"
               f"PX: wa.me/{tel_caso}", "SIS→JOSE")
        elif up == "2":
            actualizar_caso(tel_caso, "EN_GESTION", f"En proceso por {nom_full}")
            wa(tel, "🔵 Registrado como En proceso.", f"SIS→{nom}")
        elif up == "3":
            actualizar_caso(tel_caso, "ABIERTO", f"Sin contacto — {nom_full} reporta")
            wa(tel, "❌ Registrado sin contacto. Se notificará a Gerencia.", f"SIS→{nom}")
            wa(JOSE_TEL,
               f"⚠️ *Sin contacto* — {nom_full}\\n"
               f"PX: wa.me/{tel_caso}", "SIS→JOSE")
        s.pop("caso_confirmando", None)
        s["st_cc"] = "VER_CASOS"
        set_s(tel, s)
        # Volver a mostrar lista actualizada
        mis_casos2 = casos_abiertos(s.get("cc_key",""))
        if mis_casos2:
            _flujo_cc(tel, "VER", texto, cc_info)  # re-mostrar lista
        else:
            wa(tel, "✅ Todos tus casos atendidos. Excelente trabajo!", f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
        return'''

new_confirm = '''    elif st == "CONFIRMAR_CASO":
        tel_caso = s.get("caso_confirmando","")
        JOSE_TEL = "51919563284"

        if up in {"0","VOLVER"}:
            s["st_cc"] = "VER_CASOS"; set_s(tel, s)
            _flujo_cc(tel, "VER", texto, cc_info); return

        if up == "4":  # Agregar nota
            s["st_cc"] = "NOTA_CASO"; set_s(tel, s)
            wa(tel,
               f"💬 *Agregar nota al caso*\\n\\n"
               f"Escribe tu nota (queda en el historial):\\n\\n"
               f"9️⃣ Cancelar",
               f"SIS→{nom}")
            return

        if up == "1":
            cerrar_caso(tel_caso, f"Resuelto por {nom_full}")
            wa(tel,
               f"✅ *Caso cerrado correctamente.*\\n"
               f"Registrado. Gerencia notificada. 👏",
               f"SIS→{nom}")
            wa(JOSE_TEL,
               f"✅ *CASO CERRADO* — Torre de Control\\n"
               f"CC: *{nom_full}*\\nPX: wa.me/{tel_caso}\\n"
               f"Hora: {ahora().strftime('%d/%m %H:%M')}",
               "SIS→GERENTE")
        elif up == "2":
            actualizar_caso(tel_caso, "EN_GESTION", f"Contactado — en proceso por {nom_full}")
            wa(tel,
               f"🟡 *Caso → En Gestión.*\\n"
               f"Recuerda actualizarlo cuando lo cierres.",
               f"SIS→{nom}")
        elif up == "3":
            actualizar_caso(tel_caso, "ABIERTO", f"Sin respuesta — {nom_full} reporta")
            wa(tel,
               f"🔴 *Sin contacto registrado.*\\n"
               f"Gerencia notificada para apoyo.",
               f"SIS→{nom}")
            wa(JOSE_TEL,
               f"⚠️ *SIN CONTACTO* — Torre de Control\\n"
               f"CC: *{nom_full}*\\nPX: wa.me/{tel_caso}\\n"
               f"Necesita apoyo para gestionar este caso.",
               "SIS→GERENTE")
        else:
            wa(tel,
               f"Responde: 1️⃣ Resolví  2️⃣ En proceso  3️⃣ Sin contacto  4️⃣ Nota  0️⃣ Volver",
               f"SIS→{nom}")
            return

        s.pop("caso_confirmando", None)
        s["st_cc"] = "VER_CASOS"; set_s(tel, s)
        mis_casos2 = casos_abiertos(s.get("cc_key",""))
        if mis_casos2:
            _flujo_cc(tel, "VER", texto, cc_info)
        else:
            wa(tel,
               f"🌟 *Todos tus casos atendidos.*\\n"
               f"¡Excelente gestión, {nom}!\\n\\n0️⃣ Menú",
               f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
        return

    elif st == "NOTA_CASO":
        tel_caso = s.get("caso_confirmando","")
        if up in {"9","VOLVER","CANCELAR"}:
            s["st_cc"] = "CONFIRMAR_CASO"; set_s(tel, s)
            _flujo_cc(tel, "VER", texto, cc_info); return
        # Guardar nota
        actualizar_caso(tel_caso, s.get("caso_estado_previo","ABIERTO"),
                        f"Nota de {nom_full}: {texto[:200]}")
        wa(tel,
           f"📝 *Nota registrada en el caso.*\\n\\n0️⃣ Menú | 4️⃣ Volver a mis casos",
           f"SIS→{nom}")
        s["st_cc"] = "VER_CASOS"; set_s(tel, s)
        return'''

if old_confirm in content:
    content = content.replace(old_confirm, new_confirm)
    print("CONFIRMAR_CASO replaced")
else:
    print("CONFIRMAR_CASO NOT FOUND")

with open('bot_whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patching complete.")
