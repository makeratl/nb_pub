from openai import OpenAI
from lmstudio_config import LMSTUDIO_CONFIG, CHAT_PROFILES
import json
import re

class LMStudioChat:
    def __init__(self, profile="default"):
        self.client = OpenAI(
            base_url=LMSTUDIO_CONFIG["base_url"],
            api_key=LMSTUDIO_CONFIG["api_key"]
        )
        self.profile = profile
        self.profile_config = CHAT_PROFILES.get(profile, CHAT_PROFILES["default"])

    def sanitize_response(self, response):
        """Clean up AI response and extract JSON if needed."""
        if self.profile_config["output_format"] != "json":
            return response

        # Try to find JSON in the response
        try:
            # First try to parse the entire response as JSON
            json.loads(response)  # Validate JSON
            return response
        except json.JSONDecodeError:
            # If that fails, try to extract JSON from the response
            try:
                # Look for JSON between curly braces
                json_match = re.search(r'\{[^{]*\}', response)
                if json_match:
                    json_str = json_match.group(0)
                    json.loads(json_str)  # Validate JSON
                    return json_str
                
                # Look for JSON in code blocks
                code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if code_block_match:
                    json_str = code_block_match.group(1)
                    json.loads(json_str)  # Validate JSON
                    return json_str
                
                # If no JSON found, return original response
                print("Warning: Could not extract valid JSON from response")
                return response
            except json.JSONDecodeError:
                print("Warning: Found JSON-like content but failed to parse it")
                return response

    def chat(self, user_message):
        messages = []
        
        # Add system prompt if it exists
        if self.profile_config["system_prompt"]:
            messages.append({
                "role": "system",
                "content": self.profile_config["system_prompt"]
            })
        
        # Add user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        try:
            completion = self.client.chat.completions.create(
                model=LMSTUDIO_CONFIG["default_model"],
                messages=messages,
                max_tokens=LMSTUDIO_CONFIG["max_tokens"],
                stream=True
            )

            # Collect the AI response
            response = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    response += chunk.choices[0].delta.content

            # Clean up the response if needed
            cleaned_response = self.sanitize_response(response)
            return cleaned_response if cleaned_response else "Failed to generate a response. Please try again."
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return "An error occurred while communicating with the AI."

def chat_with_profile(profile, user_message):
    chat = LMStudioChat(profile)
    return chat.chat(user_message)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python lmstudio_chat.py <profile> <message>")
        sys.exit(1)
        
    profile = sys.argv[1]
    user_input = " ".join(sys.argv[2:])
    
    if profile not in CHAT_PROFILES:
        print(f"Invalid profile. Available profiles: {', '.join(CHAT_PROFILES.keys())}")
        sys.exit(1)
        
    response = chat_with_profile(profile, user_input)
    print(response) 