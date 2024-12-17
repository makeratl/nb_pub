import requests
import json
from datetime import datetime, timezone

# Bluesky account credentials
BLUESKY_HANDLE = "ainewsbrew.bsky.social"
BLUESKY_APP_PASSWORD = 'iB9gUDAwAg@BGXu'

# Create a session
def create_session():
    resp = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_APP_PASSWORD},
    )
    resp.raise_for_status()
    return resp.json()

# Upload an image
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

# Create a post with an image
def create_post(session, text, image_blob):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    post = {
        "$type": "app.bsky.feed.post",
        "text": text,
        "createdAt": now,
        "embed": {
            "$type": "app.bsky.embed.images",
            "images": [
                {
                    "image": image_blob,
                    "alt": "Wandering in to the future",
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

def main():
    # Create a session
    session = create_session()
    print(f"Created session with token: {session['accessJwt']}")

    # Upload the image
    image_blob = upload_image(session, "haikubg_with_text.png")
    print(f"Uploaded image: {image_blob}")

    # Create a post with the image
    post_text = "AI News Brew (ainewsbrew.com) has come to Bluesky!\n\nFollow us for objective, unbiased reporting on events with a poetic twist.  More information at https://www.ainewsbrew.com/ \n\n#ainewsbrew #objective #unbiased #aicontent #ai #news #dailynews #haiku #newhaiku #Bluesky"
    post_result = create_post(session, post_text, image_blob)
    print(f"Created post: {json.dumps(post_result, indent=2)}")

if __name__ == "__main__":
    main()
