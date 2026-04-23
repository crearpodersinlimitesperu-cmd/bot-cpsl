import os, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('bot_whatsapp.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_menu = '''       f"4️⃣ 📊 Ver mis casos derivados\\n"
       f"0️⃣ Salir\\n\\n"'''
new_menu = '''       f"4️⃣ 📊 Ver mis casos derivados\\n"
       f"8️⃣ 📦 Ver mis casos archivados\\n"
       f"0️⃣ Salir\\n\\n"'''

if old_menu in content:
    content = content.replace(old_menu, new_menu)
    with open('bot_whatsapp.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Menu patched")
else:
    print("Menu string not found")
