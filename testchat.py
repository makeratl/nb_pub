import subprocess
import os
import sys

def test_chat_lmstudio():
    # Test message to send to the AI
    test_message = "Hello AI! Can you tell me about your capabilities?"
    
    # Get the current directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the full path to chat_lmstudio.py
    chat_script_path = os.path.join(current_dir, "chat_lmstudio.py")
    
    # print(f"Attempting to run: {chat_script_path}")
    # print(f"With message: {test_message}")
    
    # Use the Python executable from the current environment
    python_executable = sys.executable
    
    # Run the chat_lmstudio.py script with the test message
    result = subprocess.run(
        [python_executable, chat_script_path, test_message],
        capture_output=True,
        text=True,
        env=os.environ  # Pass the current environment variables
    )

    # Print both stdout and stderr
    print(result.stdout)

if __name__ == "__main__":
    test_chat_lmstudio()
