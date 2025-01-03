import streamlit as st
import requests
from dotenv import load_dotenv
import os
import time
import logging

load_dotenv()
api_key = os.getenv("HORIAR_API_KEY")

logging.basicConfig(level=logging.DEBUG)

st.title("Horiar API Testing")

def poll_text_to_image_status(job_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    start_time = time.time()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    elapsed_time_placeholder = st.empty()
    
    while True:
        elapsed_time = int(time.time() - start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        elapsed_time_placeholder.text(f"Elapsed time: {minutes:02d}:{seconds:02d}")
        
        response = requests.get(f"https://api.horiar.com/enterprise/query/{job_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"Text-to-Image response: {result}")
            
            if "message" in result:
                progress_bar.progress(0)
                status_text.text(f"Status: {result['message']}. Waiting...")
                time.sleep(5)  # Wait for 5 seconds before checking again
            else:
                progress_bar.progress(100)
                status_text.text("Request completed!")
                return result
        elif response.status_code == 500:
            error_message = response.json().get("message", "")
            if "is not a valid ObjectId" in error_message:
                st.warning(f"Encountered an issue with the job ID format: {error_message}. Please check with the API provider for the correct format.")
                return None
            else:
                st.error(f"Request failed with status code {response.status_code}: {response.text}")
                return None
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")
            return None

def poll_text_to_video_status(job_id):
    headers = {"Authorization": f"Bearer {api_key}"}
    start_time = time.time()
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    elapsed_time_placeholder = st.empty()
    
    while True:
        elapsed_time = int(time.time() - start_time)
        minutes, seconds = divmod(elapsed_time, 60)
        elapsed_time_placeholder.text(f"Elapsed time: {minutes:02d}:{seconds:02d}")
        
        response = requests.get(f"https://api.horiar.com/enterprise/query/{job_id}", headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"Text-to-Video response: {result}")
            
            if "message" in result:
                progress_bar.progress(0)
                status_text.text(f"Status: {result['message']}. Waiting...")
                time.sleep(5)  # Wait for 5 seconds before checking again
            else:
                progress_bar.progress(100)
                status_text.text("Request completed!")
                return result
        elif response.status_code == 500:
            error_message = response.json().get("message", "")
            if "is not a valid ObjectId" in error_message:
                st.warning(f"Encountered an issue with the job ID format: {error_message}. Please check with the API provider for the correct format.")
                return None
            else:
                st.error(f"Request failed with status code {response.status_code}: {response.text}")
                return None
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")
            return None

def test_upscale_enhance():
    st.header("Upscale Enhance")
    
    image_url = st.text_input("Image URL")
    
    if st.button("Upscale"):
        with st.spinner("Upscaling image..."):
            headers = {"Authorization": api_key}
            data = {"link": image_url}
            response = requests.post("https://api.horiar.com/enterprise/upscale-enhance", 
                                    headers=headers, data=data)
        
        if response.status_code == 200:
            st.json(response.json())
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")

def test_text_to_image():
    st.header("Text to Image")
    
    prompt = st.text_input("Enter a prompt", key="text_to_image_prompt")
    model_type = st.selectbox("Select model type", ["normal", "ultra detailed"], key="text_to_image_model_type")
    resolution = st.selectbox("Select resolution", [
        "1024x1024 | 1:1 (Square)",
        "1344x768 | 16:9 (Horizontal)", 
        "768x1344 | 9:16 (Vertical)",
        "832x1216 | 2:3 (Classic Portrait)",
        "1536x640 | 21:9 (Epic Ultrawide)",
        "640x1536 | 9:21 (Ultra tall)",
        "1472x704 | 19:9 (Cinematic Ultrawide)", 
        "1152x896 | 4:3 (Classic Landscape)"
    ], key="text_to_image_resolution")
    
    if st.button("Generate Image", key="text_to_image_button"):
        with st.spinner("Generating image..."):
            headers = {"Authorization": f"Bearer {api_key}"}
            data = {
                "prompt": prompt,
                "model_type": model_type,
                "resolution": resolution
            }
            response = requests.post("https://api.horiar.com/enterprise/text-to-image", 
                                    headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"Text-to-Image response: {result}")
            job_id = result["job_id"]
            st.info(f"Request queued with job ID: {job_id}. Waiting for completion...")
            
            result = poll_text_to_image_status(job_id)
            
            if result:
                image_url = result["image"]
                st.image(image_url, caption="Generated Image")
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")

def test_text_to_video():
    st.header("Text to Video")
    
    prompt = st.text_input("Enter a prompt", key="text_to_video_prompt")
    
    if st.button("Generate Video", key="text_to_video_button"):
        with st.spinner("Generating video..."):
            headers = {"Authorization": f"Bearer {api_key}"}
            data = {"prompt": prompt}
            response = requests.post("https://api.horiar.com/enterprise/text-to-video", 
                                    headers=headers, json=data)
        
        if response.status_code == 200:
            result = response.json()
            logging.debug(f"Text-to-Video response: {result}")
            job_id = result["job_id"]
            st.info(f"Request queued with job ID: {job_id}. Waiting for completion...")
            
            result = poll_text_to_video_status(job_id)
            
            if result:
                video_url = result["video_url"]
                st.video(video_url)
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")

def test_image_to_video():
    st.header("Image to Video")
    
    image_file = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png"])
    prompt = st.text_input("Enter a prompt", key="image_to_video_prompt")
    
    if st.button("Generate Video", key="image_to_video_button") and image_file is not None:
        with st.spinner("Generating video from image..."):
            files = {"image": image_file}
            data = {"prompt": prompt}
            headers = {"Authorization": api_key}
            
            response = requests.post("https://api.horiar.com/enterprise/image-to-video",
                                    files=files, data=data, headers=headers)
        
        if response.status_code == 200:
            st.json(response.json())
        else:
            st.error(f"Request failed with status code {response.status_code}: {response.text}")

# ... API testing functions will go here ...

if __name__ == '__main__':
    print("API key loaded:", api_key) 
    test_upscale_enhance()
    test_text_to_image()
    test_text_to_video() 
    test_image_to_video()