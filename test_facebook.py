import os
from dotenv import load_dotenv
from modules.facebook_publish import FacebookPublisher, test_facebook_connection

def test_post_to_facebook():
    """Test posting an image to Facebook"""
    # Load environment variables
    load_dotenv()
    
    # First test the connection
    if not test_facebook_connection():
        print("Failed to connect to Facebook. Please check your credentials.")
        return
    
    # Use a local test image
    test_image_path = "bluesky_haikubg_with_text.jpg"  # Using the square image
    if not os.path.exists(test_image_path):
        print(f"Test image not found: {test_image_path}")
        print("Please make sure you have a test image file available.")
        return
    
    test_message = """🤖 AI News Brew Test Post

Testing Facebook integration for AI News Brew.
This is an automated test post.

#AINewsBrew #TestPost #AI #News"""

    try:
        publisher = FacebookPublisher()
        post_id = publisher.publish_post(test_image_path, test_message)
        
        if post_id:
            print(f"Successfully published test post to Facebook!")
            print(f"Post ID: {post_id}")
        else:
            print("Failed to publish test post to Facebook")
            
    except Exception as e:
        print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    test_post_to_facebook() 