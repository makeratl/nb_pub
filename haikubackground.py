import time
import os
from chat_codegpt import chat_with_codegpt
import requests
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from datetime import datetime

def generate_image_prompt(haiku):
    prompt_request = f"Create an image prompt for a background that captures the essence of this haiku:\n{haiku}\nUse your rules for Haiku Background Prompt."
    return chat_with_codegpt(prompt_request)

def generate_image(prompt):
    base_url = "http://127.0.0.1:7801"
    auth_token = "Bearer homeauthcode"
    headers = {
        "Content-Type": "application/json",
        "Authorization": auth_token
    }

    # Create a new session
    session_response = requests.post(f"{base_url}/API/GetNewSession", headers=headers, json={})
    if session_response.status_code != 200:
        return "Failed to create session."
    
    session_data = session_response.json()
    session_id = session_data['session_id']

    # Generate image
    payload = {
        "session_id": session_id,
        "images": 1,
        "prompt": prompt,
        "model": "dreamshaperXL_lightningDPMSDE",
        "width": 1024,
        "height": 512,
        "steps": 8,
        "cfg_scale": 4.5,
        "sampler": "euler_ancestral",
        "seed": -1
    }

    print("Generating image...")
    start_time = time.time()

    response = requests.post(f"{base_url}/API/GenerateText2Image", json=payload, headers=headers)

    while response.status_code == 202:
        print(f"Image generation in progress... Time elapsed: {time.time() - start_time:.2f} seconds", end="\r")
        time.sleep(1)
        response = requests.get(f"{base_url}/API/CheckGenerationProgress", headers=headers, params={"session_id": session_id})

    if response.status_code == 200:
        json_response = response.json()
        if 'images' in json_response and json_response['images']:
            image_url = f"{base_url}/{json_response['images'][0]}"
            image_response = requests.get(image_url, headers=headers)
            if image_response.status_code == 200:
                filename = "haikubg.png"
                with open(filename, "wb") as file:
                    file.write(image_response.content)
                return f"Image generated and saved as '{filename}'"
    
    return "Failed to generate image."

def add_text_to_image(image_path, haiku, ai_headline, article_date, font_path, initial_font_size=40, text_color=(255, 255, 255, 255)):
    with Image.open(image_path) as img:
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        lines = haiku.split('\n')
        max_width = img.width * 0.9
        
        # Find the largest font size that fits all lines
        font_size = initial_font_size
        while font_size > 1:
            font = ImageFont.truetype(font_path, font_size)
            if all(draw.textlength(line, font=font) <= max_width for line in lines):
                break
            font_size -= 1
        
        # print(f"Selected font size: {font_size}")
        
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate text position and background size
        line_height = font.getbbox('A')[3] + 5
        total_text_height = line_height * len(lines)
        y_text = img.height // 3 - total_text_height // 2  # Move to upper third
        
        bg_width = max(draw.textlength(line, font=font) for line in lines) + 60
        bg_height = total_text_height + 60
        bg_left = (img.width - bg_width) // 2
        bg_top = y_text - 30
        
        draw.rounded_rectangle([bg_left, bg_top, bg_left + bg_width, bg_top + bg_height], 
                               radius=20, fill=(0, 0, 0, 160))
        
        for line in lines:
            text_width = draw.textlength(line, font=font)
            x_text = (img.width - text_width) // 2
            
            for offset in range(1, 3):
                draw.text((x_text + offset, y_text + offset), line, font=font, fill=(0, 0, 0, 128))
            
            draw.text((x_text, y_text), line, font=font, fill=text_color)
            y_text += line_height
        
        # Footer section
        footer_font_size = font_size // 2
        footer_font = ImageFont.truetype(font_path, footer_font_size)
        
        # Calculate footer height
        footer_height = 100  # Adjust this value as needed
        footer_top = img.height - footer_height
        
        # Draw transparent background for footer
        draw.rectangle([0, footer_top, img.width, img.height], fill=(0, 0, 0, 128))
        
        # AIHeadline
        headline_lines = textwrap.wrap(ai_headline, width=60)  # Adjust width as needed
        headline_y = footer_top + 10  # 10 pixels padding from top of footer
        
        for line in headline_lines:
            draw.text((20, headline_y), line, font=footer_font, fill=text_color)
            headline_y += footer_font.getbbox('A')[3] + 5
        
        # Date and @ainewsbrew
        date_font_size = footer_font_size - 4
        date_font = ImageFont.truetype(font_path, date_font_size)
        
        # Format the date, or use a default if it's empty or invalid
        try:
            if article_date:
                formatted_date = datetime.strptime(article_date, "%Y-%m-%d").strftime("%B %d, %Y")
            else:
                formatted_date = datetime.now().strftime("%B %d, %Y")
        except ValueError:
            print(f"Warning: Invalid date format '{article_date}'. Using current date.")
            formatted_date = datetime.now().strftime("%B %d, %Y")
        
        draw.text((20, img.height - 30), formatted_date, font=date_font, fill=text_color)
        
        ainewsbrew_width = draw.textlength("@ainewsbrew", font=date_font)
        draw.text((img.width - ainewsbrew_width - 20, img.height - 30), "@ainewsbrew", font=date_font, fill=text_color)
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        output_path = "haikubg_with_text.png"
        img.save(output_path)
        return output_path

def generate_haiku_background(haiku, ai_headline, article_date):
    # print(f"Received haiku:\n{haiku}\n")
    print("Generating image prompt based on the haiku...")
    image_prompt = generate_image_prompt(haiku)
    # print(f"\nGenerated image prompt:\n{image_prompt}\n")
    result = generate_image(image_prompt)
    # print(result)

    if "Image generated and saved as" in result:
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSerif-BoldItalic.ttf")
        
        if not os.path.exists(font_path):
            print(f"Warning: Font file not found at {font_path}. Using default font.")
            font_path = None  # This will use a default font

        # Add text to the image with enhanced visibility
        final_image = add_text_to_image("haikubg.png", haiku, ai_headline, article_date, font_path, initial_font_size=40)
        print(f"Haiku text added to image. Final image saved as '{final_image}'")
        return final_image
    
    return result

if __name__ == "__main__":
    # This block is for testing purposes only
    test_haiku = "Autumn moonlight—\na worm digs silently\ninto the chestnut."
    test_ai_headline = "Test Headline"
    test_article_date = "2022-01-01"
    generate_haiku_background(test_haiku, test_ai_headline, test_article_date)