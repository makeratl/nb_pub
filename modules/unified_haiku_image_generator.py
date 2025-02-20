import os
import time
from chat_codegpt import chat_with_codegpt
import requests
import json
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

load_dotenv()
api_key = os.getenv("HORIAR_API_KEY")

# Define the specific agent ID for image generation
IMAGE_GENERATION_AGENT_ID = "c065444b-510f-4ab0-97b8-3840c66109d3"

def generate_unified_image_prompt(haiku, ai_headline, feedback=None):
    """
    Generate a single image prompt that works for both standard and Bluesky formats.
    
    Args:
        haiku (str): The haiku text
        ai_headline (str): The AI-generated headline
        feedback (str, optional): User feedback for image regeneration
        
    Returns:
        str: The generated image prompt
    """
    # Check if this is an AI Perspective piece
    if ai_headline.startswith("AI Perspective:"):
        prompt_request = f"""Create an artistically emotive image prompt that symbolically represents the story's essence, using a retro 1960s-style aesthetic. 
This prompt will be used to generate two versions of the image:
1. A standard landscape format (1344x768)
2. A square Bluesky format (1024x1024)

Headline: {ai_headline}
Haiku:
{haiku}

Artistic Guidance:
1. Focus on symbolic, metaphorical representation
2. Avoid literal or potentially disturbing imagery
3. Use abstract visual metaphors that capture emotional nuance
4. Prioritize artistic interpretation over direct representation
5. Create a visual poem that resonates with the haiku's emotional core
6. Use color, texture, and composition to convey mood
7. Maintain a vintage 1960s visual style with artistic abstraction
8. Ensure the image feels more like an emotional landscape than a news report
9. Design composition that works in both landscape and square formats
{f'10. Incorporate user feedback: {feedback}' if feedback else ''}

The prompt should generate an artistically interpreted image that speaks to the story's emotional essence, using symbolic visual language."""
    else:
        prompt_request = f"""Create an artistically emotive image prompt that symbolically represents the story's essence.
This prompt will be used to generate two versions of the image:
1. A standard landscape format (1344x768)
2. A square Bluesky format (1024x1024)

Headline: {ai_headline}
Haiku:
{haiku}

Artistic Guidance:
1. Focus on symbolic, metaphorical representation
2. Avoid literal or potentially disturbing imagery
3. Use abstract visual metaphors that capture emotional nuance
4. Prioritize artistic interpretation over direct representation
5. Create a visual poem that resonates with the haiku's emotional core
6. Use color, texture, and composition to convey mood
7. Ensure the image feels more like an emotional landscape than a news report
8. Design composition that works in both landscape and square formats
{f'9. Incorporate user feedback: {feedback}' if feedback else ''}

The prompt should generate an artistically interpreted image that speaks to the story's emotional essence, using symbolic visual language."""
    return chat_with_codegpt(prompt_request, agent_id=IMAGE_GENERATION_AGENT_ID)

