import http.client
import json
import base64
import traceback
from haikubackground import generate_haiku_background
from colorama import Fore, Style

def encode_image(image_path):
    """Encode an image file to base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

def generate_and_encode_images(haiku, headline, date=''):
    """Generate and encode haiku background images"""
    try:
        print("\nGenerating haiku background...")
        result = generate_haiku_background(haiku, headline, date)
        print(f"Haiku background generation result: {result}")
        
        # Encode both images
        image_data = encode_image("haikubg.png")
        image_haiku = encode_image("haikubg_with_text.png")
        
        return image_data, image_haiku
    except Exception as e:
        print(f"{Fore.RED}Error generating/encoding images: {str(e)}{Style.RESET_ALL}")
        return None, None

def publish_article(publish_data, api_key):
    """Send article data to publishing API"""
    conn = None
    try:
        conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
        payload = json.dumps(publish_data)
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }

        print("\nSending to publishing API...")
        conn.request("POST", "/api/index_v5.php?mode=pub", payload, headers)
        res = conn.getresponse()
        data = res.read()

        if res.status == 200:
            try:
                result = json.loads(data.decode('utf-8'))
                if result.get('status') == 'success':
                    print(f"\n{Fore.GREEN}Article published successfully!")
                    print(f"Article ID: {result.get('articleId')}")
                    print(f"Article link: {result.get('link')}{Style.RESET_ALL}")
                    return result.get('articleId')
                else:
                    print(f"\n{Fore.RED}Error publishing article: {result.get('message')}{Style.RESET_ALL}")
            except json.JSONDecodeError:
                print(f"{Fore.RED}Failed to parse API response{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.RED}HTTP Error: {res.status}")
            print(f"Error content: {data.decode('utf-8')}{Style.RESET_ALL}")

    except Exception as e:
        print(f"\n{Fore.RED}Publication error: {str(e)}")
        print(f"Traceback:\n{traceback.format_exc()}{Style.RESET_ALL}")

    finally:
        if conn:
            conn.close()
    
    return None 