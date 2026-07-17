import sys
import subprocess
import math

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
    from PIL import Image
    import imageio
except ImportError:
    install('Pillow')
    install('imageio')
    from PIL import Image
    import imageio

image_path = r"C:\Users\josem\.gemini\antigravity\brain\bae479b6-642b-4b11-b3f1-41c739f318e1\astronaut_dog_and_cat_1779916804166.png"
out_path = r"C:\Users\josem\Downloads\sticker_animado_gato.webp"

print("Loading image...")
img = Image.open(image_path).convert("RGBA")
width, height = img.size

frames = []
num_frames = 24  # Smooth 24 frames
max_zoom = 1.08  # 8% zoom

print("Generating frames...")
for i in range(num_frames):
    # Sinusoidal zoom for smooth in and out (looping)
    progress = i / num_frames
    scale = 1.0 + (max_zoom - 1.0) * math.sin(progress * math.pi)
    
    new_w = int(width / scale)
    new_h = int(height / scale)
    
    left = (width - new_w) // 2
    top = (height - new_h) // 2
    right = left + new_w
    bottom = top + new_h
    
    cropped = img.crop((left, top, right, bottom))
    resized = cropped.resize((width, height), Image.Resampling.LANCZOS)
    frames.append(resized)

print("Saving animated WebP...")
imageio.mimsave(out_path, frames, format='WEBP', duration=100, loop=0)
print(f"Animated sticker saved to {out_path}")
