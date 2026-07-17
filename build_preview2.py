html = open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html', 'r', encoding='utf-8').read()

# Replace cid:logo with local file for preview
html = html.replace('src="cid:logo_crear"', 'src="logo_crear.png"')

# Replace placeholders
html = html.replace('{{NOMBRE}}', 'María')
html = html.replace('{{WHATSAPP_COORD}}', '51933599903')

with open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Preview lista con logo local")