def poll_text_to_image_status(job_id, progress_container, progress_bar, status_text, image_type="standard"):
    """
    Poll the image generation status.
    
    Args:
        job_id (str): The job ID to poll
        progress_container: Streamlit container for progress display
        progress_bar: Streamlit progress bar
        status_text: Streamlit text element for status updates
        image_type (str): Type of image being generated ("standard" or "bluesky")
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    start_time = time.time()
    
    while True:
        elapsed_time = int(time.time() - start_time)
        
        response = requests.get(f"https://api.horiar.com/enterprise/query/{job_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            
            if "message" in result:
                progress_bar.progress(0.5)
                status_text.text(f"🎨 Creating your {image_type} image...")
                time.sleep(5)
            else:
                progress_bar.progress(1.0)
                progress_container.empty()
                return result
        else:
            st.error(f"Unable to generate {image_type} image. Please try again.")
            return None

def generate_image(prompt, is_bluesky=False):
    """
    Generate an image using the provided prompt.
    
    Args:
        prompt (str): The image generation prompt
        is_bluesky (bool): Whether to generate a Bluesky format image
        
    Returns:
        tuple: (filename, prompt) or (None, prompt) if generation fails
    """
    headers = {"Authorization": f"Bearer {api_key}"}
    
    # Configure image parameters based on type
    if is_bluesky:
        data = {
            "prompt": f"{prompt} | professional news media style | high quality | balanced composition | social media optimized | 1024x1024 | 1:1 (Square)",
            "model_type": "normal",
            "resolution": "1024x1024 | 1:1 (Square)"
        }
        filename = "bluesky_haikubg.png"
        image_type = "Bluesky"
    else:
        data = {
            "prompt": f"{prompt} | professional news media aesthetic | high quality | balanced composition | digital platform optimized",
            "model_type": "normal",
            "resolution": "1344x768"
        }
        filename = "haikubg.png"
        image_type = "standard"
    
    progress_container = st.container()
    with progress_container:
        progress_bar = st.progress(0.0)
        status_text = st.empty()
        status_text.text(f"🖼️ Preparing your {image_type} image...")
    
    response = requests.post("https://api.horiar.com/enterprise/text-to-image", 
                           headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        job_id = result["job_id"]
        
        result = poll_text_to_image_status(job_id, progress_container, progress_bar, status_text, image_type.lower())
        
        if result:
            try:
                image_url = result["output"]["image"]
                image_response = requests.get(image_url)
                if image_response.status_code == 200:
                    with open(filename, "wb") as file:
                        file.write(image_response.content)
                    return filename, prompt
            except KeyError:
                st.error(f"Unable to process the generated {image_type} image. Please try again.")
                return None, prompt
    else:
        st.error(f"Unable to start {image_type} image generation. Please try again.")
    
    progress_container.empty()
    return None, prompt

def add_text_to_image(image_path, haiku, article_date, font_path, is_bluesky=False, ai_headline=None, initial_font_size=None):
    """
    Add text overlay to the generated image.
    
    Args:
        image_path (str): Path to the image file
        haiku (str): The haiku text
        article_date (str): The article date
        font_path (str): Path to the font file
        is_bluesky (bool): Whether this is a Bluesky format image
        ai_headline (str, optional): The AI headline (only used for standard format)
        initial_font_size (int, optional): Initial font size
    """
    with Image.open(image_path) as img:
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        lines = haiku.split('\n')
        max_width = img.width * 0.9
        
        # Set initial font size based on image type
        if initial_font_size is None:
            initial_font_size = 100 if is_bluesky else 40
        
        # Find the largest font size that fits all lines
        font_size = initial_font_size
        while font_size > 1:
            font = ImageFont.truetype(font_path, font_size)
            if all(draw.textlength(line, font=font) <= max_width for line in lines):
                break
            font_size -= 1
        
        font = ImageFont.truetype(font_path, font_size)
        
        # Calculate text position and background size
        line_height = font.getbbox('A')[3] + (15 if is_bluesky else 5)
        total_text_height = line_height * len(lines)
        
        # Position text differently for Bluesky vs standard
        if is_bluesky:
            y_text = (img.height - total_text_height) // 2
        else:
            y_text = img.height // 3 - total_text_height // 2
        
        # Background dimensions
        bg_width = max(draw.textlength(line, font=font) for line in lines) + (80 if is_bluesky else 60)
        bg_height = total_text_height + (80 if is_bluesky else 60)
        bg_left = (img.width - bg_width) // 2
        bg_top = y_text - (40 if is_bluesky else 30)
        
        # Draw background
        draw.rounded_rectangle(
            [bg_left, bg_top, bg_left + bg_width, bg_top + bg_height],
            radius=30 if is_bluesky else 20,
            fill=(0, 0, 0, 160)
        )
        
        # Draw haiku text
        for line in lines:
            text_width = draw.textlength(line, font=font)
            x_text = (img.width - text_width) // 2
            
            for offset in range(1, 3):
                draw.text((x_text + offset, y_text + offset), line, font=font, fill=(0, 0, 0, 128))
            
            draw.text((x_text, y_text), line, font=font, fill=(255, 255, 255, 255))
            y_text += line_height
        
        # Footer section
        if is_bluesky:
            footer_font_size = font_size // 4
        else:
            footer_font_size = font_size // 2
        
        footer_font = ImageFont.truetype(font_path, footer_font_size)
        
        if not is_bluesky:
            # Add headline and transparent footer background for standard format
            footer_height = 100
            footer_top = img.height - footer_height
            draw.rectangle([0, footer_top, img.width, img.height], fill=(0, 0, 0, 128))
            
            if ai_headline:
                headline_lines = textwrap.wrap(ai_headline, width=60)
                headline_y = footer_top + 10
                
                for line in headline_lines:
                    draw.text((20, headline_y), line, font=footer_font, fill=(255, 255, 255, 255))
                    headline_y += footer_font.getbbox('A')[3] + 5
        
        # Format date
        try:
            if article_date:
                formatted_date = datetime.strptime(article_date, "%Y-%m-%d").strftime("%B %d, %Y")
            else:
                formatted_date = datetime.now().strftime("%B %d, %Y")
        except ValueError:
            print(f"Warning: Invalid date format '{article_date}'. Using current date.")
            formatted_date = datetime.now().strftime("%B %d, %Y")
        
        # Add date and @ainewsbrew
        date_font = ImageFont.truetype(font_path, footer_font_size - (4 if not is_bluesky else 0))
        draw.text((30 if is_bluesky else 20, img.height - 40), formatted_date, font=date_font, fill=(255, 255, 255, 255))
        
        ainewsbrew_width = draw.textlength("@ainewsbrew", font=date_font)
        draw.text(
            (img.width - ainewsbrew_width - (30 if is_bluesky else 20), img.height - 40),
            "@ainewsbrew",
            font=date_font,
            fill=(255, 255, 255, 255)
        )
        
        # Composite the overlay with the original image
        img = Image.alpha_composite(img.convert('RGBA'), overlay)
        
        # Resize if needed (for standard format)
        if not is_bluesky:
            max_width = 1200
            if img.width > max_width:
                aspect_ratio = max_width / img.width
                new_height = int(img.height * aspect_ratio)
                img = img.resize((max_width, new_height), Image.ANTIALIAS)
        
        # Convert to RGB and save
        img = img.convert('RGB')
        output_path = "bluesky_haikubg_with_text.jpg" if is_bluesky else "haikubg_with_text.jpg"
        img.save(output_path, "JPEG", quality=85)
        return output_path

def generate_haiku_images(haiku, ai_headline, article_date, existing_prompt=None, feedback=None):
    """
    Generate both standard and Bluesky format images for a haiku.
    
    Args:
        haiku (str): The haiku text
        ai_headline (str): The AI-generated headline
        article_date (str): The article date
        existing_prompt (str, optional): An existing image prompt to reuse
        feedback (str, optional): User feedback for image regeneration
        
    Returns:
        tuple: (standard_image_path, bluesky_image_path, prompt)
    """
    with st.spinner("Generating haiku images..."):
        # Use existing prompt or generate new one
        image_prompt = existing_prompt if existing_prompt else generate_unified_image_prompt(haiku, ai_headline, feedback)
        
        # Generate standard image
        standard_image_path, _ = generate_image(image_prompt, is_bluesky=False)
        
        # Generate Bluesky image
        bluesky_image_path, _ = generate_image(image_prompt, is_bluesky=True)
        
        if standard_image_path and bluesky_image_path:
            font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSerif-BoldItalic.ttf")
            
            if not os.path.exists(font_path):
                st.warning(f"Font file not found at {font_path}. Using default font.")
                font_path = None
            
            # Add text to standard image
            final_standard_image = add_text_to_image(
                standard_image_path,
                haiku,
                article_date,
                font_path,
                is_bluesky=False,
                ai_headline=ai_headline,
                initial_font_size=40
            )
            
            # Add text to Bluesky image
            final_bluesky_image = add_text_to_image(
                bluesky_image_path,
                haiku,
                article_date,
                font_path,
                is_bluesky=True,
                initial_font_size=100
            )
            
            return final_standard_image, final_bluesky_image, image_prompt
        
        return None, None, image_prompt

if __name__ == "__main__":
    # Test the image generator
    test_haiku = "Example haiku\nThis is a test haiku text\nFor image testing"
    test_headline = "AI Perspective: Testing the Unified Haiku Image Generator"
    test_date = datetime.now().strftime("%Y-%m-%d")
    
    standard_image, bluesky_image, prompt = generate_haiku_images(test_haiku, test_headline, test_date)
    
    if standard_image and bluesky_image:
        print(f"Successfully generated images:")
        print(f"Standard image: {standard_image}")
        print(f"Bluesky image: {bluesky_image}")
        print(f"Image prompt: {prompt}")
    else:
        print("Failed to generate one or both images") 