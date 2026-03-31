import requests
import os
from dotenv import load_dotenv

# Path to the .env file in the frontend folder
dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'echo-v1-frontend', '.env')
load_dotenv(dotenv_path)

api_key = os.getenv("GROQ_API_KEY")
print(f"Using API Key (first 10 chars): {api_key[:10] if api_key else 'None'}")

url = "https://api.groq.com/openai/v1/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
payload = {
    "model": "llama-3.1-8b-instant",
    "messages": [{"role": "user", "content": "hello"}],
    "max_tokens": 10
}

try:
    print(f"Attempting to connect to {url}...")
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error occurred: {e}")
