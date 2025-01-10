"""API interaction functions"""
import os
import requests
import json
import urllib3
from dotenv import load_dotenv
import time

load_dotenv()
API_KEY = os.environ.get("NEWSCATCHER_API_KEY")

def get_news_data(search_type, query="", when="24h"):
    """Fetch news data from NewsCatcher API"""
    time_mapping = {
        "1h": "1h", "3h": "3h", "4h": "4h", "6h": "6h", "12h": "12h",
        "24h": "1d", "2d": "2d", "3d": "3d", "5d": "5d", "7d": "7d"
    }
    api_time = time_mapping.get(when, "1d")
    
    if search_type == "Headlines":
        url = "https://v3-api.newscatcherapi.com/api/latest_headlines"
        params = {
            "when": api_time,
            "countries": "US, CA, MX, GB",
            "predefined_sources": "top 70 US,top 50 CA,top 20 MX,top 50 GB",
            "lang": "en",
            "ranked_only": "true",
            "clustering_enabled": "true",
            "clustering_threshold": "0.8",
            "page_size": "800"
        }
    else:
        url = "https://v3-api.newscatcherapi.com/api/search"
        params = {
            "q": query,
            "from_": api_time,
            "countries": "US, CA, MX, GB, UA, IN, BR, FR, JP, CN, PL",
            "lang": "en",
            "ranked_only": "true",
            "clustering_enabled": "true",
            "page_size": "100"
        }

    headers = {"x-api-token": API_KEY}
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching news: {str(e)}")  # Log the error
        return None

def fetch_latest_headlines():
    """Fetch all headlines from the API"""
    try:
        api_key = os.environ.get("PUBLISH_API_KEY")
        http = urllib3.PoolManager()
        
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
        
        timestamp = int(time.time() * 1000)
        url = f"https://fetch.ainewsbrew.com/api/index_v5.php?mode=latest&timestamp={timestamp}"
        
        response = http.request(
            'GET',
            url,
            headers=headers
        )
        
        return json.loads(response.data.decode('utf-8')) if response.status == 200 else []
        
    except Exception as e:
        print(f"Error fetching headlines: {str(e)}")
        return []