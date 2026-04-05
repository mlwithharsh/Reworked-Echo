import os
import requests
from tqdm import tqdm

def download_gguf(url, dest_path):
    response = requests.get(url, stream=True)
    total_size = int(response.headers.get('content-length', 0))
    
    if os.path.exists(dest_path) and os.path.getsize(dest_path) == total_size:
        print(f"Model already exists at {dest_path}")
        return

    print(f"Downloading Production GGUF Model: {os.path.basename(dest_path)} ({total_size/1e6:.1f} MB)...")
    
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
    # Standardizing on Qwen2-0.5B-Instruct GGUF for production
    MODEL_URL = "https://huggingface.co/Qwen/Qwen2-0.5B-Instruct-GGUF/resolve/main/qwen2-0.5b-instruct-q4_k_m.gguf"
    DEST = "d:/ECHO V1/helix_backend/models/qwen2-0.5b-instruct-q4_k_m.gguf"
    download_gguf(MODEL_URL, DEST)
