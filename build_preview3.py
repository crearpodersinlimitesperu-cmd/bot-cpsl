html = open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html', 'r', encoding='utf-8').read()

# Replace cid: references with local files for preview
html = html.replace('src="cid:banner_c1_e28"', 'src="banner_c1_e28.jpg"')

# Replace placeholders
html = html.replace('{{NOMBRE}}', 'María')
html = html.replace('{{WHATSAPP_COORD}}', '51933599903')

with open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Preview lista con banner oficial del E28")
