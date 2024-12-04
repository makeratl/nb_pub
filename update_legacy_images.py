import requests
import json
import base64
import os
import http.client
import time
from chat_codegpt import chat_with_codegpt
from haikubackground import generate_image, add_text_to_image, generate_image_prompt
from datetime import datetime
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()

def is_valid_base64_image(base64_string):
    try:
        # Remove the data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        
        # Try to decode and open the image
        image_data = base64.b64decode(base64_string)
        Image.open(io.BytesIO(image_data))
        return True
    except:
        return False

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

def update_article_images(article_id, image_data, image_haiku, api_key):
    conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
    payload = json.dumps({
        "image_data": image_data,
        "image_haiku": image_haiku
    })
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': api_key
    }
    
    conn.request("POST", f"/api/index_v5.php?mode=updateImages&id={article_id}", payload, headers)
    res = conn.getresponse()
    return json.loads(res.read().decode('utf-8'))

def process_article(api_key):
    # Get next article with missing haiku image
    conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
    headers = {'X-API-KEY': api_key}
    
    conn.request("GET", "/api/index_v5.php?mode=getMissingHaiku", headers=headers)
    res = conn.getresponse()
    article = json.loads(res.read().decode('utf-8'))
    
    if not article:
        print("No articles found with missing haiku images.")
        return False
    
    print(f"\nProcessing article ID: {article['ID']}")
    print(f"Headline: {article['AIHeadline']}")
    
    image_data = article.get('image_data')
    valid_existing_image = False
    
    if image_data:
        valid_existing_image = is_valid_base64_image(image_data)
    
    if valid_existing_image:
        print("Using existing image data...")
        # Save existing image to file
        image_data_clean = image_data.split(',')[1] if ',' in image_data else image_data
        with open("haikubg.png", "wb") as f:
            f.write(base64.b64decode(image_data_clean))
    else:
        print("Generating new image...")
        # Generate new image using existing pipeline
        prompt = generate_image_prompt(article['AIHaiku'])
        generate_image(prompt)
    
    # Parse the Published date from the article
    try:
        # MySQL datetime format is "YYYY-MM-DD HH:MM:SS"
        article_date = datetime.strptime(article['Published'], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d')
    except (ValueError, KeyError):
        print(f"Warning: Could not parse date from {article.get('Published')}. Using current date.")
        article_date = datetime.now().strftime('%Y-%m-%d')
    
    # Add text overlay to create haiku image
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSerif-BoldItalic.ttf")
    add_text_to_image(
        "haikubg.png",
        article['AIHaiku'],
        article['AIHeadline'],
        article_date,  # Pass the parsed article date
        font_path
    )
    
    # Encode both images
    if not valid_existing_image:
        image_data = encode_image("haikubg.png")
    image_haiku = encode_image("haikubg_with_text.png")
    
    # Update the article
    result = update_article_images(article['ID'], image_data, image_haiku, api_key)
    print(f"Update result: {result}")
    
    return True

def main():
    api_key = os.environ.get("PUBLISH_API_KEY")
    if not api_key:
        print("Error: PUBLISH_API_KEY not found in environment variables")
        return
    
    print("Starting automatic processing of articles...")
    print("Press Ctrl+C to stop the process at any time")
    
    try:
        while True:
            if not process_article(api_key):
                print("\nNo more articles to process.")
                break
            print("\nWaiting 2 seconds before processing next article...")
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n\nProcess interrupted by user. Shutting down gracefully...")
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
    finally:
        print("Process completed.")

if __name__ == "__main__":
    main() 