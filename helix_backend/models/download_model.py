import os
import requests
from tqdm import tqdm

def download_gguf(url, dest_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) == total_size:
        print(f"Model already exists at {dest_path}")
        return

    print(f"Downloading Edge AI Model: {os.path.basename(dest_path)} ({total_size/1e6:.1f} MB)...")
    
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    with open(dest_path, "wb") as f, tqdm(
        desc=os.path.basename(dest_path),
        total=total_size,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            size = f.write(chunk)
            bar.update(size)

if __name__ == "__main__":
    MODEL_URL = "https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf?download=true"
    DEST = "d:/ECHO V1/helix_backend/models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    download_gguf(MODEL_URL, DEST)
