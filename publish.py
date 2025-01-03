import os
from dotenv import load_dotenv
import tweepy

load_dotenv()  # Load environment variables from .env file

def post_to_twitter(content):
    # Authenticate with Twitter API
    auth = tweepy.OAuthHandler(os.environ["TWITTER_CONSUMER_KEY"], os.environ["TWITTER_CONSUMER_SECRET"])
    auth.set_access_token(os.environ["TWITTER_ACCESS_TOKEN"], os.environ["TWITTER_ACCESS_TOKEN_SECRET"])
    api = tweepy.API(auth)

    # Post content to Twitter
    try:
        api.update_status(content)
        print("Successfully posted to Twitter.")
    except tweepy.TweepyException as e:
        print(f"Error posting to Twitter: {e}")

if __name__ == "__main__":
    test_content = "This is a test post from my Python application!"
    post_to_twitter(test_content)

# ... existing code ... 