import requests
import json
import os
from datetime import datetime, timezone

# Bluesky account credentials
BLUESKY_HANDLE = os.environ.get("BLUESKY_HANDLE")
BLUESKY_APP_PASSWORD = os.environ.get("BLUESKY_APP_PASSWORD")

def create_session():
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json()

def upload_image(session, image_path):
    mime_type = "image/png"  # Adjust the mime type based on the image format
    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
            headers={
                "Content-Type": mime_type,
                "Authorization": "Bearer " + session["accessJwt"]
            },
            data=f.read(),
        )
    resp.raise_for_status()
    return resp.json()["blob"]

def create_post(session, text, image_blob, article_url, hashtags):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Calculate the start and end positions of the article URL in the text
    url_start = len(text) + 1
    url_end = url_start + len(article_url) + 24  # Add 24 to account for "Read the full article: " and the period
    
    # Limit hashtags to a maximum of 5
    hashtags = ' '.join(hashtags.split()[:5])
    
    post_text = f"{text}\n\nRead the full article: {article_url}\n\n{hashtags}"
    
    # Truncate post_text if it exceeds 300 characters
    if len(post_text) > 300:
        truncated_text = text[:200] + "..."  # Truncate the main text
        post_text = f"{truncated_text}\n\nRead the full article: {article_url}\n\n{hashtags}"
    
    post = {
        "$type": "app.bsky.feed.post",
        "text": post_text,
        "createdAt": now,
        "facets": [
            {
                "index": {
                    "byteStart": url_start,
                    "byteEnd": url_end
                },
                "features": [
                    {
                        "$type": "app.bsky.richtext.facet#link",
                        "uri": article_url
                    }
                ]
            }
        ],
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": image_blob,
                    "alt": "AI News Brew Article Image",
                }
            ],
        },
    }

    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": "Bearer " + session["accessJwt"]},
        json={
            "repo": session["did"],
            "collection": "app.bsky.feed.post",
            "record": post,
        },
    )
    resp.raise_for_status()
    return resp.json()

def publish_to_bluesky(haiku, article_url, image_path, hashtags):
    try:
        session = create_session()
        image_blob = upload_image(session, image_path)
        post_result = create_post(session, haiku, image_blob, article_url, hashtags)
        print(f"Published to Bluesky: {json.dumps(post_result, indent=2)}")
        # Return True if we got a valid post result with an 'uri' field
        return bool(post_result and post_result.get('uri'))
    except requests.exceptions.RequestException as e:
        print(f"Error publishing to Bluesky: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'content'):
            print(f"Response Content: {e.response.content}")
        return False
    except Exception as e:
        print(f"Unexpected error publishing to Bluesky: {str(e)}")
        return False