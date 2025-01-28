import os
import requests
from datetime import datetime
import json
from typing import Optional, Dict, Any, Tuple
import mimetypes
import ftplib
import base64
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

class InstagramPublisher:
    """
    Handles publishing to Instagram using the Graph API
    Documentation: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
    """
    
    def __init__(self):
        """Initialize with credentials from environment variables"""
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.instagram_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
        self.api_version = "v18.0"  # Current stable version as of 2024
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.instagram_account_id:
            raise ValueError("Missing required Instagram credentials in environment variables")

    def _make_request(self, method: str, endpoint: str, params: Dict = None, data: Dict = None) -> Dict[str, Any]:
        """Make a request to the Instagram Graph API"""
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
            
            # If there's an error, try to get detailed error information
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
                    f"Instagram API error: {error_message} (Type: {error_type}, Code: {error_code})"
                )
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"\nRequest Failed:")
            print(f"Error: {str(e)}")
            raise

    def get_account_info(self) -> Dict[str, Any]:
        """Get basic information about the Instagram account"""
        try:
            # For IGUser nodes, we use different fields
            endpoint = f"{self.instagram_account_id}"
            fields = "id,username,profile_picture_url"
            result = self._make_request('GET', endpoint, params={'fields': fields})
            
            if result:
                print(f"\nSuccessfully connected to Instagram account:")
                print(f"Username: {result.get('username')}")
                print(f"Account ID: {result.get('id')}")
                return result
                
        except Exception as e:
            print(f"\nFailed to get account info: {str(e)}")
            raise

    def create_container(self, image_path: str, caption: str) -> str:
        """
        Create a media container for the post
        Returns the container ID if successful
        """
        endpoint = f"{self.instagram_account_id}/media"
        
        # First upload the image to FTP
        print("\nUploading image to FTP server...")
        
        # Read the image file
        with open(image_path, 'rb') as img:
            image_data = img.read()
        
        # Generate a unique filename
        filename = f"instagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        # Upload to FTP
        image_url = upload_image_to_ftp(image_data, filename)
        if not image_url:
            raise ValueError("Failed to upload image to FTP server")
        
        print(f"Image uploaded successfully: {image_url}")
        
        # Create the container with the FTP URL
        data = {
            'image_url': image_url,
            'caption': caption
        }
        
        result = self._make_request('POST', endpoint, data=data)
        return result.get('id')

    def publish_container(self, container_id: str) -> str:
        """
        Publish a media container
        Returns the ID of the published post
        """
        endpoint = f"{self.instagram_account_id}/media_publish"
        data = {
            'creation_id': container_id
        }
        
        result = self._make_request('POST', endpoint, data=data)
        return result.get('id')

    def publish_post(self, image_path: str, caption: str) -> Optional[str]:
        """
        Publish an image post to Instagram
        Returns the post ID if successful, None otherwise
        """
        try:
            # Step 1: Create a media container
            container_id = self.create_container(image_path, caption)
            if not container_id:
                raise ValueError("Failed to create media container")
            
            # Step 2: Publish the container
            post_id = self.publish_container(container_id)
            if not post_id:
                raise ValueError("Failed to publish media container")
            
            return post_id
            
        except Exception as e:
            print(f"Error publishing to Instagram: {str(e)}")
            return None

def test_instagram_connection():
    """Test the Instagram connection and basic functionality"""
    try:
        publisher = InstagramPublisher()
        
        # Test getting account info
        print("\nTesting Instagram connection...")
        print(f"Using Account ID: {publisher.instagram_account_id}")
        print(f"Access Token (first 20 chars): {publisher.access_token[:20]}...")
        
        account_info = publisher.get_account_info()
        print(f"\nConnection successful!")
        print(f"Account Info:")
        print(json.dumps(account_info, indent=2))
        
        return True
        
    except Exception as e:
        print(f"\nError testing Instagram connection: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the connection
    test_instagram_connection() 