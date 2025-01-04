import os
import base64
import ftplib
import http.client
import json
import requests
from io import BytesIO
from urllib.parse import urlparse
from dotenv import load_dotenv

def get_article_data(article_id, api_key):
    """Fetch article data from the API"""
    conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': api_key
    }
    
    print(f"\nFetching article {article_id} from API...")
    conn.request("GET", f"/api/index_v5.php?mode=byIndex&index={article_id}", headers=headers)
    res = conn.getresponse()
    data = res.read()
    
    print(f"API Response Status: {res.status}")
    decoded_data = data.decode('utf-8')
    
    if res.status == 200:
        try:
            json_data = json.loads(decoded_data)
            if json_data:
                print("\nArticle Information:")
                print(f"ID: {json_data.get('ID', 'Not found')}")
                print(f"Headline: {json_data.get('AIHeadline', 'Not found')}")
                print(f"Published: {json_data.get('Published', 'Not found')}")
                print("\nAvailable Keys:", list(json_data.keys() if json_data else []))
                
                if 'image_data' in json_data:
                    print("\nFirst 100 chars of image_data:", json_data['image_data'][:100] if json_data['image_data'] else "None")
                if 'image_haiku' in json_data:
                    print("\nFirst 100 chars of image_haiku:", json_data['image_haiku'][:100] if json_data['image_haiku'] else "None")
            return json_data
        except json.JSONDecodeError as e:
            print(f"\nError decoding JSON: {str(e)}")
            print("Raw response:", decoded_data)
            return None
    return None

def base64_to_image(base64_string):
    """Convert base64 data URL to image bytes"""
    try:
        # Remove the data URL prefix if present
        if ',' in base64_string:
            prefix = base64_string.split(',')[0]
            print(f"Image data prefix: {prefix}")
            base64_string = base64_string.split(',')[1]
        return base64.b64decode(base64_string)
    except Exception as e:
        print(f"Error decoding base64: {str(e)}")
        return None

def upload_to_ftp(hostname, username, password, port, remote_dir, article_id, image_data, image_haiku):
    """Upload images to FTP server"""
    try:
        # Connect to FTP server
        print(f"\nConnecting to FTP server {hostname}:{port}...")
        ftp = ftplib.FTP()
        ftp.connect(hostname, port)
        ftp.login(username, password)
        
        print(f"Changing to directory: {remote_dir}")
        # Change to the target directory
        ftp.cwd(remote_dir)
        
        # Upload background image
        if image_data:
            print("\nProcessing background image...")
            bg_filename = f"{article_id}_background.jpg"
            bg_data = BytesIO(base64_to_image(image_data))
            if bg_data.getvalue():
                print(f"Uploading {bg_filename} (size: {len(bg_data.getvalue())} bytes)")
                ftp.storbinary(f'STOR {bg_filename}', bg_data)
                print(f"Uploaded {bg_filename}")
            else:
                print("Error: Background image data is empty")
        else:
            print("No background image data provided")
        
        # Upload haiku image
        if image_haiku:
            print("\nProcessing haiku image...")
            haiku_filename = f"{article_id}_haiku.jpg"
            haiku_data = BytesIO(base64_to_image(image_haiku))
            if haiku_data.getvalue():
                print(f"Uploading {haiku_filename} (size: {len(haiku_data.getvalue())} bytes)")
                ftp.storbinary(f'STOR {haiku_filename}', haiku_data)
                print(f"Uploaded {haiku_filename}")
            else:
                print("Error: Haiku image data is empty")
        else:
            print("No haiku image data provided")
        
        ftp.quit()
        return True
    except Exception as e:
        print(f"\nFTP upload error: {str(e)}")
        if 'ftp' in locals():
            try:
                ftp.quit()
            except:
                pass
        return False

def check_image_exists(article_id):
    """Check if images already exist for the article"""
    bg_url = f"https://fetch.ainewsbrew.com/images/{article_id}_background.jpg"
    haiku_url = f"https://fetch.ainewsbrew.com/images/{article_id}_haiku.jpg"
    
    try:
        bg_response = requests.head(bg_url)
        haiku_response = requests.head(haiku_url)
        
        bg_exists = bg_response.status_code == 200
        haiku_exists = haiku_response.status_code == 200
        
        if bg_exists and haiku_exists:
            print(f"Both images already exist for article {article_id}")
            return True
        elif bg_exists:
            print(f"Only background image exists for article {article_id}")
        elif haiku_exists:
            print(f"Only haiku image exists for article {article_id}")
        return False
    except Exception as e:
        print(f"Error checking image existence: {str(e)}")
        return False

