from PIL import Image, ImageDraw, ImageFont
import os

def add_text_to_image():
    image_path = "setup_cover.jpg"
    # Change output to BMP
    output_path = "Resources/installer_cover_v1.5.3.bmp"
    
    if not os.path.exists("Resources"):
        os.makedirs("Resources")

    try:
        img = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image: {e}")
        return

    draw = ImageDraw.Draw(img)
    
    # Text settings
    text = "AO Development"
    
    # Try to load a font, fallback to default
    try:
        # Try a nice font if available, otherwise default
        font = ImageFont.truetype("arial.ttf", 40)
    except IOError:
        font = ImageFont.load_default()
    
    width, height = img.size
    
    # Get text text box
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    text_width = right - left
    text_height = bottom - top
    
    x = (width - text_width) / 2
    y = height - (height * 0.2) # 20% from bottom
    
    # Draw simple shadow for readability
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill="black")
    draw.text((x, y), text, font=font, fill="white")
    
    # Save as BMP
    img.save(output_path, "BMP")
    print(f"Image saved to {output_path}")

if __name__ == "__main__":
    add_text_to_image()
