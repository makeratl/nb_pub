import os
from dotenv import load_dotenv
from modules.threads_publish import ThreadsPublisher, test_threads_connection

def test_post_to_threads():
    """Test posting an image to Threads"""
    # Load environment variables
    load_dotenv()
    
    # First test the connection
    if not test_threads_connection():
        print("Failed to connect to Threads. Please check your credentials.")
        return
    
    # Use a local test image
    test_image_path = "bluesky_haikubg_with_text.jpg"  # Using the square image
    if not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        print("Please make sure you have a test image file available.")
        return
    
    test_caption = """🤖 AI News Brew Test Post

Testing Threads integration for AI News Brew.
This is an automated test post.

Read more: https://ainewsbrew.com

#AINewsBrew #TestPost #AI #News"""

    try:
        publisher = ThreadsPublisher()
        post_id = publisher.publish_post(test_image_path, test_caption)
        
        if post_id:
            print(f"Successfully published test post to Threads!")
            print(f"Post ID: {post_id}")
        else:
            print("Failed to publish test post to Threads")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_post_to_threads() 