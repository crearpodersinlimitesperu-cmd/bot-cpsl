import base64
from PIL import Image
import io

# Resize logo for email (160px wide)
img = Image.open(r'C:\Users\josem\Downloads\Imágenes\Logo Crear fb.png')
img = img.convert('RGBA')
ratio = 160 / img.width
new_h = int(img.height * ratio)
img = img.resize((160, new_h), Image.LANCZOS)

buf = io.BytesIO()
img.save(buf, format='PNG', optimize=True)
b64 = base64.b64encode(buf.getvalue()).decode()

# Read the template
with open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_bth.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Replace logo src with base64
logo_data_uri = f'data:image/png;base64,{b64}'
html = html.replace('src="cid:logo_crear"', f'src="{logo_data_uri}"')

# 2. Add new items to "Qué traer" section - saco/abrigo and no food
old_compromiso = '''&#128170; Tu Compromiso Total:</strong> Tu disposici&oacute;n a participar plenamente abrir&aacute; todas las puertas.</td></tr>
                                        </table>'''

new_items = '''&#128170; Tu Compromiso Total:</strong> Tu disposici&oacute;n a participar plenamente abrir&aacute; todas las puertas.</td></tr>
                                            <tr><td class="text-sub" style="padding: 4px 0; font-size: 14px; color: #444444; line-height: 1.6; font-family: Arial, Helvetica, sans-serif;"><strong>&#129507; Saco o Abrigo:</strong> El sal&oacute;n cuenta con aire acondicionado. Lleva una prenda de abrigo para tu comodidad.</td></tr>
                                            <tr><td class="text-sub" style="padding: 4px 0; font-size: 14px; color: #444444; line-height: 1.6; font-family: Arial, Helvetica, sans-serif;"><strong style="color: #c0392b;">&#128683; No se permite el ingreso de alimentos</strong> al sal&oacute;n del entrenamiento.</td></tr>
                                        </table>'''
html = html.replace(old_compromiso, new_items)

# 3. Replace placeholder names for preview
html = html.replace('{{NOMBRE}}', 'María')
html = html.replace('{{WHATSAPP_COORD}}', '51933599903')

# Write preview
with open(r'c:\Users\josem\Downloads\bot-cpsl-review\templates\email_c1_e28_preview.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Logo optimizado: {len(b64)} chars base64 ({len(buf.getvalue())/1024:.1f} KB)")
print("Preview actualizada con logo, nuevas indicaciones y botón funcional")
