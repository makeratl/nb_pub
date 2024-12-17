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
        return "Failed to create session.", prompt
    
    session_data = session_response.json()
    session_id = session_data['session_id']

    # Generate image
    payload = {
        "session_id": session_id,
        "images": 1,
        "prompt": prompt,
        "model": "dreamshaperXL_lightningDPMSDE",
        "width": 512,
        "height": 512,  # Change height to match width for square image
        "steps": 8,
        "cfg_scale": 4.5,
        "sampler": "euler_ancestral",
        "seed": -1
    }

    response = requests.post(f"{base_url}/API/GenerateText2Image", json=payload, headers=headers)

    while response.status_code == 202:
        time.sleep(1)
        response = requests.get(f"{base_url}/API/CheckGenerationProgress", headers=headers, params={"session_id": session_id})

    if response.status_code == 200:
        json_response = response.json()
        if 'images' in json_response and json_response['images']:
            image_url = f"{base_url}/{json_response['images'][0]}"
            image_response = requests.get(image_url, headers=headers)
            if image_response.status_code == 200:
                filename = "bluesky_haikubg.png"
                with open(filename, "wb") as file:
                    file.write(image_response.content)
                return filename, prompt
    
    return None, prompt

def add_text_to_image(image_path, haiku, article_date, font_path, initial_font_size=80, text_color=(255, 255, 255, 255)):
    with Image.open(image_path) as img:
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        lines = haiku.split('\n')
        max_width = img.width * 0.8  # Increased to 80% of image width
        
        # Find the largest font size that fits all lines
        font_size = initial_font_size
        while font_size > 1:
            font = ImageFont.truetype(font_path, font_size)
            if all(draw.textlength(line, font=font) <= max_width for line in lines):
                break
            font_size -= 1
        
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate text position and background size
        line_height = font.getbbox('A')[3] + 10  # Increased line spacing
        total_text_height = line_height * len(lines)
        y_text = (img.height - total_text_height) // 2  # Center vertically
        
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
        footer_font_size = font_size // 3
        footer_font = ImageFont.truetype(font_path, footer_font_size)
        
        # Format the date, or use a default if it's empty or invalid
        try:
            if article_date:
                formatted_date = datetime.strptime(article_date, "%Y-%m-%d").strftime("%B %d, %Y")
            else:
                formatted_date = datetime.now().strftime("%B %d, %Y")
        except ValueError:
            print(f"Warning: Invalid date format '{article_date}'. Using current date.")
            formatted_date = datetime.now().strftime("%B %d, %Y")
        
        draw.text((20, img.height - 30), formatted_date, font=footer_font, fill=text_color)
        
        ainewsbrew_width = draw.textlength("@ainewsbrew", font=footer_font)
        draw.text((img.width - ainewsbrew_width - 20, img.height - 30), "@ainewsbrew", font=footer_font, fill=text_color)
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        output_path = "bluesky_haikubg_with_text.png"
        img.save(output_path)
        return output_path

def generate_bluesky_haiku_background(haiku, ai_headline, article_date):
    image_prompt = generate_image_prompt(haiku)
    print(f"Generated image prompt: {image_prompt}")
    
    image_path, prompt = generate_image(image_prompt)
    print(f"Generated image path: {image_path}")
    
    if image_path:
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSerif-BoldItalic.ttf")
        
        if not os.path.exists(font_path):
            print(f"Font file not found at {font_path}. Using default font.")
            font_path = None  # This will use a default font

        final_image = add_text_to_image(image_path, haiku, article_date, font_path, initial_font_size=80)
        print(f"Final image path: {final_image}")
        return final_image, prompt
    
    print("Failed to generate Bluesky haiku image")
    return None, prompt

if __name__ == "__main__":
    haiku = "Example haiku\nThis is a test haiku\nFor Bluesky image"
    ai_headline = "AI Generates Haiku Images for Bluesky"
    article_date = "2023-06-15"
    
    final_image, prompt = generate_bluesky_haiku_background(haiku, ai_headline, article_date)
    
    if final_image:
        print(f"Bluesky haiku image generated successfully: {final_image}")
        print(f"Image prompt: {prompt}")
    else:
        print("Failed to generate Bluesky haiku image") 