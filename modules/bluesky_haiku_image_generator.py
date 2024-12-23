import os
from chat_codegpt import chat_with_codegpt
import requests
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from datetime import datetime
from dotenv import load_dotenv
import time
import streamlit as st

load_dotenv()
api_key = os.getenv("HORIAR_API_KEY")

def generate_image_prompt(haiku):
    prompt_request = f"Create an image prompt for a background that captures the essence of this haiku:\n{haiku}\nUse your rules for Haiku Background Prompt."
    return chat_with_codegpt(prompt_request)

def poll_text_to_image_status(job_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    start_time = time.time()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    elapsed_time_placeholder = st.empty()
    
    while True:
        elapsed_time = int(time.time() - start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        elapsed_time_placeholder.text(f"Elapsed time: {minutes:02d}:{seconds:02d}")
        
        response = requests.get(f"https://api.horiar.com/enterprise/query/{job_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if "message" in result:
                progress_bar.progress(0)
                status_text.text(f"Status: {result['message']}. Waiting...")
                time.sleep(5)  # Wait for 5 seconds before checking again
            else:
                progress_bar.progress(100)
                status_text.text("Request completed!")
                progress_bar.empty()
                status_text.empty()
                elapsed_time_placeholder.empty()
                return result
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")
            return None

def generate_image(prompt):
    with st.spinner("Generating image..."):
        headers = {"Authorization": f"Bearer {api_key}"}
        data = {
            "prompt": prompt,
            "model_type": "normal",
            "resolution": "1024x1024 | 1:1 (Square)"
        }
        response = requests.post("https://api.horiar.com/enterprise/text-to-image", 
                                headers=headers, json=data)

        if response.status_code == 200:
            result = response.json()
            job_id = result["job_id"]
            request_queued_placeholder = st.empty()
            request_queued_placeholder.info(f"Request queued with job ID: {job_id}. Waiting for completion...")
            
            result = poll_text_to_image_status(job_id)
            
            if result:
                image_url = result["image"]
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    filename = "bluesky_haikubg.png"
                    with open(filename, "wb") as file:
                        file.write(image_response.content)
                    request_queued_placeholder.empty()
                    return filename, prompt
        
        return None, prompt

def add_text_to_image(image_path, haiku, article_date, font_path, initial_font_size=100, text_color=(255, 255, 255, 255)):
    with Image.open(image_path) as img:
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        lines = haiku.split('\n')
        max_width = img.width * 0.9  # Increased to 90% of image width
        
        # Find the largest font size that fits all lines
        font_size = initial_font_size
        while font_size > 1:
            font = ImageFont.truetype(font_path, font_size)
            if all(draw.textlength(line, font=font) <= max_width for line in lines):
                break
            font_size -= 1
        
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate text position and background size
        line_height = font.getbbox('A')[3] + 15  # Increased line spacing
        total_text_height = line_height * len(lines)
        y_text = (img.height - total_text_height) // 2  # Center vertically
        
        bg_width = max(draw.textlength(line, font=font) for line in lines) + 80
        bg_height = total_text_height + 80
        bg_left = (img.width - bg_width) // 2
        bg_top = y_text - 40
        
        draw.rounded_rectangle([bg_left, bg_top, bg_left + bg_width, bg_top + bg_height], 
                               radius=30, fill=(0, 0, 0, 160))
        
        for line in lines:
            text_width = draw.textlength(line, font=font)
            x_text = (img.width - text_width) // 2
            
            for offset in range(1, 3):
                draw.text((x_text + offset, y_text + offset), line, font=font, fill=(0, 0, 0, 128))
            
            draw.text((x_text, y_text), line, font=font, fill=text_color)
            y_text += line_height
        
        # Footer section
        footer_font_size = font_size // 4
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
        
        draw.text((30, img.height - 40), formatted_date, font=footer_font, fill=text_color)
        
        ainewsbrew_width = draw.textlength("@ainewsbrew", font=footer_font)
        draw.text((img.width - ainewsbrew_width - 30, img.height - 40), "@ainewsbrew", font=footer_font, fill=text_color)
        
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        # Resize the image to a maximum width of 1200 pixels while maintaining the aspect ratio
        max_width = 1200
        if img.width > max_width:
            aspect_ratio = max_width / img.width
            new_height = int(img.height * aspect_ratio)
            img = img.resize((max_width, new_height), Image.ANTIALIAS)
        
        img = img.convert('RGB')  # Convert the image to RGB mode
        
        output_path = "bluesky_haikubg_with_text.jpg"
        img.save(output_path, "JPEG", quality=85)
        return output_path

def generate_bluesky_haiku_background(haiku, ai_headline, article_date):
    with st.spinner("Generating Bluesky haiku background..."):
        image_prompt = generate_image_prompt(haiku)
        print(f"Generated image prompt: {image_prompt}")
        
        image_path, prompt = generate_image(image_prompt)
        print(f"Generated image path: {image_path}")
        
        if image_path:
            font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSerif-BoldItalic.ttf")
            
            if not os.path.exists(font_path):
                print(f"Font file not found at {font_path}. Using default font.")
                font_path = None  # This will use a default font

            final_image = add_text_to_image(image_path, haiku, article_date, font_path, initial_font_size=100)
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