import http.client
import json
import time
import hashlib
import base64
import traceback
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from haikubackground import generate_haiku_background
from dotenv import load_dotenv
load_dotenv()

def get_file_hash(file_path):
    with open(file_path, 'rb') as file:
        return hashlib.md5(file.read()).hexdigest()

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded_string}"

def publish_article(json_file_path, api_key):
    print(f"Publishing article from {json_file_path}")
    try:
        # Read the JSON file
        with open(json_file_path, 'r') as file:
            article_data = json.load(file)

        # Generate haiku background
        haiku = article_data.get('AIHaiku', '')
        ai_headline = article_data.get('AIHeadline', '')
        article_date = article_data.get('date', '') or article_data.get('publishDate', '') or ''
        if haiku:
            while True:
                print("Generating haiku background...")
                result = generate_haiku_background(haiku, ai_headline, article_date)
                print(f"Haiku background generation result: {result}")
                
                # User interaction for approval
                print("\nHaiku background has been generated with overlaid text.")
                print("Options:")
                print("1. Accept and continue")
                print("2. Retry (generate a new image)")
                print("3. Cancel publication")
                choice = input("Enter your choice (1/2/3): ").strip()
                
                if choice == '1':
                    # Encode the generated image with overlaid text
                    try:
                        image_data = encode_image("haikubg.png")
                        article_data['image_data'] = image_data
                        print(f"Image successfully encoded. Length: {len(image_data)} characters")
                        break
                    except Exception as e:
                        print(f"Error encoding image: {str(e)}")
                        article_data['image_data'] = None
                        break
                elif choice == '2':
                    continue  # This will restart the loop and generate a new image
                elif choice == '3':
                    print("Publication cancelled. Returning to file observation.")
                    return
                else:
                    print("Invalid choice. Please try again.")

        # API endpoint
        conn = http.client.HTTPSConnection("fetch.ainewsbrew.com")
        payload = json.dumps(article_data)
        headers = {
            'Content-Type': 'application/json',
            'X-API-KEY': api_key
        }

        print(f"Payload size: {len(payload)} bytes")
        print("Sending request to API...")
        conn.request("POST", "/api/index_v5.php?mode=pub", payload, headers)
        res = conn.getresponse()
        data = res.read()

        print(f"Response status code: {res.status}")
        print(f"Response headers: {res.headers}")
        print(f"Response content: {data.decode('utf-8')}")

        if res.status == 200:
            try:
                result = json.loads(data.decode('utf-8'))
                if result.get('status') == 'success':
                    print(f"Article published successfully. Article ID: {result.get('articleId')}")
                    print(f"Article link: {result.get('link')}")
                else:
                    print(f"Error publishing article: {result.get('message')}")
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
        else:
            print(f"HTTP Error: {res.status}")
            print(f"Error content: {data.decode('utf-8')}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print("Traceback:")
        print(traceback.format_exc())

    finally:
        if 'conn' in locals():
            conn.close()

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, json_file_path, api_key):
        self.json_file_path = json_file_path
        self.api_key = api_key
        self.last_hash = get_file_hash(json_file_path)
        self.last_check_time = 0

    def on_modified(self, event):
        current_time = time.time()
        if event.src_path.endswith(self.json_file_path) and current_time - self.last_check_time >= 10:
            current_hash = get_file_hash(self.json_file_path)
            if current_hash != self.last_hash:
                print(f"{self.json_file_path} has been modified")
                publish_article(self.json_file_path, self.api_key)
                self.last_hash = current_hash
            else:
                print(f"File {self.json_file_path} was touched but content didn't change")
            self.last_check_time = current_time

# Usage
api_key = os.environ.get("PUBLISH_API_KEY")
json_file_path = 'publish.json'

event_handler = FileChangeHandler(json_file_path, api_key)
observer = Observer()
observer.schedule(event_handler, path='.', recursive=False)
observer.start()

print(f"Started monitoring {json_file_path} for changes...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
