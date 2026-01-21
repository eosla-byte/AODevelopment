
from PIL import Image
import os

source = r"C:\Users\arqui\.gemini\antigravity\scratch\AO_Development\plugin\Resources\LOGO AO DEV.png"
dest_32 = r"C:\Users\arqui\.gemini\antigravity\scratch\AO_Development\plugin\Resources\LOGO_AO_DEV_32.png"

try:
    with Image.open(source) as img:
        # Resize to 32x32 for Revit LargeImage
        img_32 = img.resize((32, 32), Image.Resampling.LANCZOS)
        img_32.save(dest_32)
        print(f"Created {dest_32}")
except Exception as e:
    print(f"Error: {e}")