def process_article(index, api_key, ftp_config):
    """Process a single article"""
    article_data = get_article_data(index, api_key)
    if not article_data:
        print(f"\nSkipping index {index}: Could not fetch article data")
        return False
    
    article_id = article_data.get('ID')
    if not article_id:
        print(f"\nSkipping index {index}: Could not find article ID")
        return False
    
    print(f"\nProcessing article {article_id}: {article_data.get('AIHeadline', 'No headline')}")
    
    # Check if images already exist
    if check_image_exists(article_id):
        print(f"Skipping article {article_id}: Images already exist")
        return True
    
    image_data = article_data.get('image_data')
    image_haiku = article_data.get('image_haiku')
    
    if not image_data and not image_haiku:
        print(f"Skipping article {article_id}: No images found")
        return False
    
    success = upload_to_ftp(
        ftp_config['host'], ftp_config['user'], ftp_config['pass'], ftp_config['port'], ftp_config['dir'],
        article_id, image_data, image_haiku
    )
    
    if success:
        print(f"Successfully processed article {article_id}")
        print(f"URLs:")
        print(f"Background: https://fetch.ainewsbrew.com/images/{article_id}_background.jpg")
        print(f"Haiku: https://fetch.ainewsbrew.com/images/{article_id}_haiku.jpg")
    else:
        print(f"Failed to process article {article_id}")
    
    return success

def main():
    load_dotenv()
    
    # Get credentials from environment variables
    api_key = os.getenv("PUBLISH_API_KEY")
    ftp_host = os.getenv("FTP_HOST", "gvam1076.siteground.biz")
    ftp_user = os.getenv("FTP_USER", "imagepost@ainewsbrew.com")
    ftp_pass = os.getenv("FTP_PASS")
    ftp_port = int(os.getenv("FTP_PORT", "21"))
    ftp_dir = os.getenv("FTP_DIR", "/fetch.ainewsbrew.com/public_html/images/")
    
    print("\nConfiguration:")
    print(f"API Key: {'*' * len(api_key) if api_key else 'Not set'}")
    print(f"FTP Host: {ftp_host}")
    print(f"FTP User: {ftp_user}")
    print(f"FTP Pass: {'*' * len(ftp_pass) if ftp_pass else 'Not set'}")
    
    if not all([api_key, ftp_pass]):
        print("Error: Missing required environment variables")
        return
    
    # FTP configuration dictionary
    ftp_config = {
        'host': ftp_host,
        'user': ftp_user,
        'pass': ftp_pass,
        'port': ftp_port,
        'dir': ftp_dir
    }
    
    print("\nStarting automatic batch processing...")
    start_index = 0
    batch_size = 100  # Process in batches of 100
    
    successful = 0
    failed = 0
    skipped = 0
    current_index = start_index
    empty_responses = 0  # Counter for empty responses
    
    while empty_responses < 3:  # Stop if we get 3 empty responses in a row
        print(f"\n=== Processing batch starting at index {current_index} ===")
        
        batch_had_data = False
        for index in range(current_index, current_index + batch_size):
            print(f"\n--- Processing index {index} ---")
            try:
                # First check if we can get any data
                article_data = get_article_data(index, api_key)
                if not article_data:
                    print(f"No data returned for index {index}")
                    if not batch_had_data:
                        empty_responses += 1
                    continue
                
                # Reset empty responses counter if we got data
                empty_responses = 0
                batch_had_data = True
                
                # Process the article
                result = process_article(index, api_key, ftp_config)
                if result:
                    successful += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"Error processing index {index}: {str(e)}")
                failed += 1
            
            # Print progress
            total_processed = successful + skipped + failed
            print(f"\nOverall Progress:")
            print(f"Total Processed: {total_processed}")
            print(f"Successful: {successful}")
            print(f"Skipped: {skipped}")
            print(f"Failed: {failed}")
        
        if empty_responses >= 3:
            print("\nNo more articles found after 3 consecutive empty responses")
            break
            
        current_index += batch_size
    
    print("\n=== Final Statistics ===")
    print(f"Total Processed: {successful + skipped + failed}")
    print(f"Successful: {successful}")
    print(f"Skipped: {skipped}")
    print(f"Failed: {failed}")
    print(f"Last Index Processed: {current_index - 1}")

if __name__ == "__main__":
    main() 