import http.client
import json
import base64
import traceback
from modules.unified_haiku_image_generator import generate_haiku_images
from colorama import Fore, Style
from PIL import Image
from io import BytesIO
import urllib.parse

def encode_image(image_path):
    """Encode an image file to base64"""
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_string}"

def generate_and_encode_images(image_path, output_path):
    """Generate and encode images for publishing"""
    try:
        if image_path:
            # Encode the original image
            encoded_image = encode_image(image_path)
            # Encode the image with text
            encoded_image_with_text = encode_image(output_path)
            return encoded_image, encoded_image_with_text
        else:
            return None, None
    except Exception as e:
        print(f"Error encoding images: {str(e)}")
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

def search_historical_articles(keywords, time_range, filters, api_key):
    """Send historical search request to API"""
    conn = None
    try:
        conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
        
        # URL encode all parameters
        encoded_keywords = urllib.parse.quote(keywords)
        encoded_time_range = urllib.parse.quote(time_range)
        
        # Prepare query parameters
        params = f"/api/index_v5.php?mode=historical&keywords={encoded_keywords}&timeRange={encoded_time_range}"
        
        # Prepare the filters payload
        payload = json.dumps(filters)
        
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }

        print("\nSending historical search request...")
        print(f"URL: {params}")
        print(f"Payload: {payload}")
        
        conn.request("POST", params, payload, headers)
        res = conn.getresponse()
        data = res.read()
        
        print(f"Response status: {res.status}")
        print(f"Raw response: {data.decode('utf-8')}")

        if res.status == 200:
            try:
                result = json.loads(data.decode('utf-8'))
                # Return the result regardless of status - let the UI handle any errors
                return result
            except json.JSONDecodeError as e:
                print(f"{Fore.RED}Failed to parse API response: {str(e)}")
                print(f"Raw response: {data.decode('utf-8')}{Style.RESET_ALL}")
                return {
                    'error': 'Failed to parse API response',
                    'details': str(e),
                    'raw_response': data.decode('utf-8')
                }
        else:
            error_msg = f"HTTP Error: {res.status}"
            print(f"\n{Fore.RED}{error_msg}")
            print(f"Error content: {data.decode('utf-8')}{Style.RESET_ALL}")
            return {
                'error': error_msg,
                'details': data.decode('utf-8')
            }

    except Exception as e:
        error_msg = f"Historical search error: {str(e)}"
        print(f"\n{Fore.RED}{error_msg}")
        print(f"Traceback:\n{traceback.format_exc()}{Style.RESET_ALL}")
        return {
            'error': error_msg,
            'details': traceback.format_exc()
        }

    finally:
        if conn:
            conn.close() 