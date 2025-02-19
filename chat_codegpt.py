from judini import CodeGPTPlus
import sys
import os
from dotenv import load_dotenv
load_dotenv()

def chat_with_codegpt(user_message, agent_id=None):
    # Load API credentials from environment variables
    api_key = os.environ.get("CODEGPT_API_KEY")
    org_id = os.environ.get("CODEGPT_ORG_ID")
    default_agent_id = os.environ.get("CODEGPT_AGENT_ID")

    # Use provided agent_id or fall back to default from environment
    agent_id = agent_id or default_agent_id

    if not all([api_key, org_id, agent_id]):
        raise ValueError("Missing required environment variables for CodeGPT API")

    # Initialize CodeGPTPlus
    codegpt = CodeGPTPlus(api_key=api_key, org_id=org_id)

    # Prepare the message
    messages = [{"role": "user", "content": user_message}]

    # Call the CodeGPTPlus API for a chat completion
    chat = codegpt.chat_completion(agent_id=agent_id, messages=messages)

    # Return the AI response
    return chat if chat else "Failed to generate a response. Please try again."

if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
        response = chat_with_codegpt(user_input)
        print(response)
    else:
        print("Please provide a message as a command-line argument.")
