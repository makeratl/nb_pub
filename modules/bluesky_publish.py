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

def create_post(session, text, image_blob, article_url):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    # Calculate the start and end positions of the article URL in the text
    url_start = len(text) + 1
    url_end = url_start + len(article_url) + 24  # Add 24 to account for "Read the full article: " and the period
    
    post_text = f"{text}\n\nRead the full article: {article_url}"
    
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

def publish_to_bluesky(haiku, article_url, image_path):
    try:
        session = create_session()
        image_blob = upload_image(session, image_path)
        post_result = create_post(session, haiku, image_blob, article_url)
        print(f"Published to Bluesky: {json.dumps(post_result, indent=2)}")
    except requests.exceptions.RequestException as e:
        print(f"Error publishing to Bluesky: {str(e)}")
        print(f"Response Content: {e.response.content}")