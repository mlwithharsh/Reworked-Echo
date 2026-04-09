import requests
import json

url = "http://localhost:8000/api/chat/stream"
payload = {
    "user_id": "test-user-sonnet",
    "message": "Hey Suzi, what are you doing right now?",
    "personality": "suzi"
}
headers = {
    "Content-Type": "application/json",
    "x-api-token": "dev-token"
}

try:
    response = requests.post(url, json=payload, headers=headers, stream=True)
    full_text = ""
    for line in response.iter_lines():
        if line:
            chunk = line.decode('utf-8')
            if chunk.startswith("data: "):
                data_str = chunk[6:]
                if data_str == "[DONE]":
                    break
                data = json.loads(data_str)
                token = data.get("token", "")
                full_text += token
                print(token, end="", flush=True)
    print(f"\n\nFull Response: {full_text}")
except Exception as e:
    print(f"Error: {e}")
