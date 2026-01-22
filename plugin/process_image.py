from PIL import Image, ImageDraw, ImageFont
import os

def process_images():
    image_path = "setup_cover.jpg" # The source JPG
    output_large = "Resources/installer_cover_v1.5.3.bmp"
    output_small = "Resources/installer_small_v1.5.3.bmp"
    
    if not os.path.exists("Resources"):
        os.makedirs("Resources")

    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    # Process Large Image (WizardImageFile)
    # Ensure RGB mode (24-bit) which is what Inno Setup expects. 
    # PIL might save as 32-bit if RGBA.
    img_large = img.convert("RGB")
    
    draw = ImageDraw.Draw(img_large)
    
    # Text settings
    text = "AO Development"
    
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    width, height = img_large.size
    
    # Get text text box
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    
    x = (width - text_width) / 2
    y = height - (height * 0.2) 
    
    # Draw simple shadow
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")
    
    # Save Large BMP
    img_large.save(output_large, "BMP")
    print(f"Saved large image to {output_large}")


    # Process Small Image (WizardSmallImageFile)
    # Standard size is usually around 55x55 to 64x64.
    # We will resize the original image to 55x55 (cropping might be better but resize is safer for now)
    img_small = img.convert("RGB")
    img_small = img_small.resize((55, 55))
    img_small.save(output_small, "BMP")
    print(f"Saved small image to {output_small}")

if __name__ == "__main__":
    process_images()
