import os
import requests
from datetime import datetime
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

class ThreadsPublisher:
    """
    Handles publishing to Threads using the Threads API
    """
    
    def __init__(self):
        """Initialize with credentials from environment variables"""
        self.access_token = os.environ.get("THREADS_ACCESS_TOKEN")
        self.threads_account_id = os.environ.get("THREADS_ACCOUNT_ID")
        self.api_version = "v18.0"  # Current stable version as of 2024
        self.base_url = f"https://graph.facebook.com/{self.api_version}"
        
        if not self.access_token or not self.threads_account_id:
            raise ValueError("Missing required Threads credentials in environment variables")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the Threads API"""
        url = f"{self.base_url}/{endpoint}"
        params = kwargs.get('params', {})
        params['access_token'] = self.access_token
        
        response = requests.request(
            method,
            url,
            params=params,
            **{k: v for k, v in kwargs.items() if k != 'params'}
        )
        
        if not response.ok:
            error_data = response.json()
            raise requests.exceptions.HTTPError(
                f"Threads API error: {error_data.get('error', {}).get('message')}"
            )
        
        return response.json()

    def get_account_info(self) -> Dict[str, Any]:
        """Get basic information about the Threads account"""
        try:
            endpoint = f"{self.threads_account_id}"
            fields = "id,username,name"
            result = self._make_request('GET', endpoint, params={'fields': fields})
            
            if result:
                print(f"\nSuccessfully connected to Threads account:")
                print(f"Username: {result.get('username')}")
                print(f"Account ID: {result.get('id')}")
                return result
                
        except Exception as e:
            print(f"\nFailed to get account info: {str(e)}")
            raise

    def create_container(self, image_path: str, caption: str) -> Optional[str]:
        """
        Create a media container for Threads
        Returns the container ID if successful
        """
        try:
            # First upload the image to FTP to get a URL
            with open(image_path, 'rb') as img:
                image_data = img.read()
            
            # Generate a unique filename
            filename = f"threads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
            # Upload to FTP
            image_url = upload_image_to_ftp(image_data, filename)
            if not image_url:
                raise ValueError("Failed to upload image to FTP server")
            
            # Create the media container
            endpoint = f"{self.threads_account_id}/media"
            data = {
                'image_url': image_url,
                'caption': caption,
                'media_type': 'IMAGE'
            }
            
            result = self._make_request('POST', endpoint, data=data)
            return result.get('id')
            
        except Exception as e:
            print(f"Error creating media container: {str(e)}")
            return None

    def publish_container(self, container_id: str) -> str:
        """
        Publish a media container to Threads
        Returns the ID of the published post
        """
        endpoint = f"{self.threads_account_id}/media_publish"
        data = {
            'creation_id': container_id
        }
        
        result = self._make_request('POST', endpoint, data=data)
        return result.get('id')

    def publish_post(self, image_path: str, caption: str) -> Optional[str]:
        """
        Publish an image post to Threads
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
            
            print(f"\nSuccessfully published to Threads!")
            print(f"Post ID: {post_id}")
            return post_id
            
        except Exception as e:
            print(f"Error publishing to Threads: {str(e)}")
            return None

def test_threads_connection() -> bool:
    """Test the connection to Threads API"""
    try:
        publisher = ThreadsPublisher()
        publisher.get_account_info()
        print("\nThreads connection test successful!")
        return True
    except Exception as e:
        print(f"\nThreads connection test failed: {str(e)}")
        return False 