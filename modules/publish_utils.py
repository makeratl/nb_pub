from .haiku_image_generator import generate_haiku_background
import base64

def generate_and_encode_images(haiku, headline, article_date):
    try:
        image_path, image_prompt = generate_haiku_background(haiku, headline, article_date)
        if image_path:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            return encoded_image, image_prompt
        else:
            return None, None
    except Exception as e:
        print(f"Error generating haiku image: {str(e)}")
        return None, None 