import os
import requests
from datetime import datetime
import json
from typing import Optional, Dict, Any
import ftplib
from io import BytesIO

def upload_image_to_ftp(image_data: bytes, filename: str) -> Optional[str]:
    """Upload an image to FTP and return its URL"""
    try:
        # Get FTP credentials from environment
        ftp_host = os.environ.get("FTP_HOST", "gvam1076.siteground.biz")
        ftp_user = os.environ.get("FTP_USER", "imagepost@ainewsbrew.com")
        ftp_pass = os.environ.get("FTP_PASS")
        ftp_port = int(os.environ.get("FTP_PORT", "21"))
        ftp_dir = os.environ.get("FTP_DIR", "/fetch.ainewsbrew.com/public_html/images/")
        
        if not all([ftp_host, ftp_user, ftp_pass, ftp_dir]):
            raise ValueError("Missing FTP credentials in environment variables")
        
        # Connect to FTP
        ftp = ftplib.FTP()
        ftp.connect(ftp_host, ftp_port)
        ftp.login(ftp_user, ftp_pass)
        
        # Change to the correct directory
        ftp.cwd(ftp_dir)
        
        # Upload the image
        ftp.storbinary(f'STOR {filename}', BytesIO(image_data))
        
        # Close FTP connection
        ftp.quit()
        
        # Return the public URL
        return f"https://fetch.ainewsbrew.com/images/{filename}"
        
    except Exception as e:
        print(f"FTP Upload Error: {str(e)}")
        return None

class FacebookPublisher:
    """
    Handles publishing to Facebook Pages using the Graph API
    Uses the same access token as Instagram since they're both Meta platforms
    """
    
    def __init__(self):
        """Initialize with credentials from environment variables"""
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")  # We can use the same token
        self.facebook_page_id = os.environ.get("FACEBOOK_PAGE_ID")
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.facebook_page_id:
            raise ValueError("Missing required Facebook credentials in environment variables")

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Make a request to the Facebook Graph API"""
        url = f"{self.base_url}/{endpoint}"
        
        # Always include access token
        if params is None:
            params = {}
        params['access_token'] = self.access_token
        
        try:
            response = requests.request(method, url, params=params, json=data)
            
            # Print detailed debug information
            print(f"\nAPI Request Details:")
            print(f"URL: {url}")
            print(f"Method: {method}")
            print(f"Params: {params}")
            if data:
                print(f"Data: {data}")
            
            if not response.ok:
                error_data = response.json() if response.content else {}
                error_message = error_data.get('error', {}).get('message', 'Unknown error')
                error_type = error_data.get('error', {}).get('type', 'Unknown type')
                error_code = error_data.get('error', {}).get('code', 'Unknown code')
                
                print(f"\nAPI Error Details:")
                print(f"Status Code: {response.status_code}")
                print(f"Error Type: {error_type}")
                print(f"Error Code: {error_code}")
                print(f"Error Message: {error_message}")
                
                raise requests.exceptions.HTTPError(
                    f"Facebook API error: {error_message} (Type: {error_type}, Code: {error_code})"
                )
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"\nRequest Failed:")
            print(f"Error: {str(e)}")
            raise

    def get_page_info(self) -> Dict[str, Any]:
        """Get basic information about the Facebook Page"""
        try:
            endpoint = f"{self.facebook_page_id}"
            fields = "id,name,link,picture"
            result = self._make_request('GET', endpoint, params={'fields': fields})
            
            if result:
                print(f"\nSuccessfully connected to Facebook Page:")
                print(f"Name: {result.get('name')}")
                print(f"Page ID: {result.get('id')}")
                print(f"Link: {result.get('link')}")
                return result
                
        except Exception as e:
            print(f"\nFailed to get page info: {str(e)}")
            raise

    def publish_post(self, image_path: str, message: str) -> Optional[str]:
        """
        Publish an image post to Facebook Page using the Pages API
        Returns the post ID if successful, None otherwise
        """
        try:
            # First upload the image to FTP to get a URL
            print("\nUploading image to FTP server...")
            
            # Read the image file
            with open(image_path, 'rb') as img:
                image_data = img.read()
            
            # Generate a unique filename
            filename = f"facebook_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            # Upload to FTP using our local function
            image_url = upload_image_to_ftp(image_data, filename)
            if not image_url:
                raise ValueError("Failed to upload image to FTP server")
            
            print(f"Image uploaded successfully: {image_url}")
            
            # Post directly to the feed with the photo URL
            endpoint = f"{self.facebook_page_id}/photos"
            params = {
                'access_token': self.access_token,
                'url': image_url,
                'message': message,
                'published': 'true'
            }
            
            # Make the API request
            response = requests.post(f"{self.base_url}/{endpoint}", params=params)
            
            if not response.ok:
                error_data = response.json()
                raise requests.exceptions.HTTPError(
                    f"Facebook API error: {error_data.get('error', {}).get('message')}"
                )
            
            result = response.json()
            post_id = result.get('id')
            
            if post_id:
                print(f"\nSuccessfully published to Facebook!")
                print(f"Post ID: {post_id}")
                return post_id
            
            return None
            
        except Exception as e:
            print(f"Error publishing to Facebook: {str(e)}")
            return None

def test_facebook_connection():
    """Test the Facebook connection and basic functionality"""
    try:
        publisher = FacebookPublisher()
        
        # Test getting page info
        print("\nTesting Facebook connection...")
        print(f"Using Page ID: {publisher.facebook_page_id}")
        print(f"Access Token (first 20 chars): {publisher.access_token[:20]}...")
        
        page_info = publisher.get_page_info()
        print(f"\nConnection successful!")
        print(f"Page Info:")
        print(json.dumps(page_info, indent=2))
        
        return True
        
    except Exception as e:
        print(f"\nError testing Facebook connection: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the connection
    test_facebook_connection() 