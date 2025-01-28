import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import time

def load_env_file():
    """Load and parse the .env file"""
    env_path = '.env'
    env_content = {}
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_content[key] = value
    return env_content

def save_env_file(env_content):
    """Save the updated environment variables back to .env"""
    env_path = '.env'
    with open(env_path, 'w') as f:
        for key, value in env_content.items():
            f.write(f"{key}={value}\n")

def get_long_lived_token(short_lived_token, app_id, app_secret):
    """Convert a short-lived token to a long-lived token"""
    url = "https://graph.facebook.com/v18.0/oauth/access_token"
    params = {
        'grant_type': 'fb_exchange_token',
        'client_id': app_id,
        'client_secret': app_secret,
        'fb_exchange_token': short_lived_token
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'access_token' in data:
            return data['access_token']
        else:
            print("Error getting long-lived token:")
            print(json.dumps(data, indent=2))
            return None
    except Exception as e:
        print(f"Error exchanging token: {str(e)}")
        return None

def check_token_validity(access_token):
    """Check if the token is valid and when it expires"""
    url = "https://graph.facebook.com/debug_token"
    params = {
        'input_token': access_token,
        'access_token': access_token
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'data' in data:
            token_data = data['data']
            is_valid = token_data.get('is_valid', False)
            expires_at = token_data.get('expires_at', 0)
            
            if is_valid:
                expiry_date = datetime.fromtimestamp(expires_at)
                days_until_expiry = (expiry_date - datetime.now()).days
                
                print(f"\nToken Status:")
                print(f"✓ Token is valid")
                print(f"✓ Expires in {days_until_expiry} days ({expiry_date.strftime('%Y-%m-%d %H:%M:%S')})")
                print(f"✓ Scopes: {', '.join(token_data.get('scopes', []))}")
                
                return is_valid, days_until_expiry
            else:
                print("\n❌ Token is invalid")
                error_message = token_data.get('error', {}).get('message', 'Unknown error')
                print(f"Error: {error_message}")
                return False, 0
    except Exception as e:
        print(f"Error checking token: {str(e)}")
        return False, 0

def refresh_token_if_needed():
    """Main function to check and refresh the Instagram access token"""
    # Load environment variables
    load_dotenv()
    env_content = load_env_file()
    
    current_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN')
    app_id = os.environ.get('INSTAGRAM_APP_ID')
    app_secret = os.environ.get('INSTAGRAM_APP_SECRET')
    
    if not all([current_token, app_id, app_secret]):
        print("❌ Missing required environment variables")
        print("Please ensure you have set:")
        print("- INSTAGRAM_ACCESS_TOKEN")
        print("- INSTAGRAM_APP_ID")
        print("- INSTAGRAM_APP_SECRET")
        return
    
    print("\n🔍 Checking current token status...")
    is_valid, days_until_expiry = check_token_validity(current_token)
    
    # If token is invalid or expires in less than 7 days, get a new long-lived token
    if not is_valid or days_until_expiry < 7:
        print("\n🔄 Getting new long-lived token...")
        new_token = get_long_lived_token(current_token, app_id, app_secret)
        
        if new_token:
            # Verify the new token
            is_valid, days_until_expiry = check_token_validity(new_token)
            
            if is_valid:
                # Update the .env file with the new token
                env_content['INSTAGRAM_ACCESS_TOKEN'] = new_token
                save_env_file(env_content)
                
                print("\n✅ Token updated successfully!")
                print("The new token has been saved to your .env file")
                
                # Test the new token
                from modules.instagram_publish import test_instagram_connection
                print("\n🧪 Testing new token...")
                time.sleep(2)  # Brief pause for rate limiting
                if test_instagram_connection():
                    print("\n🎉 All done! Your Instagram connection is ready to use")
                else:
                    print("\n⚠️ Token updated but test connection failed")
            else:
                print("\n❌ New token validation failed")
        else:
            print("\n❌ Failed to get new long-lived token")
    else:
        print("\n✅ Current token is valid and not near expiration")
        print("No action needed at this time")

if __name__ == "__main__":
    refresh_token_if_needed() 