import os, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')

with open('bot_whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add import for ia_chain
if 'from ia_chain import' not in content:
    content = content.replace('import requests as req_lib', 'import requests as req_lib\nfrom ia_chain import ia_detect_intent_cc, buscar_caso_por_nombre')

# 2. Re-write _menu_cc
old_menu = '''def _menu_cc(tel_cc, nom):
    """Menú principal para coordinadoras — incluye conteo de casos pendientes."""
    cc_key    = _CC_TELS.get(tel_cc, {}).get("key", "")
    mis_casos = casos_abiertos(cc_key) if cc_key else []
    urgentes  = sum(1 for c in mis_casos if c.get("estado") == "URGENTE")

    if mis_casos:
        alerta = f"\\n\\n⚠️ Tienes *{len(mis_casos)} caso(s) derivado(s)* pendiente(s)"
        if urgentes:
            alerta += f" — {urgentes} URGENTE{'S' if urgentes>1 else ''}"
        alerta += ".\\nUsa la opción 4 para confirmar atención."
    else:
        alerta = "\\n\\n✅ Sin casos derivados pendientes."

    wa(tel_cc,
       f"👋 Hola {nom}! — Torre de Control CPSL Lima"
       f"{alerta}\\n\\n"
       f"1️⃣ Enviar reporte del día\\n"
       f"2️⃣ Registrar confirmación de PX\\n"
       f"3️⃣ Reportar devolución\\n"
       f"4️⃣ Ver y confirmar mis casos derivados\\n"
       f"0️⃣ Salir\\n\\n"
       f"_Escribe el número de tu opción._",
       f"SIS→{nom}")'''

new_menu = '''def _menu_cc(tel_cc, nom):
    """Menú principal para coordinadoras con conteo de casos y acciones directas."""
    cc_key     = _CC_TELS.get(tel_cc, {}).get("key", "")
    mis_casos  = casos_abiertos(cc_key) if cc_key else []
    urgentes   = sum(1 for c in mis_casos if c.get("estado") == "URGENTE")
    en_gestion = sum(1 for c in mis_casos if c.get("estado") == "EN_GESTION")
    abiertos   = sum(1 for c in mis_casos if c.get("estado") == "ABIERTO")

    if mis_casos:
        if urgentes:
            alerta = f"\\n\\n🚨 *{urgentes} URGENTE{'S' if urgentes>1 else ''} + {abiertos+en_gestion} en seguimiento*"
        else:
            alerta = f"\\n\\n⏳ *{len(mis_casos)} caso(s) derivado(s) pendiente(s)*"
            if en_gestion:
                alerta += f" ({en_gestion} en gestión)"
    else:
        alerta = "\\n\\n✅ *Sin casos derivados pendientes.*"

    wa(tel_cc,
       f"🏆 *TORRE DE CONTROL — CPSL Lima*\\n"
       f"Hola {nom}!{alerta}\\n\\n"
       f"1️⃣ Reporte de llamadas del día\\n"
       f"2️⃣ Registrar confirmación de PX\\n"
       f"3️⃣ Reportar devolución\\n"
       f"4️⃣ 📊 Ver mis casos derivados\\n"
       f"0️⃣ Salir\\n\\n"
       f"💡 *Tip:* Puedes simplemente escribirme qué hiciste.\\n"
       f"_Ej: 'Resolví el caso de Bertha' o 'Le escribí a Juan'_",
       f"SIS→{nom}")'''

if old_menu in content:
    content = content.replace(old_menu, new_menu)
    print("Menu CC replaced")
else:
    print("Menu CC NOT FOUND")

# 3. Add AI Intent Detection at the top of _flujo_cc
old_flujo_start = '''    if st == "MAIN":
        # Respuestas rápidas al followup de casos (1=resuelto, 2=gestión, 3=apoyo)'''

new_flujo_start = '''    # ── IA DETECCIÓN DE INTENCIÓN (TEXTO LIBRE) ──
    # Si la CC escribe algo que no es una opción de menú (más de 5 letras)
    if st in {"MAIN", "VER_CASOS"} and len(texto) > 5 and not up.isdigit() and up not in {"HOLA","MENU","0","INICIO"}:
        intent_res = ia_detect_intent_cc(texto)
        if intent_res["intent"] in {"CERRAR_CASO", "ACTUALIZAR_CASO", "SIN_CONTACTO"}:
            mis_casos = casos_abiertos(cc_key)
            nombre_px = intent_res.get("nombre", "")
            caso_target = buscar_caso_por_nombre(nombre_px, mis_casos) if nombre_px else None
            
            if caso_target:
                tel_caso = caso_target["tel_px"]
                estado_nuevo = intent_res["estado"]
                
                if intent_res["intent"] == "CERRAR_CASO":
                    cerrar_caso(tel_caso, f"Resuelto por {nom_full} (Detectado IA)")
                    wa(tel, f"🤖 *Entendido {nom}.*\nHe cerrado el caso de *{caso_target['nombre']}* como RESUELTO. ✅", f"SIS→{nom}")
                    wa(JOSE_TEL, f"✅ *Caso cerrado* por {nom_full} (Vía IA)\nPX: wa.me/{tel_caso}", f"SIS→JOSE")
                else:
                    actualizar_caso(tel_caso, estado_nuevo, f"Actualizado por {nom_full} (Detectado IA)")
                    wa(tel, f"🤖 *Entendido {nom}.*\nHe actualizado el caso de *{caso_target['nombre']}* a {estado_nuevo}.", f"SIS→{nom}")
                
                # Volver al menú
                s["st_cc"] = "MAIN"
                set_s(tel, s)
                return
            elif nombre_px:
                wa(tel, f"🤖 *Detecté que quieres reportar a {nombre_px}*, pero no encontré un caso abierto con ese nombre. Usa la opción 4 para ver tu lista.", f"SIS→{nom}")
            else:
                wa(tel, f"🤖 *Detecté tu intención*, pero no pude identificar de qué participante hablas. Por favor, especifica el nombre o usa la opción 4.", f"SIS→{nom}")

    if st == "MAIN":
        # Respuestas rápidas al followup de casos (1=resuelto, 2=gestión, 3=apoyo)'''

if old_flujo_start in content:
    content = content.replace(old_flujo_start, new_flujo_start)
    print("Flujo CC intent detection added")
else:
    print("Flujo CC intent detection NOT FOUND")

# 4. Fix VER_CASOS to be cleaner
old_ver_casos = '''    elif st == "VER_CASOS":
        # CC está revisando sus casos — responde con número para confirmar
        cc_key_act = s.get("cc_key","")
        mis_casos  = casos_abiertos(cc_key_act)
        if not mis_casos:
            wa(tel, "✅ Sin casos derivados pendientes.", f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
            return
        # Mapeo número → caso
        mapa_casos = {str(i+1): c for i,c in enumerate(mis_casos[:9])}
        if up in mapa_casos:
            caso = mapa_casos[up]
            tel_px = caso.get("tel_px","")
            nom_px = caso.get("nombre","?")
            # Submenú de confirmación
            s["caso_confirmando"] = tel_px
            s["st_cc"] = "CONFIRMAR_CASO"
            set_s(tel, s)
            wa(tel,
               f"Caso seleccionado:\\n"
               f"*{nom_px}* (wa.me/{tel_px})\\n"
               f"Asunto: {caso.get('asunto_original') or caso.get('asunto','?')}\\n\\n"
               f"¿Cuál es el estado?\\n"
               f"1️⃣ Atendí y resolví ✅\\n"
               f"2️⃣ Contacté — en proceso 🔵\\n"
               f"3️⃣ No pude contactar ❌\\n"
               f"0️⃣ Volver a la lista",
               f"SIS→{nom}")
            return
        # Mostrar lista de casos
        lineas = ["*Tus casos derivados pendientes:*\\n"]
        for i,c in enumerate(mis_casos[:9],1):
            emoji = "🔴" if c.get("estado")=="URGENTE" else "⏳"
            lineas.append(f"{i}️⃣ {emoji} *{c.get('nombre','?')}*\\n"
                         f"   wa.me/{c.get('tel_px','')}\\n"
                         f"   {c.get('equipo','')} | {c.get('asunto','?')[:50]}\\n")
        lineas.append("\\nEscribe el *número* del caso para confirmar atención.\\n0️⃣ Volver al menú.")
        wa(tel, "\\n".join(lineas), f"SIS→{nom}")
        return'''

new_ver_casos = '''    elif st == "VER_CASOS":
        cc_key_act = s.get("cc_key","")
        mis_casos  = casos_abiertos(cc_key_act)

        if up in {"0","VOLVER","SALIR"}:
            s["st_cc"] = "MAIN"; set_s(tel, s)
            _menu_cc(tel, nom); return

        if not mis_casos:
            wa(tel,
               f"✅ *Sin casos derivados pendientes.*\\n\\n"
               f"🌟 ¡Excelente gestión, {nom}!\\n\\n0️⃣ Menú",
               f"SIS→{nom}")
            s["st_cc"] = "MAIN"; set_s(tel, s)
            return

        # Mapeo número → caso
        mapa_casos = {str(i+1): c for i,c in enumerate(mis_casos[:9])}
        if up in mapa_casos:
            caso    = mapa_casos[up]
            tel_px  = caso.get("tel_px","")
            nom_px  = caso.get("nombre","?")
            asunto  = caso.get("asunto_original") or caso.get("asunto","?")
            estado  = caso.get("estado","ABIERTO")
            ts_ap   = (caso.get("ts_apertura") or "")[:16].replace("T"," ")
            s["caso_confirmando"] = tel_px
            s["st_cc"] = "CONFIRMAR_CASO"
            set_s(tel, s)
            wa(tel,
               f"📌 *CASO SELECCIONADO*\\n"
               f"─────────────\\n"
               f"👤 *PX:* {nom_px}\\n"
               f"📱 wa.me/{tel_px}\\n"
               f"📝 *Asunto:* {asunto[:80]}\\n"
               f"🟡 *Estado:* {estado}\\n"
               f"─────────────\\n\\n"
               f"¿Qué hiciste con este caso?\\n\\n"
               f"1️⃣ ✅ Resolví — caso cerrado\\n"
               f"2️⃣ 📞 Lo contacté — en proceso\\n"
               f"3️⃣ ⏰ No pude contactar — pido apoyo\\n"
               f"4️⃣ 💬 Agregar nota al caso\\n"
               f"0️⃣ Volver a la lista",
               f"SIS→{nom}")
            return

        # Mostrar lista paginada (máx 9)
        emojis = {"URGENTE":"🔴","EN_GESTION":"🟡","ABIERTO":"🔵"}
        lineas = [f"📋 *Tus casos derivados ({len(mis_casos)} total):*\\n"]
        for i,c in enumerate(mis_casos[:9],1):
            em     = emojis.get(c.get("estado","ABIERTO"),"▪️")
            npx    = c.get("nombre","?")[:25]
            asunto = (c.get("asunto_original") or c.get("asunto","?"))[:40]
            lineas.append(
                f"{i}️⃣ {em} *{npx}*\\n"
                f"   📝 {asunto}\\n"
                f"   wa.me/{c.get('tel_px','')[:12]}\\n"
            )
        lineas.append("✏️ *Escribe el número* para gestionar, o escribe: *'Resolví el caso de <nombre>'*\\n0️⃣ Menú.")
        wa(tel, "\\n".join(lineas), f"SIS→{nom}")
        return'''

if old_ver_casos in content:
    content = content.replace(old_ver_casos, new_ver_casos)
    print("VER_CASOS replaced")
else:
    print("VER_CASOS NOT FOUND")


with open('bot_whatsapp.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patching complete.")
