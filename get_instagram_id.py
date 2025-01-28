import os
import requests
from dotenv import load_dotenv
import json

def debug_token(access_token):
    """Debug the access token to get app and user information"""
    url = "https://graph.facebook.com/debug_token"
    params = {
        'input_token': access_token,
        'access_token': access_token
    }
    
    try:
        print("\n🔍 Debugging Access Token...")
        response = requests.get(url, params=params)
        data = response.json()
        
        if 'data' in data:
            print("\nFacebook App Details:")
            print("--------------------")
            print(f"Facebook App ID: {data['data'].get('app_id')} (Not what we need)")
            print(f"Facebook User ID: {data['data'].get('user_id')} (Not what we need)")
            print(f"\nPermissions granted: {', '.join(data['data'].get('scopes', []))}")
            return data['data'].get('user_id')
    except Exception as e:
        print(f"Error debugging token: {str(e)}")
    return None

def get_instagram_business_id(access_token, user_id):
    """Get the Instagram Business Account ID"""
    # First get the Facebook Pages
    url = f"https://graph.facebook.com/v18.0/{user_id}/accounts"
    params = {
        'access_token': access_token,
        'fields': 'id,name,instagram_business_account{id,username}'
    }
    
    try:
        print("\n📘 Checking Facebook Pages for Instagram connections...")
        response = requests.get(url, params=params)
        data = response.json()
        
        found_instagram = False
        if 'data' in data:
            for page in data['data']:
                instagram = page.get('instagram_business_account')
                if instagram:
                    found_instagram = True
                    print("\n✅ FOUND THE ID YOU NEED!")
                    print("------------------------")
                    print(f"Instagram Business Account ID: {instagram.get('id')} ← THIS IS WHAT YOU NEED")
                    print(f"Instagram Username: {instagram.get('username')}")
                    print("\nUpdate your .env file with:")
                    print("------------------------")
                    print(f"INSTAGRAM_ACCOUNT_ID={instagram.get('id')}")
                    
        if not found_instagram:
            print("\n❌ No Instagram Business Account found!")
            print("\nPlease make sure:")
            print("1. Your Instagram account is converted to a Business/Creator account")
            print("2. Your Instagram account is connected to your Facebook Page")
            print("3. Your Facebook App has the required permissions:")
            print("   - instagram_basic")
            print("   - instagram_content_publish")
            print("   - pages_read_engagement")
            print("   - pages_show_list")
            
            # Print the raw data for debugging
            print("\n🔍 Debug Data:")
            print("--------------")
            print(json.dumps(data, indent=2))
            
    except Exception as e:
        print(f"Error getting Instagram Business ID: {str(e)}")
        if hasattr(e, 'response'):
            print("\nError Response:")
            print(e.response.text)

def main():
    """Main function to find the Instagram Business Account ID"""
    load_dotenv()
    
    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    if not access_token:
        print("❌ Missing INSTAGRAM_ACCESS_TOKEN in .env file")
        return
    
    print("\n🔎 Looking for your Instagram Business Account ID...")
    print("================================================")
    
    # First debug the token to get the user ID
    user_id = debug_token(access_token)
    if user_id:
        # Then get the Instagram Business Account ID
        get_instagram_business_id(access_token, user_id)

if __name__ == "__main__":
    main() 