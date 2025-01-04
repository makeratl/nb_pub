import os
import ftplib
import base64
from io import BytesIO
from PIL import Image
import streamlit as st

def base64_to_image(base64_string):
    """Convert base64 data URL to image bytes"""
    try:
        # Remove the data URL prefix if present
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        return base64.b64decode(base64_string)
    except Exception as e:
        st.error(f"Error decoding base64: {str(e)}")
        return None

def upload_images_to_ftp(article_id, image_data, image_haiku):
    """Upload images to FTP server and return URLs"""
    ftp_host = os.getenv("FTP_HOST", "gvam1076.siteground.biz")
    ftp_user = os.getenv("FTP_USER", "imagepost@ainewsbrew.com")
    ftp_pass = os.getenv("FTP_PASS")
    ftp_port = int(os.getenv("FTP_PORT", "21"))
    ftp_dir = os.getenv("FTP_DIR", "/fetch.ainewsbrew.com/public_html/images/")
    
    if not all([ftp_host, ftp_user, ftp_pass]):
        st.error("Missing FTP credentials in environment variables")
        return None, None
    
    try:
        # Connect to FTP server
        with st.spinner("Connecting to FTP server..."):
            ftp = ftplib.FTP()
            ftp.connect(ftp_host, ftp_port)
            ftp.login(ftp_user, ftp_pass)
            ftp.cwd(ftp_dir)
        
        image_urls = {"background": None, "haiku": None}
        
        # Upload background image
        if image_data:
            with st.spinner("Uploading background image..."):
                bg_filename = f"{article_id}_background.jpg"
                bg_data = BytesIO(base64_to_image(image_data))
                if bg_data.getvalue():
                    ftp.storbinary(f'STOR {bg_filename}', bg_data)
                    image_urls["background"] = f"https://fetch.ainewsbrew.com/images/{bg_filename}"
                    st.success(f"Background image uploaded: {bg_filename}")
                else:
                    st.error("Error: Background image data is empty")
        
        # Upload haiku image
        if image_haiku:
            with st.spinner("Uploading haiku image..."):
                haiku_filename = f"{article_id}_haiku.jpg"
                haiku_data = BytesIO(base64_to_image(image_haiku))
                if haiku_data.getvalue():
                    ftp.storbinary(f'STOR {haiku_filename}', haiku_data)
                    image_urls["haiku"] = f"https://fetch.ainewsbrew.com/images/{haiku_filename}"
                    st.success(f"Haiku image uploaded: {haiku_filename}")
                else:
                    st.error("Error: Haiku image data is empty")
        
        ftp.quit()
        return image_urls["background"], image_urls["haiku"]
        
    except Exception as e:
        st.error(f"Error uploading images to FTP: {str(e)}")
        if 'ftp' in locals():
            try:
                ftp.quit()
            except:
                pass
        return None, None 