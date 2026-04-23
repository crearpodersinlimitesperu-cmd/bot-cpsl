import os, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('bot_whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update imports
old_import = '''    from casos_derivados import (
        abrir_caso, cerrar_caso, actualizar_caso,
        casos_abiertos, casos_para_followup,
        marcar_notificado, resumen_casos
    )'''
new_import = '''    from casos_derivados import (
        abrir_caso, cerrar_caso, actualizar_caso,
        casos_abiertos, casos_para_followup,
        marcar_notificado, resumen_casos, casos_cerrados
    )'''
content = content.replace(old_import, new_import)

old_except = '''    def casos_abiertos(*a,**k): return []
    def casos_para_followup(*a,**k): return []'''
new_except = '''    def casos_abiertos(*a,**k): return []
    def casos_cerrados(*a,**k): return []
    def casos_para_followup(*a,**k): return []'''
content = content.replace(old_except, new_except)

# 2. Update VER_CASOS logic
old_ver_casos = '''        if not mis_casos:
            wa(tel,
               f"✅ *Sin casos derivados pendientes.*\\n\\n"
               f"🌟 ¡Excelente gestión, {nom}!\\n\\n0️⃣ Menú",
               f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
            return'''

new_ver_casos = '''        archivados = casos_cerrados(cc_key_act, limite=5)
        if not mis_casos:
            msg = f"✅ *Sin casos derivados pendientes.*\\n🌟 ¡Excelente gestión, {nom}!\\n\\n"
            if archivados:
                msg += f"📦 Tienes {len(archivados)} casos en tu archivo.\\n\\n8️⃣ Ver mi archivo\\n0️⃣ Menú principal"
                s["st_cc"] = "MAIN"; set_s(tel, s)  # Permitiremos que 8️⃣ lo lleve al archivo desde MAIN
            else:
                msg += f"0️⃣ Menú"
                s["st_cc"] = "MAIN"; set_s(tel, s)
            wa(tel, msg, f"SIS→{nom}")
            return'''

content = content.replace(old_ver_casos, new_ver_casos)

old_list = '''            lineas.append(
                f"{i}️⃣ {em} *{npx}*\\n"
                f"   📝 {asunto}\\n"
                f"   ⏱️ {c.get('ts_apertura','')[11:16]}"
            )
        lineas.append(f"\\nResponde el número para gestionar el caso.\\n0️⃣ Menú")'''

new_list = '''            lineas.append(
                f"{i}️⃣ {em} *{npx}*\\n"
                f"   📝 {asunto}\\n"
                f"   ⏱️ {c.get('ts_apertura','')[11:16]}"
            )
        lineas.append(f"\\nResponde el número para gestionar el caso.\\n8️⃣ Ver mis casos archivados\\n0️⃣ Menú")'''

content = content.replace(old_list, new_list)

# 3. Add VER_ARCHIVADOS state handling
old_menu_cc = '''        elif up == "4":
            s["st_cc"] = "VER_CASOS"'''
new_menu_cc = '''        elif up == "4":
            s["st_cc"] = "VER_CASOS"
        elif up == "8":
            s["st_cc"] = "VER_ARCHIVADOS"'''
content = content.replace(old_menu_cc, new_menu_cc)

old_elif = '''    elif st == "VER_CASOS":'''
new_elif = '''    elif st == "VER_ARCHIVADOS":
        cc_key_act = s.get("cc_key","")
        archivados = casos_cerrados(cc_key_act, limite=15)
        
        if up in {"0","VOLVER","SALIR","9"}:
            s["st_cc"] = "MAIN"; set_s(tel, s)
            _menu_cc(tel, nom); return
            
        if not archivados:
            wa(tel, "No tienes casos en tu archivo.\\n\\n0️⃣ Menú", f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
            return
            
        lineas = [f"📦 *Tus Últimos Casos Archivados ({len(archivados)}):*\\n"]
        for c in archivados:
            npx = c.get("nombre","?")[:25]
            asunto = c.get("ultimo_comentario") or "Resuelto"
            ts_c = c.get("ts_cierre","")[:16].replace("T", " ")
            lineas.append(f"✅ *{npx}*\\n   🗒️ {asunto[:40]}\\n   📅 {ts_c}\\n")
            
        lineas.append("\\n0️⃣ Volver al menú")
        wa(tel, "\\n".join(lineas), f"SIS→{nom}")
        
    elif st == "VER_CASOS":'''

if 'elif st == "VER_ARCHIVADOS":' not in content:
    content = content.replace(old_elif, new_elif)

# Also support 8 in VER_CASOS to go to VER_ARCHIVADOS
old_ver_casos_0 = '''        if up in {"0","VOLVER","SALIR"}:
            s["st_cc"] = "MAIN"; set_s(tel, s)
            _menu_cc(tel, nom); return'''

new_ver_casos_0 = '''        if up in {"0","VOLVER","SALIR"}:
            s["st_cc"] = "MAIN"; set_s(tel, s)
            _menu_cc(tel, nom); return
        if up == "8":
            s["st_cc"] = "MAIN"; set_s(tel, s)  # Hacky way to route to archivados
            _flujo_cc(tel, "MAIN", "8", cc_info); return'''
content = content.replace(old_ver_casos_0, new_ver_casos_0)


with open('bot_whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch archivados applied")
